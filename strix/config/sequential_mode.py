"""Sequential agent execution support.

``--sequential-agents`` exists to stop multiple Strix agents from hitting
the model API at the same time -- fewer 429s, lower peak cost -- not to
force a strict "one branch of the agent tree at a time" ordering. Two
earlier designs aimed for the stricter version and both broke:

1. Holding a semaphore around each agent's whole ``Runner.run_streamed()``
   call. That deadlocked outright: a single call isn't one HTTP request,
   it's a turn loop that can include tool calls blocking for minutes
   (``wait_for_agents`` chief among them), so whichever agent grabbed the
   semaphore first held it hostage for its entire turn sequence and
   starved every other agent, including its own children.

2. Making the ``create_agent`` tool call itself block until the spawned
   child finished its work, so a parent's turn wouldn't advance until its
   child was done. This one is subtler: `create_agent` carries an SDK-level
   ``timeout=120`` (see ``strix/tools/agents_graph/tools.py``). Real
   recon/scan work routinely runs longer than that. When the wait outlasted
   120s, the SDK cancelled the *tool call* out from under it and fed the
   model a timeout error -- letting the parent immediately spawn another
   child -- while the first child's task, already created and independent
   of the tool call that spawned it, kept running completely unsupervised.
   Net effect: worse than doing nothing, since it looked like it was
   enforcing ordering right up until a child ran long.

What's actually being gated below is the one thing that matters for the
stated goal -- concurrent model calls -- via the SDK's ``on_llm_start`` /
``on_llm_end`` run hooks (see ``ReportUsageHooks`` in ``strix/core/hooks.py``),
which fire once per actual outbound model request rather than once per
multi-turn stream. That gives the right granularity: an agent only holds
the gate for the span of its own request, never while running a local
tool or blocked waiting on another agent, so nesting (parent -> child ->
grandchild) can't self-deadlock the way approach #1 did.

The one hazard specific to hooks: ``on_llm_end`` is only called when the
request actually returns a response (see ``run_internal/run_loop.py``) --
not on a transient error, a rate limit, or a dropped connection, all of
which Strix already retries. Acquire-in-start / release-in-end alone would
leak the gate's one permit on the first such failure and wedge the whole
scan. ``run_agent_loop`` (``strix/core/execution.py``) closes that gap with
an unconditional release in its ``finally``, covering the entire life of
one agent regardless of how many retries or turns it took internally.

Known tradeoff -- prompt-cache TTL: this gate round-robins a single lock
across every active agent, so the wall-clock gap between one specific
agent's own successive calls grows with however many other agents are
queued ahead of it. Strix enables Claude prompt caching by default
(``STRIX_PROMPT_CACHE``, see ``strix/core/inputs.py``'s
``cache_control_injection_points``), which needs an agent's calls to land
within the cache's TTL (a few minutes) to keep hitting. With enough
concurrent agents, the round-robin gap can exceed that TTL, so an agent's
next call reprocesses its full system prompt/skills/tool definitions from
scratch instead of hitting cache -- working against this flag's own
"lower peak cost" goal even as it achieves "fewer 429s". The gate has no
cache-TTL awareness today (no priority for an agent close to expiring its
cache); this is a real scheduling problem, not a bug, and is a candidate
for a future fairness policy rather than something acquire()/release()
alone can fix.
"""

from __future__ import annotations

import asyncio
from typing import Any


class SequentialLLMGate:
    """Serializes actual model requests across every agent in the scan.

    Reentrant per agent id: an agent that still "holds" the gate from a
    request whose ``on_llm_end`` never fired (a failed/retried call) can
    re-acquire it for its next attempt without waiting on itself.
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._holder: str | None = None

    async def acquire(self, agent_id: str) -> None:
        if self._holder == agent_id:
            return
        await self._lock.acquire()
        self._holder = agent_id

    def release(self, agent_id: str) -> None:
        if self._holder != agent_id:
            return
        self._holder = None
        self._lock.release()


def create_llm_gate(enabled: bool) -> SequentialLLMGate | None:
    return SequentialLLMGate() if enabled else None


def release_llm_gate_if_held(context: dict[str, Any], agent_id: str) -> None:
    """Safety net: release the gate this agent may still hold, no matter how its
    run ended. See the module docstring for why ``on_llm_end`` alone isn't enough.
    """
    gate = context.get("sequential_llm_gate")
    if isinstance(gate, SequentialLLMGate):
        gate.release(agent_id)
