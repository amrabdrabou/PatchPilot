<!-- Explains the PatchPilot frontend structure and workflow. -->
# PatchPilot Frontend

This folder contains the Vite/React control UI for PatchPilot.

The UI handles:

- task input
- live streamed ReAct steps
- collapsible step groups
- separate final answers
- approval prompts for tool calls
- stop requests for running web runs
- run progress and limits
- `/clear`
- `/help`
- `/status`

Run from this folder:

```bash
npm.cmd run dev -- --host 127.0.0.1
```

Run with Docker from the project root:

```bash
docker compose up -d --build frontend
```

Verify from this folder:

```bash
npm.cmd run lint
npm.cmd run build
```

`npm.cmd run build` runs the Vite production build and writes generated files to `dist/`.

## Later Tests

Later add frontend tests for local commands like `/help`, `/status`, and `/clear`, plus stream rendering and approval controls.
