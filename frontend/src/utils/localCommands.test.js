// Verifies local slash-command helpers.
import { describe, expect, test } from "vitest";

import {
  HELP_MESSAGE,
  buildStatusMessage,
  getLocalCommand,
  handleLocalCommand,
} from "./localCommands.js";

function createCommandContext(overrides = {}) {
  const calls = {
    messages: [],
    statuses: [],
    drafts: [],
  };

  return {
    calls,
    context: {
      addLocalMessage: (agentId, text, type) => {
        calls.messages.push({ agentId, text, type });
      },
      agentRunning: false,
      limits: {
        maxSteps: 10,
        maxToolCalls: 8,
      },
      messageCount: 3,
      pendingApproval: null,
      runProgress: {
        modelCalls: 2,
        status: "idle",
        stepsUsed: 1,
        toolCallsUsed: 0,
      },
      setDraft: (draft) => calls.drafts.push(draft),
      setStatus: (status) => calls.statuses.push(status),
      status: "Connected",
      ...overrides,
    },
  };
}

describe("localCommands", () => {
  test("getLocalCommand normalizes slash commands", () => {
    expect(getLocalCommand("  /HELP  ")).toBe("/help");
    expect(getLocalCommand("hello")).toBeNull();
  });

  test("buildStatusMessage includes progress and approval state", () => {
    const message = buildStatusMessage({
      agentRunning: false,
      limits: {
        maxSteps: 10,
        maxToolCalls: 8,
      },
      messageCount: 4,
      pendingApproval: { approvalId: "approval-1" },
      runProgress: {
        modelCalls: 2,
        status: "waiting",
        stepsUsed: 3,
        toolCallsUsed: 1,
      },
      status: "Agent waiting",
    });

    expect(message).toMatch(/Status: Agent waiting/);
    expect(message).toMatch(/Steps: 3 \/ 10/);
    expect(message).toMatch(/Pending approval: yes/);
    expect(message).toMatch(/Messages: 4/);
  });

  test("handleLocalCommand dispatches help", () => {
    const { calls, context } = createCommandContext();

    expect(handleLocalCommand("/help", context)).toBe(true);
    expect(calls.drafts).toEqual([""]);
    expect(calls.statuses).toEqual(["Help shown"]);
    expect(calls.messages[0].text).toBe(HELP_MESSAGE);
  });

  test("handleLocalCommand returns false for unknown commands", () => {
    const { calls, context } = createCommandContext();

    expect(handleLocalCommand("/unknown", context)).toBe(false);
    expect(calls.messages).toEqual([]);
  });
});
