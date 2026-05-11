# PatchPilot Project Guide

PatchPilot is a custom Python ReAct software-developer agent with a React control UI. The goal is to build one safe, understandable developer agent first, then later connect it to the class-wide multi-agent hub when the shared protocol is decided.

## Current Goal

- Build PatchPilot as one reliable student-owned developer agent.
- Keep the agent fully Python-based with our own ReAct loop and homemade action parsing.
- Use API calls to an LLM provider for reasoning, but do not use Codex, Cursor, Claude Code, OpenCode, or similar tools inside the agent runtime.
- Let the agent inspect, edit, and test code only through controlled tools.
- Keep human approval and safety limits around dangerous actions.

## Architecture

- `backend/` contains the Python runtime:
  - `agent.py` has the CLI ReAct loop.
  - `agent_stream.py` has the streaming ReAct loop used by the web UI.
  - `backend_server.py` exposes the FastAPI endpoints.
  - `model_client.py` calls the LLM API.
  - `parser.py` parses homemade `Action: tool_name(...)` calls.
  - `prompts.py` defines PatchPilot's system prompt.
  - `tool_registry.py` maps tool names to Python functions.
  - `tools.py` implements file, search, edit, git, and safe command tools.
  - `config.py` stores model, step, tool, command, and sandbox limits.
- `frontend/` contains the Vite/React interface:
  - `App.jsx` composes the page.
  - `api/agentApi.js` contains backend HTTP calls.
  - `hooks/useAgentHub.js` owns UI state, streaming, `/clear`, approvals, and progress.
  - `utils/agentStream.js` formats stream events and final answers.
  - `utils/messages.js` handles local message IDs and timestamps.
  - `components/` contains focused UI sections.
- `test_project/` is the sandbox folder PatchPilot can inspect and modify.
- `.env` stores local secrets and must stay untracked.

## Current Behavior

- PatchPilot is the only active agent in the UI.
- The UI streams ReAct steps live.
- Steps are grouped in a collapsible section.
- While a run is executing, steps stay open.
- When the run finishes, steps collapse and the final answer appears separately in white text.
- The message stream auto-scrolls to new output.
- `/clear` clears messages instead of being sent to the model.
- The UI shows real run progress:
  - status
  - steps used / max steps
  - tool calls used / max tool calls
  - model calls
- `run_bash` uses an allowlist and `shell=False`.
- `run_bash` and `edit_file` require frontend approval before execution.

## Safety Rules

- PatchPilot must only work inside the configured sandbox project folder.
- Never expose or print `.env` secrets.
- Keep max steps, max tool calls, command timeout, and output truncation enabled.
- Prefer allowlists over denylists for command execution.
- Commands should stay read-only or test-oriented unless there is a clear approved need.
- Editing files and running commands must remain approval-gated.
- Avoid broad filesystem access.
- Avoid hidden background work that the user cannot review.

## Development Rules

- Build step by step and explain what is changing before edits.
- Keep changes scoped to the current request.
- Prefer existing architecture and local patterns.
- Keep code clean: small functions, clear names, limited side effects, and no unrelated refactors.
- Add short purpose comments to files we work on when useful.
- Avoid noisy comments that restate obvious code.
- Verify every meaningful change with the smallest useful command.
- For frontend changes, run `npm.cmd run lint` and `npm.cmd run build`.
- For backend Python changes, run `python -m compileall backend`.
- Protect user work and never revert unrelated changes unless explicitly asked.

## Best Next Steps

1. Add backend tests:
   - `tests/test_parser.py`
   - `tests/test_tools.py`
   - allowed command tests
   - blocked command tests
   - safe path tests
2. Clean `edit_file` so it is fully API/UI-friendly and does not print CLI approval text.
3. Add run logs for task, start time, final answer, steps, tools, and model calls.
4. Add frontend commands:
   - `/help`
   - `/status`
   - `/clear`
5. Later add persistent storage with SQLite or JSON so messages survive backend restarts.
6. Later prepare a class-hub integration layer for agent registration, shared message format, and task handoff.

## Assignment Fit

- Del 1 is the current focus: custom ReAct agent, bash commands through homemade function calling, no framework-based agent runtime.
- Multi-agent class collaboration is future work. PatchPilot should be solid and safe before connecting to other student agents.
