// Defines local slash-command responses for the PatchPilot UI.
export const HELP_MESSAGE = [
  "Available commands:",
  "/help - Show local UI commands.",
  "/status - Show current run status and limits.",
  "/clear - Clear the message stream.",
  "",
  "PatchPilot can inspect files, search text, run allowlisted commands, show git status/diff, and edit sandbox files after approval.",
].join("\n");

export function getLocalCommand(text) {
  const command = text.trim().toLowerCase();

  if (!command.startsWith("/")) return null;

  return command;
}

export function buildStatusMessage({
  agentRunning,
  limits,
  messageCount,
  pendingApproval,
  runProgress,
  status,
}) {
  return [
    `Status: ${status}`,
    `Run state: ${agentRunning ? "running" : runProgress.status}`,
    `Steps: ${runProgress.stepsUsed} / ${limits.maxSteps}`,
    `Tool calls: ${runProgress.toolCallsUsed} / ${limits.maxToolCalls}`,
    `Model calls: ${runProgress.modelCalls}`,
    `Pending approval: ${pendingApproval ? "yes" : "no"}`,
    `Messages: ${messageCount}`,
  ].join("\n");
}

export function handleLocalCommand(command, context) {
  if (command === "/help") {
    context.setDraft("");
    context.addLocalMessage("backend", HELP_MESSAGE, "message");
    context.setStatus("Help shown");
    return true;
  }

  if (command === "/status") {
    context.setDraft("");
    context.addLocalMessage(
      "backend",
      buildStatusMessage({
        agentRunning: context.agentRunning,
        limits: context.limits,
        messageCount: context.messageCount,
        pendingApproval: context.pendingApproval,
        runProgress: context.runProgress,
        status: context.status,
      }),
      "message"
    );
    context.setStatus("Status shown");
    return true;
  }

  return false;
}
