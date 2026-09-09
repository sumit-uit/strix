"""Tests for create_agent's hard depth/count caps on the agent graph.

Regression coverage for two real bugs found in one live run:

1. ``AgentCoordinator.agent_depth`` was off by one -- root reported depth 1
   instead of 0 -- which made the depth cap one level stricter than
   documented and tripped every specialist (grandchild-of-root) agent the
   first time it tried to spawn any helper at all.
2. The refusal message read "do this task yourself instead of delegating
   further," which some agents took literally as an instruction to perform
   the blocked sub-step (e.g. redo reconnaissance) rather than return to
   their own assigned specialization.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from agents.tool_context import ToolContext

from strix.config.settings import (
    DEFAULT_MAX_AGENT_DEPTH,
    DEFAULT_MAX_CONCURRENT_AGENTS,
    DEFAULT_MAX_TOTAL_AGENTS,
)
from strix.core.agents import AgentCoordinator
from strix.tools.agents_graph.tools import _agent_cap_error, create_agent


async def _register_chain(coordinator: AgentCoordinator, depth: int) -> str:
    """Register root -> agent-0 -> agent-1 -> ... of ``depth`` hops; return the leaf id."""
    await coordinator.register("root", "Root Agent", parent_id=None)
    leaf = "root"
    for i in range(depth):
        child = f"agent-{i}"
        await coordinator.register(child, f"Agent {i}", parent_id=leaf)
        leaf = child
    return leaf


@pytest.mark.asyncio
async def test_agent_depth_root_is_zero() -> None:
    coordinator = AgentCoordinator()
    await coordinator.register("root", "Root Agent", parent_id=None)
    assert await coordinator.agent_depth("root") == 0


@pytest.mark.asyncio
async def test_agent_depth_counts_hops_to_root() -> None:
    coordinator = AgentCoordinator()
    leaf = await _register_chain(coordinator, 3)
    assert await coordinator.agent_depth("root") == 0
    assert await coordinator.agent_depth("agent-0") == 1
    assert await coordinator.agent_depth("agent-1") == 2
    assert await coordinator.agent_depth(leaf) == 3


@pytest.mark.asyncio
async def test_total_agent_count() -> None:
    coordinator = AgentCoordinator()
    await _register_chain(coordinator, 4)
    assert await coordinator.total_agent_count() == 5


@pytest.mark.asyncio
async def test_agent_cap_error_none_within_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    coordinator = AgentCoordinator()
    # Isolate depth-cap behavior from the (lower) concurrency cap -- this test
    # is about depth, not how many of the chain happen to still be active.
    monkeypatch.setattr("strix.tools.agents_graph.tools.DEFAULT_MAX_CONCURRENT_AGENTS", 100)
    leaf = await _register_chain(coordinator, DEFAULT_MAX_AGENT_DEPTH - 1)
    assert await _agent_cap_error(coordinator, leaf) is None


@pytest.mark.asyncio
async def test_agent_cap_error_at_depth_limit_redirects_to_own_task() -> None:
    coordinator = AgentCoordinator()
    leaf = await _register_chain(coordinator, DEFAULT_MAX_AGENT_DEPTH)
    error = await _agent_cap_error(coordinator, leaf)
    assert error is not None
    assert "depth limit" in error.lower()
    # Regression: must not read as "perform the blocked sub-step yourself".
    assert "YOUR OWN assigned task" in error
    assert "does NOT mean" in error


@pytest.mark.asyncio
async def test_agent_cap_error_at_total_limit_redirects_to_own_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = AgentCoordinator()
    await coordinator.register("root", "Root Agent", parent_id=None)
    monkeypatch.setattr("strix.tools.agents_graph.tools.DEFAULT_MAX_TOTAL_AGENTS", 1)
    error = await _agent_cap_error(coordinator, "root")
    assert error is not None
    assert "agent limit reached" in error.lower()
    assert "YOUR OWN assigned task" in error


@pytest.mark.asyncio
async def test_create_agent_refuses_spawn_past_depth_cap_without_calling_spawner() -> None:
    coordinator = AgentCoordinator()
    leaf = await _register_chain(coordinator, DEFAULT_MAX_AGENT_DEPTH)

    spawner_called = False

    async def _spawner(**_kwargs: Any) -> dict[str, Any]:
        nonlocal spawner_called
        spawner_called = True
        return {"success": True, "agent_id": "should-not-be-created"}

    ctx = ToolContext(
        context={
            "coordinator": coordinator,
            "agent_id": leaf,
            "spawn_child_agent": _spawner,
        },
        tool_name="create_agent",
        tool_call_id="call-1",
        tool_arguments="{}",
    )
    result: str = await create_agent.on_invoke_tool(
        ctx, json.dumps({"name": "Helper", "task": "do something"})
    )
    parsed = json.loads(result)

    assert parsed["success"] is False
    assert "depth limit" in parsed["error"].lower()
    assert spawner_called is False


@pytest.mark.asyncio
async def test_create_agent_allows_spawn_one_level_below_cap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The exact boundary that was previously off by one: a grandchild of
    root (depth 2, one level short of the default cap of 3) must still be
    able to spawn a helper.
    """
    coordinator = AgentCoordinator()
    # Isolate depth-cap behavior from the (lower) concurrency cap, as above.
    monkeypatch.setattr("strix.tools.agents_graph.tools.DEFAULT_MAX_CONCURRENT_AGENTS", 100)
    leaf = await _register_chain(coordinator, DEFAULT_MAX_AGENT_DEPTH - 1)

    spawned_ids: list[str] = []

    async def _spawner(**kwargs: Any) -> dict[str, Any]:
        spawned_ids.append(kwargs["name"])
        return {"success": True, "agent_id": "new-child"}

    ctx = ToolContext(
        context={
            "coordinator": coordinator,
            "agent_id": leaf,
            "spawn_child_agent": _spawner,
        },
        tool_name="create_agent",
        tool_call_id="call-1",
        tool_arguments="{}",
    )
    result: str = await create_agent.on_invoke_tool(
        ctx, json.dumps({"name": "Helper", "task": "do something"})
    )
    parsed = json.loads(result)

    assert parsed["success"] is True
    assert spawned_ids == ["Helper"]


