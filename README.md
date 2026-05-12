<!-- Introduces the PatchPilot project and local setup. -->
# PatchPilot

PatchPilot is a custom Python ReAct software-developer agent with a React control UI. The current goal is to build one safe, understandable student-owned developer agent first, then connect it to the class-wide multi-agent hub later when the shared protocol is decided.

## What PatchPilot Does

- Uses a homemade ReAct loop: `Thought`, `Action`, `Observation`, `Final Answer`.
- Uses homemade function-calling by parsing `Action: tool_name(...)`.
- Calls an LLM API from Python for reasoning.
- Inspects files, reads files, searches files, shows git status/diff, edits files, and runs allowed commands.
- Requires frontend approval before file edits or shell commands.
- Shows live run progress in the UI: status, steps, tool calls, and model calls.
- Supports stopping web runs at safe checkpoints.
- Logs token usage and compact per-step traces for completed, stopped, rejected, and handled-error runs.
- Retries transient model API failures before failing safely.
- Keeps active stream run state in a focused backend module.

## Project Structure

- `backend/` contains the Python agent runtime and FastAPI server.
- `frontend/` contains the Vite/React control UI.
- `test_project/` is the sandbox folder PatchPilot is allowed to work inside.
- `AGENTS.md` defines assistant operating rules for this repository.
- `PATCHPILOT_GUIDE.md` is the detailed PatchPilot architecture, behavior, and roadmap guide.
- `.env` stores local secrets and should stay untracked.

## Safety Model

PatchPilot is designed to control code tasks, but not with unlimited power.

- File access is restricted to the configured sandbox folder.
- `run_bash` uses an allowlist and `shell=False`.
- File output is truncated before returning to the model or UI.
- `search_files` skips large files and noisy generated folders.
- Dangerous actions require user approval in the UI.
- Runs are limited by `MAX_STEPS` and `MAX_TOOL_CALLS`.
- Commands have a timeout and output limit.
- Command requests are logged.
- Stream runs can be stopped by the user or cancelled after browser disconnects.
- Finished, stopped, and rejected stream runs are removed from active run state.
- Active stream run state is centralized so cancellation and cleanup are easier to test.
- Observations are tagged as success, error, or blocked.
- Expected model, tool, subprocess, filesystem, and logging failures return safe errors.

## Current Limitation

PatchPilot is currently designed for one local developer using one trusted backend instance. Backend state is still process-global, so multiple browsers or users can share message history, run state, and approval state. Scope state by session/client before multi-user or class-hub use.

Current allowed command families include:

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

## Setup

Create a `.env` file in the project root:

```env
OPENAI_API_KEY=your_api_key_here
```

Use `.env.example` as the template. Keep `.env` private.

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Install frontend dependencies:

```bash
cd frontend
npm install
```

## Run

Start the backend from the project root:

```bash
uvicorn backend.backend_server:app --reload
```

Start the frontend:

```bash
cd frontend
npm.cmd run dev -- --host 127.0.0.1
```

Open:

```txt
http://127.0.0.1:5173/
```

## Run With Docker

Make sure Docker Desktop is running first.

Build and start both services in the background:

```bash
docker compose up -d --build
```

Open:

```txt
http://127.0.0.1:5173/
```

Useful Docker commands:

```bash
docker compose logs -f
docker compose ps
docker compose down
```

Do not share the output of `docker compose config`; Docker may expand values from `.env` into that output.

## Useful UI Commands

- `/clear` clears the current message stream.
- `/help` shows available local UI commands.
- `/status` shows current run progress, limits, message count, and approval state.

## Logs

- Command requests are written to `logs/commands.log`.
- Completed, stopped, rejected, and handled-error UI/CLI runs are written to `logs/runs.jsonl`.
- Run logs include task, final answer, step/tool/model counts, token usage, tool usage, and compact trace entries.

## Verify

Backend syntax check:

```bash
python -m compileall backend
```

Backend tests on Windows:

```bash
.\.venv\Scripts\python.exe -m pytest tests --basetemp .pytest_tmp_run
```

Use a project-local `.pytest_tmp*` folder when Windows blocks pytest's default temp directory.

Frontend checks:

```bash
cd frontend
npm.cmd run lint
npm.cmd run build
```

`npm.cmd run build` runs the Vite production build and writes generated files to `frontend/dist/`.

## Next Steps

1. Done: Add backend tests for parser behavior, safe paths, allowed commands, blocked commands, stream lifecycle, run logging, and model retries.
2. Done: Clean `edit_file` so it is fully API/UI-friendly.
3. Done: Add structured run logs for task, start time, final answer, steps, tools, and model calls.
4. Done: Add `/help` and `/status` frontend commands.
5. Done: Add stop endpoint, active-run cleanup, tagged observations, token usage logging, compact traces, disconnect cancellation, and transient model retry/backoff.
6. Later add frontend tests for local commands, stream rendering, and approval controls.
7. Later add persistent storage so messages survive backend restarts.
8. Later scope backend state by session/client before multi-user or class-hub use.
9. Later add the class-hub integration layer for shared agent communication.
