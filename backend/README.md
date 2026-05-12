<!-- Explains the PatchPilot backend runtime and API. -->
# PatchPilot Backend

This folder contains the Python runtime and FastAPI server for PatchPilot.

## Purpose

The backend runs a custom ReAct software-developer agent. It owns the model call, prompt, action parser, tool registry, safety checks, streaming events, and approval flow.

## Important Files

- `backend_server.py` exposes the FastAPI API used by the frontend.
- `agent_stream.py` runs the streaming ReAct loop for the web UI.
- `agent.py` runs the CLI ReAct loop.
- `context_window.py` compacts old conversation history before model calls.
- `model_client.py` calls the LLM API.
- `model_results.py` normalizes model results, token usage, observations, and stopped answers.
- `prompts.py` defines PatchPilot's system prompt.
- `parser.py` parses homemade `Action: tool_name(...)` calls.
- `run_logger.py` writes structured JSONL records for completed UI and CLI runs.
- `run_state.py` owns active web-run state, cancellation flags, pending approvals, and cleanup.
- `stream_events.py` builds stream event payloads and SSE chunks.
- `trace_utils.py` builds shared compact trace entries for CLI and web run logs.
- `conversation_store.py` stores saved UI conversations in `data/conversations.json`.
- `tool_registry.py` maps tool names to Python functions.
- `tools/` contains focused modules for safety checks, file tools, command execution, and git inspection.
- `config.py` stores model, step, tool, command, and sandbox limits.

## API Routes

- `GET /state` returns agents, messages, and configured limits.
- `POST /reset` clears messages and resets agent state.
- `POST /run-agent-stream` starts a streamed PatchPilot run.
- `POST /approve-tool` approves a pending tool call.
- `POST /stop-run` requests a running stream to stop.
- `POST /reject-tool` rejects a pending tool call.
- `GET /conversations` lists saved conversation summaries.
- `GET /conversations/{conversation_id}` loads one saved conversation into the current UI state.
- `POST /conversations/archive-current` saves the current UI message stream and clears it.
- `DELETE /conversations/{conversation_id}` removes one saved conversation.

## ReAct Flow

PatchPilot follows this loop:

1. Build a system prompt with available tools.
2. Send conversation messages to the model.
3. Parse the model response for `Action: tool_name(...)`.
4. Run the matching Python tool if allowed.
5. Feed the observation back to the model.
6. Stop when the model returns `Final Answer:`.

The streaming loop also emits progress data:

- current step
- max steps
- model calls
- tool calls
- max tool calls

## CLI Flow

The backend also includes a terminal runner:

- `main.py` is the CLI entry point.
- `agent.py` runs the non-streaming CLI ReAct loop.
- The CLI loop uses the same model client, prompt, homemade parser, tool registry, sandboxed tools, step limit, and tool call limit as the web flow.
- The CLI loop asks for terminal approval before running `run_bash` or `edit_file`.
- The React UI does not use `agent.py`; UI runs go through `agent_stream.py` and `backend_server.py`.

From the project root:

```bash
python -m backend.main
```

From the backend folder:

```bash
python main.py
```

## Safety Model

- File access is restricted to `PROJECT_DIR`.
- `run_bash` uses an allowlist and `shell=False`.
- `run_bash` validates pytest and git arguments before execution.
- File tool output is truncated before returning to the model or UI.
- Search skips large files and noisy generated folders.
- `run_bash` and `edit_file` require frontend approval in the web flow and terminal approval in the CLI flow.
- Commands have a timeout.
- Command output is truncated.
- Command requests are logged.
- Completed, stopped, and rejected runs are logged to `logs/runs.jsonl`.
- Runs stop at `MAX_STEPS` or `MAX_TOOL_CALLS`.
- Terminal-state stream runs are removed from active run state to avoid stale run state.
- Active stream state is centralized in `run_state.py` so `agent_stream.py` can focus on orchestration.
- Stream event formatting is centralized in `stream_events.py`.
- CLI and web trace compaction share `trace_utils.py`.
- CLI and web observation tagging and token usage accumulation share `model_results.py`.
- Expected model, tool, subprocess, filesystem, and logging failures are handled with safe error messages.
- Transient model API errors use a short retry/backoff before failing safely.
- Long runs compact older conversation history before model calls to reduce context-length failures.
- Run logs include token usage totals, context compaction counts, and compact per-step traces.
- Observations are tagged as success, error, or blocked.
- Stream endpoints request cancellation if a browser disconnects mid-run.
- Stop requests are checked before tool execution, and approved pending tools are cleared before running.
- Stopped runs include the latest assistant message as a best-effort partial answer when available.