@pytest.mark.asyncio
async def test_active_agent_count_ignores_completed_agents() -> None:
    coordinator = AgentCoordinator()
    await coordinator.register("root", "Root Agent", parent_id=None)
    await coordinator.register("agent-0", "Agent 0", parent_id="root")
    await coordinator.set_status("agent-0", "completed")
    assert await coordinator.active_agent_count() == 1
    assert await coordinator.total_agent_count() == 2


@pytest.mark.asyncio
async def test_agent_cap_error_at_concurrency_limit_is_retryable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = AgentCoordinator()
    await coordinator.register("root", "Root Agent", parent_id=None)
    monkeypatch.setattr("strix.tools.agents_graph.tools.DEFAULT_MAX_CONCURRENT_AGENTS", 1)
    error = await _agent_cap_error(coordinator, "root")
    assert error is not None
    assert "concurrent" in error.lower()
    # Regression guard: unlike the depth/total caps, this one must NOT tell
    # the agent to abandon the delegation -- a finished sibling frees a slot.
    assert "do NOT abandon" in error


@pytest.mark.asyncio
async def test_agent_cap_error_frees_slot_when_sibling_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    coordinator = AgentCoordinator()
    await coordinator.register("root", "Root Agent", parent_id=None)
    await coordinator.register("agent-0", "Agent 0", parent_id="root")
    monkeypatch.setattr("strix.tools.agents_graph.tools.DEFAULT_MAX_CONCURRENT_AGENTS", 2)
    assert await _agent_cap_error(coordinator, "root") is not None
    await coordinator.set_status("agent-0", "completed")
    assert await _agent_cap_error(coordinator, "root") is None


def test_default_caps_are_positive() -> None:
    assert DEFAULT_MAX_AGENT_DEPTH > 0
    assert DEFAULT_MAX_TOTAL_AGENTS > 0
    assert DEFAULT_MAX_CONCURRENT_AGENTS > 0
