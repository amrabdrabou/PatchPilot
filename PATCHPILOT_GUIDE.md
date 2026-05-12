<!-- Documents PatchPilot architecture, safety rules, and roadmap. -->
# PatchPilot Project Guide

PatchPilot is a custom Python ReAct software-developer agent with a React control UI. The goal is to build one safe, understandable developer agent first, then later connect it to the class-wide multi-agent hub when the shared protocol is decided.

## Current Goal

- Build PatchPilot as one reliable student-owned developer agent.
- Keep the agent fully Python-based with our own ReAct loop and homemade action parsing.
- Use API calls to an LLM provider for reasoning, but do not use Codex, Cursor, Claude Code, OpenCode, or similar tools inside the agent runtime.
- Let the agent inspect, edit, and test code only through controlled tools.
- Keep human approval and safety limits around dangerous actions.

Do not implement PatchPilot by calling Codex, Cursor, Claude Code, OpenCode, or another coding-agent runtime.

PatchPilot must keep its own Python ReAct loop, homemade action parser, controlled tools, and approval system.

## Architecture

- `backend/` contains the Python runtime:
  - `agent.py` has the CLI ReAct loop.
  - `agent_stream.py` has the streaming ReAct loop used by the web UI.
  - `backend_server.py` exposes the FastAPI endpoints.
  - `model_client.py` calls the LLM API.
  - `model_results.py` normalizes model results, token usage, observations, and stopped answers.
  - `parser.py` parses homemade `Action: tool_name(...)` calls.
  - `prompts.py` defines PatchPilot's system prompt.
  - `run_logger.py` writes structured JSONL records for completed UI and CLI runs.
  - `run_state.py` owns active web-run state, cancellation flags, pending approvals, and cleanup.
  - `stream_events.py` builds stream event payloads and compact trace entries.
  - `tool_registry.py` maps tool names to Python functions.
  - `tools/` contains focused runtime tool modules:
    - `safety.py` handles sandbox paths and command allowlists.
    - `file.py` implements file listing, reading, search, and edit tools.
    - `command.py` runs approved commands and writes command audit logs.
    - `git.py` implements read-only git inspection tools.
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
- Running web runs can be stopped by the user at the next safe checkpoint.
- When the run finishes, steps collapse and the final answer appears separately in white text.
- The message stream auto-scrolls to new output.
- `/clear` clears messages instead of being sent to the model.
- `/help` and `/status` are handled locally instead of being sent to the model.
- The UI shows real run progress:
  - status
  - steps used / max steps
  - tool calls used / max tool calls
  - model calls
- Stream runs request cancellation if the browser disconnects mid-stream.
- Run logs include token usage totals and a compact per-step trace.
- Observations are tagged as success, error, or blocked so the model can react more reliably.
- CLI and web runs share model-result normalization and observation tagging through `backend/model_results.py`.
- Stop requests are checked before tool execution, and approved pending tools are cleared before running.
- Stopped runs include the latest assistant message as a best-effort partial answer when available.
- `run_bash` uses an allowlist and `shell=False`.
- `run_bash` validates allowed pytest and git arguments instead of trusting every flag.
- File tool output is truncated before returning to the model or UI.
- `search_files` skips large files and noisy generated folders.
- `edit_file` rejects empty `old_text` so edits cannot insert text accidentally.
- `run_bash` and `edit_file` require frontend approval before execution.
- The CLI loop also asks for terminal approval before `run_bash` or `edit_file`.
- Completed, stopped, and rejected runs are logged to `logs/runs.jsonl`.
- Finished, stopped, and rejected stream runs are removed from `ACTIVE_RUNS`.
- Active stream state is centralized in `backend/run_state.py` so the streaming loop can stay focused on orchestration.
- Stream event payload and trace helpers are centralized in `backend/stream_events.py`.
- Transient model API errors use a short retry/backoff before the run fails safely.
- Docker Compose bind-mounts `backend/`, `frontend/`, `logs/`, and `test_project/`.
- The backend Docker image installs `git`, and Compose mounts `.git` read-only so `git_diff` and `git_status` can inspect sandbox changes.
- Backend/frontend source edits usually need a container restart, not an image rebuild; dependency or Dockerfile changes still need rebuilds.

## CLI Behavior

