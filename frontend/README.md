# PatchPilot Frontend

This folder contains the Vite/React control UI for PatchPilot.

The UI handles:

- task input
- live streamed ReAct steps
- collapsible step groups
- separate final answers
- approval prompts for tool calls
- run progress and limits
- `/clear`

Run from this folder:

```bash
npm.cmd run dev -- --host 127.0.0.1
```

Verify from this folder:

```bash
npm.cmd run lint
npm.cmd run build
```
