"""Tests for the ``--manual-seed`` gate in ``run_strix_scan``.

``manual_seed_gate``, when provided, is awaited with the resolved host-side
Caido proxy URL right after the sandbox is up and before any agent is built,
so a TUI-only opt-in flag can pause a scan and let the user manually
authenticate through the proxy first. Passing nothing (the default, and what
every existing caller still does) must be a strict no-op.
"""

from __future__ import annotations

import types
from typing import Any

import httpx
import pytest
from agents import ModelSettings
from openai import RateLimitError

import strix.tools.notes.tools as notes_tools
import strix.tools.todo.tools as todo_tools
from strix.core import runner
from strix.core.agents import AgentCoordinator
from strix.report.state import ReportState, set_global_report_state
from strix.runtime import session_manager


_HOST_CAIDO_URL = "http://127.0.0.1:54321"


def _make_rate_limit_error() -> RateLimitError:
    request = httpx.Request("POST", "https://api.openai.com/v1/responses")
    response = httpx.Response(status_code=429, request=request)
    return RateLimitError("rate limited", response=response, body=None)


def _patch_engine_scaffold(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    events: list[str],
) -> dict[str, Any]:
    """Stub out everything around build_strix_agent and stop at run_agent_loop."""
    monkeypatch.setattr(runner, "run_dir_for", lambda _scan_id: tmp_path)
    monkeypatch.setattr(runner, "runtime_state_dir", lambda _run_dir: tmp_path)
    monkeypatch.setattr(runner, "setup_scan_logging", lambda _run_dir: lambda: None)
    monkeypatch.setattr(runner, "set_scan_id", lambda _scan_id: None)

    settings = types.SimpleNamespace(
        llm=types.SimpleNamespace(
            model="openai/gpt-4o",
            reasoning_effort="high",
            force_required_tool_choice=False,
            timeout=300,
            prompt_cache=True,
            extra_headers=None,
        ),
        runtime=types.SimpleNamespace(max_context_images=3),
    )
    monkeypatch.setattr(runner, "load_settings", lambda: settings)
    monkeypatch.setattr(runner, "configure_sdk_model_defaults", lambda _settings: None)
    monkeypatch.setattr(
        runner,
        "uses_chat_completions_tool_schema",
        lambda _model, _settings: False,
    )

    monkeypatch.setattr(todo_tools, "hydrate_todos_from_disk", lambda _state_dir: None)
    monkeypatch.setattr(notes_tools, "hydrate_notes_from_disk", lambda _state_dir: None)

    async def _create_or_reuse(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        return {
            "client": object(),
            "session": object(),
            "caido_client": None,
            "host_caido_url": _HOST_CAIDO_URL,
        }

    async def _cleanup(*_args: Any, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(session_manager, "create_or_reuse", _create_or_reuse)
    monkeypatch.setattr(session_manager, "cleanup", _cleanup)

    monkeypatch.setattr(runner, "build_root_task", lambda _scan_config: "task")
    monkeypatch.setattr(runner, "build_scope_context", lambda _scan_config: {})
    monkeypatch.setattr(runner, "make_model_settings", lambda *_args, **_kwargs: ModelSettings())

    captured: dict[str, Any] = {}

    def _build_strix_agent(**kwargs: Any) -> object:
        if kwargs.get("is_root") and "kwargs" not in captured:
            events.append("build_strix_agent")
            captured["kwargs"] = kwargs
        return object()

    monkeypatch.setattr(runner, "build_strix_agent", _build_strix_agent)
    monkeypatch.setattr(runner, "make_child_factory", lambda **_kwargs: lambda **_k: object())
    monkeypatch.setattr(runner, "open_agent_session", lambda _root_id, _db: object())

    async def _raise_rate_limit(*_args: Any, **kwargs: Any) -> None:
        captured["run_config"] = kwargs.get("run_config")
        raise _make_rate_limit_error()

    monkeypatch.setattr(runner, "run_agent_loop", _raise_rate_limit)
    return captured


@pytest.mark.asyncio
async def test_manual_seed_gate_is_awaited_with_proxy_url_before_agent_build(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    events: list[str] = []
    _patch_engine_scaffold(monkeypatch, tmp_path, events)

    seen_urls: list[str] = []

    async def _gate(proxy_url: str) -> None:
        events.append("manual_seed_gate")
        seen_urls.append(proxy_url)

    await runner.run_strix_scan(
        scan_config={"targets": [], "scan_mode": "deep"},
        scan_id="scan-manual-seed",
        image="img",
        coordinator=AgentCoordinator(),
        manual_seed_gate=_gate,
    )

    assert seen_urls == [_HOST_CAIDO_URL]
    assert events == ["manual_seed_gate", "build_strix_agent"]


@pytest.mark.asyncio
async def test_manual_seed_gate_omitted_is_a_no_op(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    """Without manual_seed_gate, behavior is unchanged: no pause, agent still builds."""
    events: list[str] = []
    captured = _patch_engine_scaffold(monkeypatch, tmp_path, events)

    await runner.run_strix_scan(
        scan_config={"targets": [], "scan_mode": "deep"},
        scan_id="scan-manual-seed-default",
        image="img",
        coordinator=AgentCoordinator(),
    )

    assert events == ["build_strix_agent"]
    assert "kwargs" in captured


@pytest.mark.asyncio
async def test_resolved_caido_url_is_stamped_onto_report_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    """Independent of --manual-seed: this lights up the existing (dormant) CLI/TUI
    'Caido: ...' display for every scan, not just ones that opt into the pause.
    """
    events: list[str] = []
    _patch_engine_scaffold(monkeypatch, tmp_path, events)

    report_state = ReportState.__new__(ReportState)
    report_state.caido_url = None
    set_global_report_state(report_state)
    try:
        await runner.run_strix_scan(
            scan_config={"targets": [], "scan_mode": "deep"},
            scan_id="scan-caido-url",
            image="img",
            coordinator=AgentCoordinator(),
        )
        assert report_state.caido_url == _HOST_CAIDO_URL
    finally:
        set_global_report_state(None)  # type: ignore[arg-type]
