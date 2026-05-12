// Reads backend SSE responses and dispatches parsed agent events.
import {
  buildPendingApproval,
  extractFinalAnswer,
  formatTraceLine,
  isTraceEvent,
} from "./agentStream.js";

function parseStreamEvent(part) {
  if (!part.startsWith("data: ")) return null;

  return JSON.parse(part.replace("data: ", ""));
}

function handleStreamPart(part, traceId, handlers) {
  let event;

  try {
    event = parseStreamEvent(part);
  } catch (error) {
    console.error(error);
    handlers.appendMessageText(
      traceId,
      "\n[ERROR]\nMalformed stream event skipped.\n"
    );
    return;
  }

  if (!event) return;

  if (event.run_id) {
    handlers.setCurrentRunId(event.run_id);
  }

  handlers.updateProgressFromEvent(event);

  if (isTraceEvent(event)) {
    handlers.appendMessageText(traceId, formatTraceLine(event));
  }

  if (event.type === "approval_required") {
    handlers.setPendingApproval(buildPendingApproval(event, traceId));
  }

  if (event.type === "approval_decision") {
    handlers.setPendingApproval(null);
  }

  if (event.type === "final" || event.type === "stopped") {
    const label = event.type === "final" ? "FINAL ANSWER" : "STOPPED";

    handlers.finishTraceMessage(
      traceId,
      extractFinalAnswer(event.content),
      label
    );
    handlers.setPendingApproval(null);
    handlers.setCurrentRunId(null);
  }
}

export async function readAgentStream(response, traceId, handlers) {
  if (!response.ok) {
    throw new Error(`Agent stream failed with status ${response.status}`);
  }

  if (!response.body) {
    throw new Error("No response stream received.");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");

  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();

    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    const parts = buffer.split("\n\n");
    buffer = parts.pop();

    for (const part of parts) {
      handleStreamPart(part, traceId, handlers);
    }
  }

  if (buffer.trim()) {
    handleStreamPart(buffer, traceId, handlers);
  }
}
