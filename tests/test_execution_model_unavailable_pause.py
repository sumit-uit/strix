"""Tests for the interactive model/quota-unavailable pause.

A capacity-class error (rate limit, quota exhaustion, or a 503 across every
configured deployment -- e.g. litellm's ALL_TARGETS_SKIPPED) that survives
the transient-retry budget should park an interactive agent instead of
ending its run, so it can pick back up once the user resolves the outage.
Headless (non-interactive) runs have no one to unpause them, so they keep
the old fail-fast behavior.
"""

from __future__ import annotations

from typing import Any, cast

import httpx
import pytest
from agents import RunConfig, Runner
from openai import APIError, APIStatusError

from strix.core import execution
from strix.core.agents import AgentCoordinator


def _request() -> httpx.Request:
    return httpx.Request("POST", "https://api.openai.com/v1/responses")


def _all_targets_skipped_error() -> APIStatusError:
    """Mirrors the litellm router error that motivated this: every configured
    deployment was skipped, 503, no "rate limit"/"too many requests" wording.
    """
    return APIStatusError(
        "Service temporarily unavailable: all targets were skipped by pre-dispatch filters",
        response=httpx.Response(status_code=503, request=_request()),
        body=None,
    )


def test_all_targets_skipped_503_is_model_unavailable() -> None:
    assert execution._is_model_unavailable_error(_all_targets_skipped_error()) is True


def test_ordinary_bad_request_is_not_model_unavailable() -> None:
    bad_request = APIStatusError(
        "invalid parameter", response=httpx.Response(400, request=_request()), body=None
    )
    assert execution._is_model_unavailable_error(bad_request) is False


class _FakeStream:
    def __init__(self, exc: BaseException | None = None) -> None:
        self._exc = exc
        self.run_loop_exception: BaseException | None = None

    async def stream_events(self) -> Any:
        if self._exc is not None:
            raise self._exc
        return
        yield  # type: ignore[unreachable]  # pragma: no cover - keeps this an async generator


def _patch_fast_backoff(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(execution, "_TRANSIENT_MODEL_RETRY_BASE_DELAY_S", 0.0)
    monkeypatch.setattr(execution, "_TRANSIENT_MODEL_RETRY_MAX_DELAY_S", 0.0)
    monkeypatch.setattr(execution, "_RATE_LIMIT_BASE_DELAY_S", 0.0)
    monkeypatch.setattr(execution, "_RATE_LIMIT_MAX_DELAY_S", 0.0)


def _patch_exhausting_streams(monkeypatch: pytest.MonkeyPatch) -> dict[str, int]:
    streams = [
        _FakeStream(exc=_all_targets_skipped_error())
        for _ in range(execution._MAX_TRANSIENT_MODEL_RETRIES + 1)
    ]
    calls = {"n": 0}

    def _fake_run_streamed(*_args: Any, **_kwargs: Any) -> _FakeStream:
        stream = streams[calls["n"]]
        calls["n"] += 1
        return stream

    monkeypatch.setattr(Runner, "run_streamed", _fake_run_streamed)
    return calls


@pytest.mark.asyncio
async def test_persistent_model_unavailable_error_pauses_interactive_agent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fast_backoff(monkeypatch)
    calls = _patch_exhausting_streams(monkeypatch)

    coordinator = AgentCoordinator()
    await coordinator.register("root", "strix", parent_id=None)

    result = await execution._run_cycle(
        object(),
        coordinator,
        "root",
        input_data="task",
        run_config=cast("RunConfig", object()),
        context={},
        max_turns=5,
        session=None,
        interactive=True,
        event_sink=None,
        hooks=None,
    )

    assert result is None
    assert calls["n"] == execution._MAX_TRANSIENT_MODEL_RETRIES + 1
    assert coordinator.statuses["root"] == "model_paused"
    assert coordinator.model_paused is True
    assert "root" not in coordinator.errors


@pytest.mark.asyncio
async def test_paused_child_notifies_its_parent_without_claiming_terminal_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_fast_backoff(monkeypatch)
    _patch_exhausting_streams(monkeypatch)

    coordinator = AgentCoordinator()
    await coordinator.register("root", "strix", parent_id=None)
    await coordinator.register("child", "recon", parent_id="root")

    await execution._run_cycle(
        object(),
        coordinator,
        "child",
        input_data="task",
        run_config=cast("RunConfig", object()),
        context={"parent_id": "root"},
        max_turns=5,
        session=None,
        interactive=True,
        event_sink=None,
        hooks=None,
    )

    assert coordinator.statuses["child"] == "model_paused"
    assert coordinator.pending_counts.get("root", 0) > 0
    # Parking on a model outage isn't a terminal notice: the child still owes
    # its parent a real completion report once it resumes and finishes.
    assert "child" not in coordinator._parent_notified


@pytest.mark.asyncio
async def test_noninteractive_child_still_fails_on_model_unavailable_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No user is attached to a headless scan to unpause it, so it must still
    fail fast and loudly rather than hang forever waiting for a message that
    will never come.
    """
    _patch_fast_backoff(monkeypatch)
    calls = _patch_exhausting_streams(monkeypatch)

    coordinator = AgentCoordinator()
    await coordinator.register("root", "strix", parent_id=None)
    await coordinator.register("child", "recon", parent_id="root")

    with pytest.raises(APIError):
        await execution._run_cycle(
            object(),
            coordinator,
            "child",
            input_data="task",
            run_config=cast("RunConfig", object()),
            context={"parent_id": "root"},
            max_turns=5,
            session=None,
            interactive=False,
            event_sink=None,
            hooks=None,
        )

    assert calls["n"] == execution._MAX_TRANSIENT_MODEL_RETRIES + 1
    assert coordinator.statuses["child"] == "failed"
