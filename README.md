# PatchPilot

PatchPilot is a custom Python ReAct software-developer agent with a React control UI. The current goal is to build one safe, understandable student-owned developer agent first, then connect it to the class-wide multi-agent hub later when the shared protocol is decided.

## What PatchPilot Does

- Uses a homemade ReAct loop: `Thought`, `Action`, `Observation`, `Final Answer`.
- Uses homemade function-calling by parsing `Action: tool_name(...)`.
- Calls an LLM API from Python for reasoning.
- Inspects files, reads files, searches files, shows git status/diff, edits files, and runs allowed commands.
- Requires frontend approval before file edits or shell commands.
- Shows live run progress in the UI: status, steps, tool calls, and model calls.

## Project Structure

- `backend/` contains the Python agent runtime and FastAPI server.
- `frontend/` contains the Vite/React control UI.
- `test_project/` is the sandbox folder PatchPilot is allowed to work inside.
- `agents.md` is the detailed project handoff guide for future sessions.
- `.env` stores local secrets and should stay untracked.

## Safety Model

PatchPilot is designed to control code tasks, but not with unlimited power.

- File access is restricted to the configured sandbox folder.
- `run_bash` uses an allowlist and `shell=False`.
- Dangerous actions require user approval in the UI.
- Runs are limited by `MAX_STEPS` and `MAX_TOOL_CALLS`.
- Commands have a timeout and output limit.
- Command requests are logged.

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

## Useful UI Commands

- `/clear` clears the current message stream.

## Verify

Backend syntax check:

```bash
python -m compileall backend
```

Frontend checks:

```bash
cd frontend
npm.cmd run lint
npm.cmd run build
```

## Next Steps

1. Add backend tests for parser behavior, safe paths, allowed commands, and blocked commands.
2. Clean `edit_file` so it is fully API/UI-friendly.
3. Add structured run logs for task, start time, final answer, steps, tools, and model calls.
4. Add `/help` and `/status` frontend commands.
5. Add persistent storage so messages survive backend restarts.
6. Later add the class-hub integration layer for shared agent communication.
