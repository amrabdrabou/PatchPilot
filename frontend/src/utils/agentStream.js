// Translates backend stream events into UI-friendly values.
const TRACE_EVENT_TYPES = new Set([
  "start",
  "step",
  "assistant_message",
  "tool_call",
  "observation",
  "approval_required",
  "approval_decision",
  "error",
]);

export function isTraceEvent(event) {
  return TRACE_EVENT_TYPES.has(event.type);
}

export function formatTraceLine(event) {
  const formatters = {
    start: () => `[START] ${event.content}\n`,
    step: () => `\n[STEP] ${event.content}\n`,
    assistant_message: () => {
      const [traceContent] = event.content.split("Final Answer:");
      return `\n[THOUGHT / ACTION]\n${traceContent.trim()}\n`;
    },
    tool_call: () => `\n[TOOL CALL] ${event.content}\n`,
    observation: () => `\n[OBSERVATION]\n${event.content}\n`,
    approval_required: () => `\n[APPROVAL REQUIRED]\n${event.content}\n`,
    approval_decision: () => `\n[APPROVAL DECISION]\n${event.content}\n`,
    error: () => `\n[ERROR]\n${event.content}\n`,
  };

  return formatters[event.type]?.() ?? "";
}

export function extractFinalAnswer(content) {
  const marker = "Final Answer:";

  if (!content.includes(marker)) return content;

  return content.split(marker).at(-1).trim();
}

export function buildPendingApproval(event, traceId) {
  return {
    runId: event.run_id,
    approvalId: event.approval_id,
    toolName: event.tool_name,
    arguments: event.arguments,
    traceId,
  };
}
