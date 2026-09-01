# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Strix is an open-source autonomous AI pentesting tool: a graph of LLM-driven agents that run against a target (local code, a URL, a GitHub repo, an API spec) inside a Docker sandbox, using a real offensive toolkit (HTTP proxy, browser, shell, Python exploit runtime) to find and validate vulnerabilities. Python 3.12+, built on the `openai-agents` SDK (`agents.sandbox.SandboxAgent`) with LiteLLM for multi-provider model routing.

## Commands

Dependency management is `uv`; there is no separate lockfile step beyond `uv sync`.

```bash
make setup-dev        # uv sync (full dev deps) + pre-commit install
uv run strix --target <target>       # run Strix from source (equivalent to installed `strix` CLI)

make format            # ruff format . (rewrites files)
make lint               # ruff check . --fix (rewrites files)
make type-check         # mypy strix/ then pyright strix/
make security            # bandit -r strix/ -c pyproject.toml
make check-all           # format + lint + type-check + security, in that order
make pre-commit          # uv run pre-commit run --all-files

uv run pytest                                  # full test suite
uv run pytest tests/test_execution_transient_retry.py           # one file
uv run pytest tests/test_execution_transient_retry.py::test_name -q  # one test
```

Notes:
- `make check-all`/`format`/`lint` **mutate files** (ruff format + `--fix`); they're not read-only checks.
- mypy runs in `strict = true` mode across `strix/`. Third-party libs without stubs (`litellm`, `docker`, `caido_sdk_client`, `reportlab`, `pypdf`, etc.) are allowlisted in `[[tool.mypy.overrides]]`.
- `pytest-asyncio` runs in `asyncio_mode = "auto"` — async tests don't need an explicit `@pytest.mark.asyncio`.
- Go 1.24.x is only needed for the Bubble Tea TUI sidecar (`strix/interface/tui/`) or building release wheels — editable/source installs run the TUI via `go run` and don't need a compiled binary. TUI-only commands: `make tui-build` / `make tui-test` / `make tui-lint`.
- The local web viewer's source is `strix/interface/viewer/frontend/` (Vite+React); its build output is *committed* to `strix/interface/viewer/static/` and shipped in the package — end users never run a JS build. If you touch the frontend source, rebuild with `make viewer` and commit both the source and the regenerated static output.
- `strix -n` / `--non-interactive` is the flag to use for any headless/scripted run — required for CI and for verifying behavior without a TUI attached. Exit codes: `0` clean, `1` fatal error, `2` vulnerabilities found.

## Architecture

### Execution flow

`strix/interface/main.py` is the entry point. It parses args (`strix/interface/cli_args.py`), then either launches the Bubble Tea TUI (`strix/interface/tui/` — Go binary + `tui/runtime.py` glue) or, for `--non-interactive`, calls `strix/interface/cli.py:run_cli`. Both paths converge on `strix/core/runner.py:run_strix_scan`, which:
1. Brings up the Docker sandbox for the scan (`strix/runtime/session_manager.py`, `docker_client.py`) and bootstraps the embedded Caido HTTP-intercept proxy inside it (`runtime/caido_bootstrap.py`).
2. Builds a single shared `RunConfig` (model, provider, sandbox handle) and a single shared `ReportUsageHooks` instance (`strix/core/hooks.py`) — both get passed by reference to *every* agent in the scan, root and children alike.
3. Builds the root agent (`strix/agents/factory.py:build_strix_agent`) and drives it via `strix/core/execution.py:run_agent_loop`.

`strix/core/execution.py` is the orchestration core: `run_agent_loop` drives one agent's SDK `Runner.run_streamed()` calls (with retry/backoff for transient and rate-limit errors), `spawn_child_agent` creates a new child as an independent `asyncio.Task`, and `respawn_subagents` reattaches to an in-progress agent tree on `--resume`. `strix/core/agents.py:AgentCoordinator` is the shared state machine tracking every agent's status, parent/child edges, and inter-agent mailboxes; it periodically snapshots to `.state/agents.json`/`agents.db` under the run directory so a scan can be resumed.

