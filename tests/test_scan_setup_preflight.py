"""Tests for preflight_model_connection's retry behavior.

Regression coverage: this is the one model call in the whole startup path
that ran completely unprotected -- a single 429/503/"all targets skipped"
blip from the configured model route (e.g. a custom routing proxy) aborted
the launch outright, with no retry at all, unlike every mid-scan turn.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from openai import APIStatusError, BadRequestError

from strix.config import Settings
from strix.interface import scan_setup


def _request() -> httpx.Request:
    return httpx.Request("POST", "https://api.openai.com/v1/responses")


def _all_targets_skipped_error() -> APIStatusError:
    return APIStatusError(
        "Service temporarily unavailable: all targets were skipped by pre-dispatch filters",
        response=httpx.Response(status_code=503, request=_request()),
        body=None,
    )


class _FakeModel:
    def __init__(self, responses: list[Any]) -> None:
        self._responses = list(responses)
        self.calls = 0

    async def get_response(self, **_kwargs: Any) -> Any:
        self.calls += 1
        result = self._responses.pop(0)
        if isinstance(result, BaseException):
            raise result
        return result


class _FakeProvider:
    def __init__(self, model: _FakeModel) -> None:
        self._model = model

    def get_model(self, _model_name: str | None) -> _FakeModel:
        return self._model


def _patch(monkeypatch: pytest.MonkeyPatch, model: _FakeModel) -> None:
    monkeypatch.setattr("strix.config.models.StrixProvider", lambda: _FakeProvider(model))
    monkeypatch.setattr("strix.config.models.configure_sdk_model_defaults", lambda _settings: None)
    monkeypatch.setattr(scan_setup, "_PREFLIGHT_RETRY_BASE_DELAY_S", 0.0)
    monkeypatch.setattr(scan_setup, "_PREFLIGHT_RETRY_MAX_DELAY_S", 0.0)


@pytest.mark.asyncio
async def test_preflight_retries_transient_capacity_error_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = _FakeModel([_all_targets_skipped_error(), _all_targets_skipped_error(), object()])
    _patch(monkeypatch, model)

    await scan_setup.preflight_model_connection("openai/kirostyle", settings=Settings())

    assert model.calls == 3


@pytest.mark.asyncio
async def test_preflight_gives_up_after_max_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    model = _FakeModel(
        [_all_targets_skipped_error() for _ in range(scan_setup._PREFLIGHT_MAX_RETRIES + 1)]
    )
    _patch(monkeypatch, model)

    with pytest.raises(APIStatusError):
        await scan_setup.preflight_model_connection("openai/kirostyle", settings=Settings())

    assert model.calls == scan_setup._PREFLIGHT_MAX_RETRIES + 1


@pytest.mark.asyncio
async def test_preflight_does_not_retry_permanent_error(monkeypatch: pytest.MonkeyPatch) -> None:
    bad_request = BadRequestError(
        "bad model name", response=httpx.Response(400, request=_request()), body=None
    )
    model = _FakeModel([bad_request, object()])
    _patch(monkeypatch, model)

    with pytest.raises(BadRequestError):
        await scan_setup.preflight_model_connection("openai/kirostyle", settings=Settings())

    assert model.calls == 1
