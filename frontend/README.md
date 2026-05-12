<!-- Explains the PatchPilot frontend structure and workflow. -->
# PatchPilot Frontend

This folder contains the Vite/React control UI for PatchPilot.

The UI handles:

- task input
- multi-line task drafts with a client-side length cap
- live streamed ReAct steps
- collapsible step groups
- separate final answers
- approval prompts for tool calls
- stop requests for running web runs
- run progress and limits
- saved conversations in the left panel
- `/clear` archive-and-clear behavior
- `/help`
- `/status`

The main hub hook is split by responsibility:

- `hooks/useAgentHub.js` orchestrates backend calls, approvals, and stream handling.
- `hooks/useAgentMessages.js` owns local message creation and trace-message updates.
- `hooks/useRunProgress.js` owns stream progress and run-limit state.

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
npm.cmd run test
npm.cmd run build
```

`npm.cmd run test` uses Vitest. The current tests cover pure frontend utilities, approval and stream rendering components, and the main hub hook.

`npm.cmd run build` runs the Vite production build and writes generated files to `dist/`.

## Later Tests

Later add broader end-to-end UI tests around complete browser workflows.