Allowed command families are intentionally narrow:

```txt
python <script.py>
py <script.py>
python -m pytest
pytest
git status
git diff
git log
git show
git branch
```

## Configuration

Edit `config.py` to change:

- `MODEL_NAME`
- `MODEL_MAX_RETRIES`
- `MODEL_RETRY_BACKOFF_SECONDS`
- `MAX_CONTEXT_CHARS`
- `CONTEXT_KEEP_RECENT_MESSAGES`
- `MAX_CONTEXT_MESSAGE_CHARS`
- `MAX_STEPS`
- `MAX_TOOL_CALLS`
- `COMMAND_TIMEOUT_SECONDS`
- `MAX_COMMAND_OUTPUT_CHARS`
- `PROJECT_DIR`
- `COMMAND_LOG_FILE`
- `RUN_LOG_FILE`
- `CONVERSATION_STORE_FILE`

Secrets should live in the project root `.env` file:

```env
OPENAI_API_KEY=your_api_key_here
```

Use `.env.example` as the safe template. Do not commit real secrets.

## Run

From the project root:

```bash
uvicorn backend.backend_server:app --reload
```

## Run With Docker

From the project root:

```bash
docker compose up -d --build backend
```

Docker Desktop must be running before this command works.

Backend URL:

```txt
http://127.0.0.1:8000/
```

## Current Limitation

The backend is currently single-user local state. `agents`, `messages`, and active stream runs are process-global, so multiple browsers or users can share history and approval state. Scope state by session/client before using PatchPilot as a multi-user service or connecting it to a class-wide hub.

## Verify

From the project root:

```bash
python -m compileall backend
```

Run backend tests with a project-local temp folder on Windows:

```bash
.\.venv\Scripts\python.exe -m pytest tests --basetemp .pytest_tmp_run
```

## Next Backend Work

1. Add tests for `parser.py`.
2. Add tests for `safe_path`.
3. Add tests for allowed and blocked commands.
4. Done: Clean `edit_file` so it is fully API/UI-friendly.
5. Done: Add structured run logs for task, final answer, steps, tools, and model calls.
6. Done: Split runtime tools into the `tools/` package.
7. Done: Add targeted tests for split command and file tool modules.
8. Done: Tighten command/file tool safety with stricter args, truncation, sorted listing, and safer edits.
9. Done: Add a stop endpoint and active-run cleanup for terminal stream states.
10. Done: Harden error handling for model calls, stream cleanup, parser/final detection, file tools, command tools, git tools, and stream parsing.
11. Done: Add token usage logging, compact trace logging, tagged observations, and disconnect cancellation.
12. Done: Add short retry/backoff handling for transient model API errors.
13. Done: Close approval/stop race gaps and include best-effort partial answers on stopped runs.
14. Done: Split active stream run state into `run_state.py`.
15. Done: Split stream event formatting into `stream_events.py`.
16. Done: Split shared model-result handling into `model_results.py`.
17. Done: Split shared trace compaction into `trace_utils.py`.
18. Done: Add deterministic context-window compaction before model calls.
19. Done: Add JSON-backed saved conversation storage and conversation API endpoints.
20. Later scope backend state by session/client before multi-user or class-hub use.