- `backend/main.py` is the terminal entry point for the CLI agent.
- `backend/agent.py` runs the non-streaming CLI ReAct loop.
- The CLI loop uses the same model client, prompt builder, action parser, tool registry, sandboxed tools, max step limit, and max tool call limit as the web flow.
- The CLI loop asks for terminal approval before running `run_bash` or `edit_file`.
- The web UI does not use `backend/agent.py`; it uses `backend/agent_stream.py` through the FastAPI server.

## Current Limitation

- PatchPilot is currently designed for one local developer using one trusted backend instance.
- The FastAPI app still uses process-global state for `agents`, `messages`, and active stream runs.
- Multiple browser tabs or users can share message history, run state, and approval state.
- This is acceptable for the current local Del 1 workflow, but it is not multi-user safe.
- Before class-hub integration, state should be scoped by session/client or moved into a persistent store with explicit ownership.

## Safety Rules

- PatchPilot must only work inside the configured sandbox project folder.
- PatchPilot's runtime tools must only inspect or modify files inside `test_project/`.
- The developer may edit `backend/`, `frontend/`, tests, and docs when working on PatchPilot itself, but PatchPilot the agent must remain sandboxed to `test_project/`.
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
- Choose the safest explicit behavior when a type checker, linter, or runtime edge case is uncertain.
- Use error-handling best practices: catch expected external failures, return clear safe errors, clean up run state, and keep logging failures from breaking user workflows.
- Keep code clean: small functions, clear names, limited side effects, and no unrelated refactors.
- Add short purpose comments to files we work on when useful.
- Avoid noisy comments that restate obvious code.
- Verify every meaningful change with the smallest useful command.
- For frontend changes, run `npm.cmd run lint` and `npm.cmd run build`.
- For backend Python changes, run `python -m compileall backend`.
- On Windows, run backend tests with `.\.venv\Scripts\python.exe -m pytest tests --basetemp .pytest_tmp_run` if the default pytest temp folder is blocked.
- Add each new runtime tool in its own focused file inside `backend/tools/`, then export it through `backend/tools/__init__.py` and register it in `tool_registry.py`.
- Protect user work and never revert unrelated changes unless explicitly asked.
- After every meaningful improvement, update this guide so the next session understands the current project state.
- Do not delete completed roadmap items just because they are done. Mark them as done and keep the history useful.

## Best Next Steps

1. Done: Add backend tests:
   - `tests/test_parser.py`
   - `tests/test_tools.py`
   - allowed command tests
   - blocked command tests
   - safe path tests
2. Done: Add Docker support for running backend and frontend in the background.
3. Done: Tighten `safe_path` so sandbox checks use real path ancestry instead of string prefix matching.
4. Done: Remove remaining `shell=True` from `git_status` and `git_diff`.
5. Done: Install Git in the backend container and mount `.git` read-only so PatchPilot can run `git_diff`.
6. Done: Clean `edit_file` so it is fully API/UI-friendly and does not print CLI approval text.
7. Done: Split `backend/tools.py` into focused modules after safety cleanup.
8. Done: Add run logs for task, start time, final answer, steps, tools, and model calls.
9. Done: Add targeted tests for split command and file tool modules.
10. Done: Tighten command/file tool safety with stricter args, truncation, sorted listing, and safer edits.
11. Done: Add a stop endpoint and active-run cleanup for terminal stream states.
12. Done: Harden error handling for model calls, stream cleanup, parser/final detection, file tools, command tools, git tools, and stream parsing.
13. Done: Add token usage logging, compact trace logging, tagged observations, and disconnect cancellation.
14. Done: Add short retry/backoff handling for transient model API errors.
15. Done: Close approval/stop race gaps and include best-effort partial answers on stopped runs.
16. Done: Split active stream run state into `backend/run_state.py`.
17. Done: Split stream event and trace helpers into `backend/stream_events.py`.
18. Done: Split shared model-result normalization into `backend/model_results.py`.
19. Done: Add frontend commands:
   - Done: `/help`
   - Done: `/status`
   - Done: `/clear`
20. Later add frontend tests for local commands, stream rendering, and approval controls.
21. Later add persistent storage with SQLite or JSON so messages survive backend restarts.
22. Later scope backend state by session/client before multi-user or class-hub use.
23. Later prepare a class-hub integration layer for agent registration, shared message format, and task handoff.

## Assignment Fit

- Del 1 is the current focus: custom ReAct agent, bash commands through homemade function calling, no framework-based agent runtime.
- Multi-agent class collaboration is future work. PatchPilot should be solid and safe before connecting to other student agents.