### Multi-agent orchestration ("graph of agents")

Agents spawn and message each other through tools in `strix/tools/agents_graph/tools.py` (`create_agent`, `agent_finish`, `wait_for_agents`, `send_message_to_agent`, `view_agent_graph`, `stop_agent`) — these are the model-visible surface for coordination, not something orchestrated externally. A few load-bearing, non-obvious details if you touch this area:
- `create_agent` carries a hard SDK-level tool-call timeout (`@function_tool(timeout=120)`); logic that needs to block for longer than that inside a tool call will get silently cancelled by the SDK, which then feeds the model a timeout error and lets it continue — see `strix/config/sequential_mode.py`'s module docstring for the two ways this bit us building `--sequential-agents` (it's a case study on why not to gate multi-agent concurrency inside a tool call).
- Concurrency control (`--sequential-agents`) is implemented via `RunHooks.on_llm_start`/`on_llm_end` (`ReportUsageHooks` in `strix/core/hooks.py`), which fire once per actual outbound model request rather than once per multi-turn SDK stream — that's the granularity that avoids deadlocking on long tool-call-driven waits like `wait_for_agents`.
- `on_llm_end` is only called by the SDK when a request actually returns a response — never on a transient failure/rate limit (which Strix retries constantly). Anything gating on that pair needs a safety-net release elsewhere (see the `finally` in `run_agent_loop`), or a single failed call permanently wedges the gate.

### Skills — two unrelated systems sharing the word

- `strix/skills/` — internal knowledge packs (`reconnaissance/`, `vulnerabilities/`, `frameworks/`, `technologies/`, `protocols/`, `tooling/`, `scan_modes/`, `coordination/`, `cloud/`, `custom/`) that pentest *agents* load at runtime via the `load_skill` tool to specialize themselves (e.g. an agent tasked with subdomain enumeration loads the `subfinder` skill). See `strix/skills/README.md` for the contribution format.
- `skills/` (repo root) — consumer-facing Agent Skills (SKILL.md format) that let *external* coding agents (Claude Code, Cursor, Codex) drive Strix itself (`penetration-testing-with-strix`, `managed-pentesting-with-strix`, `fix-security-vulnerabilities-with-strix`, `ci-security-scanning-with-strix`).

### Model routing and config

`strix/config/settings.py` uses `pydantic-settings`; all runtime config is env-var driven (`STRIX_LLM`, `LLM_API_KEY`/`OPENAI_API_KEY`, `LLM_API_BASE`, etc.), persisted to `~/.strix/cli-config.json` after first run. `strix/config/models.py:StrixProvider` resolves a `STRIX_LLM` model id to the right LiteLLM/OpenAI-compatible provider (handles per-prefix special cases like `ollama/`, `chatgpt/`, custom `auto/*` routing combos).

### Reporting and run artifacts

`strix/report/state.py:ReportState` is a per-scan singleton (`get_global_report_state()`) that accumulates SDK usage/cost, vulnerability findings, and writes everything to `strix_runs/<run-name>/`: `strix.log`, `run.json` (status, targets, `llm_usage`), `findings.sarif` (SARIF 2.1.0), `penetration_test_report.md`, `vulnerabilities/*.md`, plus `.state/agents.{json,db}` for resumability. `strix/report/pricing.py` and `hooks.py:ReportUsageHooks` handle cost estimation and budget/turn warning injection into agent input mid-run.

### Sandbox and tools

Every scan gets one Docker container (`ghcr.io/usestrix/strix-sandbox`) that all agents in that scan share, running the Caido proxy and exposing shell/filesystem capabilities to the SDK's `SandboxAgent`. Tool implementations live under `strix/tools/*` (one package per capability: `proxy`, `agent_browser`, `shell`, `apply_patch`, `reporting`, `notes`, `todo`, `web_search`, `view_image`, `thinking`, `respond`, `finish`) and are wired into an agent's toolset in `strix/agents/factory.py`, which differentiates root-agent vs child-agent construction and whitebox (local source) vs blackbox tool availability.
