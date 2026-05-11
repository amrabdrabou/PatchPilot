# PatchPilot Backend

This folder contains the Python runtime and FastAPI server for PatchPilot.

## Purpose

The backend runs a custom ReAct software-developer agent. It owns the model call, prompt, action parser, tool registry, safety checks, streaming events, and approval flow.

## Important Files

- `backend_server.py` exposes the FastAPI API used by the frontend.
- `agent_stream.py` runs the streaming ReAct loop for the web UI.
- `agent.py` runs the CLI ReAct loop.
- `model_client.py` calls the LLM API.
- `prompts.py` defines PatchPilot's system prompt.
- `parser.py` parses homemade `Action: tool_name(...)` calls.
- `tool_registry.py` maps tool names to Python functions.
- `tools.py` implements file, search, edit, git, and safe command tools.
- `config.py` stores model, step, tool, command, and sandbox limits.

## API Routes

- `GET /state` returns agents, messages, and configured limits.
- `POST /messages` creates a manual message.
- `POST /reset` clears messages and resets agent state.
- `POST /run-agent-stream` starts a streamed PatchPilot run.
- `POST /approve-tool` approves a pending tool call.
- `POST /reject-tool` rejects a pending tool call.

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

## Safety Model

- File access is restricted to `PROJECT_DIR`.
- `run_bash` uses an allowlist and `shell=False`.
- `run_bash` and `edit_file` require frontend approval.
- Commands have a timeout.
- Command output is truncated.
- Command requests are logged.
- Runs stop at `MAX_STEPS` or `MAX_TOOL_CALLS`.

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
- `MAX_STEPS`
- `MAX_TOOL_CALLS`
- `COMMAND_TIMEOUT_SECONDS`
- `MAX_COMMAND_OUTPUT_CHARS`
- `PROJECT_DIR`
- `COMMAND_LOG_FILE`

Secrets should live in the project root `.env` file:

```env
OPENAI_API_KEY=your_api_key_here
```

## Run

From the project root:

```bash
uvicorn backend.backend_server:app --reload
```

## Verify

From the project root:

```bash
python -m compileall backend
```

## Next Backend Work

1. Add tests for `parser.py`.
2. Add tests for `safe_path`.
3. Add tests for allowed and blocked commands.
4. Clean `edit_file` so it is fully API/UI-friendly.
5. Add structured run logs for task, final answer, steps, tools, and model calls.
