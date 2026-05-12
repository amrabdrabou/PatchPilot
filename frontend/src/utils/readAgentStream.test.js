// Verifies backend SSE stream reading helpers.
import { afterEach, describe, expect, test, vi } from "vitest";

import { readAgentStream } from "./readAgentStream.js";

function createStreamResponse(chunks, options = {}) {
  const encoder = new TextEncoder();

  return {
    body: new ReadableStream({
      start(controller) {
        for (const chunk of chunks) {
          controller.enqueue(encoder.encode(chunk));
        }

        controller.close();
      },
    }),
    ok: options.ok ?? true,
    status: options.status ?? 200,
  };
}

function createHandlers() {
  const calls = {
    appended: [],
    currentRunIds: [],
    finished: [],
    pendingApprovals: [],
    progressEvents: [],
  };

  return {
    calls,
    handlers: {
      appendMessageText: (traceId, text) => calls.appended.push({ traceId, text }),
      finishTraceMessage: (traceId, text, label) =>
        calls.finished.push({ label, text, traceId }),
      setCurrentRunId: (runId) => calls.currentRunIds.push(runId),
      setPendingApproval: (approval) => calls.pendingApprovals.push(approval),
      updateProgressFromEvent: (event) => calls.progressEvents.push(event),
    },
  };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("readAgentStream", () => {
  test("dispatches trace, approval, and final events", async () => {
    const { calls, handlers } = createHandlers();
    const response = createStreamResponse([
      'data: {"type":"start","content":"Agent started.","run_id":"run-1"}\n\n',
      'data: {"type":"approval_required","content":"Needs approval","run_id":"run-1","approval_id":"approval-1","tool_name":"edit_file","arguments":["a.py"]}\n\n',
      'data: {"type":"final","content":"Final Answer: done","run_id":"run-1"}\n\n',
    ]);

    await readAgentStream(response, "trace-1", handlers);

    expect(calls.currentRunIds).toEqual(["run-1", "run-1", "run-1", null]);
    expect(calls.appended).toHaveLength(2);
    expect(calls.pendingApprovals[0].approvalId).toBe("approval-1");
    expect(calls.pendingApprovals.at(-1)).toBeNull();
    expect(calls.finished).toEqual([
      {
        label: "FINAL ANSWER",
        text: "done",
        traceId: "trace-1",
      },
    ]);
  });

  test("skips malformed events and reports an error line", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    const { calls, handlers } = createHandlers();
    const response = createStreamResponse(['data: {"type":\n\n']);

    await readAgentStream(response, "trace-1", handlers);

    expect(calls.appended).toEqual([
      {
        text: "\n[ERROR]\nMalformed stream event skipped.\n",
        traceId: "trace-1",
      },
    ]);
  });

  test("dispatches a trailing event without a final blank line", async () => {
    const { calls, handlers } = createHandlers();
    const response = createStreamResponse([
      'data: {"type":"final","content":"Final Answer: trailing","run_id":"run-1"}',
    ]);

    await readAgentStream(response, "trace-1", handlers);

    expect(calls.finished).toEqual([
      {
        label: "FINAL ANSWER",
        text: "trailing",
        traceId: "trace-1",
      },
    ]);
  });

  test("rejects failed responses", async () => {
    const { handlers } = createHandlers();
    const response = createStreamResponse([], { ok: false, status: 500 });

    await expect(readAgentStream(response, "trace-1", handlers)).rejects.toThrow(
      /Agent stream failed with status 500/
    );
  });
});
