// Verifies the main hub hook orchestration with mocked backend calls.
// @vitest-environment jsdom
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import {
  archiveCurrentConversation,
  approveToolCall,
  getState,
  listConversations,
  loadConversation,
  rejectToolCall,
  resetMessages,
  startAgentRun,
  stopAgentRun,
} from "../api/agentApi";
import { readAgentStream } from "../utils/readAgentStream";
import { useAgentHub } from "./useAgentHub";

vi.mock("../api/agentApi", () => ({
  archiveCurrentConversation: vi.fn(),
  approveToolCall: vi.fn(),
  getState: vi.fn(),
  listConversations: vi.fn(),
  loadConversation: vi.fn(),
  rejectToolCall: vi.fn(),
  resetMessages: vi.fn(),
  startAgentRun: vi.fn(),
  stopAgentRun: vi.fn(),
}));

vi.mock("../utils/readAgentStream", () => ({
  readAgentStream: vi.fn(),
}));

const INITIAL_STATE = {
  agents: [{ id: "patchpilot", name: "PatchPilot" }],
  limits: {
    maxSteps: 10,
    maxToolCalls: 8,
  },
  messages: [],
};

beforeEach(() => {
  getState.mockResolvedValue(INITIAL_STATE);
  listConversations.mockResolvedValue({ conversations: [] });
  archiveCurrentConversation.mockResolvedValue({
    ...INITIAL_STATE,
    archived_conversation: null,
    conversations: [],
  });
  loadConversation.mockResolvedValue({
    ...INITIAL_STATE,
    messages: [{ agentId: "user", text: "saved", type: "user_task" }],
  });
  resetMessages.mockResolvedValue(INITIAL_STATE);
  startAgentRun.mockResolvedValue({ ok: true });
  approveToolCall.mockResolvedValue({ ok: true });
  rejectToolCall.mockResolvedValue({ ok: true });
  stopAgentRun.mockResolvedValue({ stop_requested: true });
  readAgentStream.mockResolvedValue(undefined);
});

afterEach(() => {
  vi.clearAllMocks();
});

async function renderLoadedHub() {
  const hook = renderHook(() => useAgentHub());

  await waitFor(() => {
    expect(hook.result.current.status).toBe("Connected to backend");
  });

  return hook;
}

describe("useAgentHub", () => {
  test("loads initial backend state", async () => {
    const { result } = await renderLoadedHub();

    expect(getState).toHaveBeenCalledTimes(1);
    expect(listConversations).toHaveBeenCalledTimes(1);
    expect(result.current.agents).toEqual(INITIAL_STATE.agents);
    expect(result.current.selectedAgentId).toBe("patchpilot");
    expect(result.current.progress.maxSteps).toBe(10);
  });

  test("handles /clear by archiving current messages", async () => {
    archiveCurrentConversation.mockResolvedValue({
      ...INITIAL_STATE,
      archived_conversation: { id: "conv-1" },
      conversations: [{ id: "conv-1", title: "Archived" }],
    });
    const { result } = await renderLoadedHub();

    await act(async () => {
      result.current.setDraft("save this first");
    });

    await act(async () => {
      await result.current.sendMessage();
    });

    await act(async () => {
      result.current.setDraft("/clear");
    });

    await act(async () => {
      await result.current.sendMessage();
    });

    expect(archiveCurrentConversation).toHaveBeenCalledWith([
      expect.objectContaining({
        agentId: "user",
        text: "save this first",
        type: "user_task",
      }),
      expect.objectContaining({
        agentId: "backend",
        type: "agent_trace",
      }),
    ]);
    expect(resetMessages).not.toHaveBeenCalled();
    expect(result.current.conversations).toEqual([{ id: "conv-1", title: "Archived" }]);
    expect(result.current.status).toBe("Conversation archived");
    expect(result.current.draft).toBe("");
  });

  test("loads a saved conversation into the message stream", async () => {
    const { result } = await renderLoadedHub();

    await act(async () => {
      await result.current.loadSavedConversation("conv-1");
    });

    expect(loadConversation).toHaveBeenCalledWith("conv-1");
    expect(result.current.messages).toEqual([
      { agentId: "user", text: "saved", type: "user_task" },
    ]);
    expect(result.current.status).toBe("Conversation loaded");
  });

  test("sends a task and applies final stream updates", async () => {
    readAgentStream.mockImplementation(async (_response, traceId, handlers) => {
      handlers.appendMessageText(traceId, "[STEP] 1\n");
      handlers.finishTraceMessage(traceId, "Done.", "FINAL ANSWER");
      handlers.updateProgressFromEvent({
        max_steps: 10,
        max_tool_calls: 8,
        model_calls: 1,
        step: 1,
        tool_calls: 0,
        type: "final",
      });
    });
    const { result } = await renderLoadedHub();

    await act(async () => {
      result.current.setDraft("inspect the sandbox");
    });

    await act(async () => {
      await result.current.sendMessage();
    });

    expect(startAgentRun).toHaveBeenCalledWith("inspect the sandbox");
    expect(result.current.agentRunning).toBe(false);
    expect(result.current.status).toBe("Agent waiting or finished");
    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages.at(-1)).toMatchObject({
      finalLabel: "FINAL ANSWER",
      finalText: "Done.",
      type: "agent_trace_final",
    });
    expect(result.current.progress).toMatchObject({
      modelCalls: 1,
      status: "finished",
      stepsUsed: 1,
      toolCallsUsed: 0,
    });
  });

  test("approves and rejects pending tool calls", async () => {
    readAgentStream.mockImplementation(async (_response, traceId, handlers) => {
      handlers.setPendingApproval({
        approvalId: "approval-1",
        runId: "run-1",
        toolName: "edit_file",
        traceId,
      });
    });
    const { result } = await renderLoadedHub();

    await act(async () => {
      result.current.setDraft("edit file");
    });

    await act(async () => {
      await result.current.sendMessage();
    });

    expect(result.current.pendingApproval).toMatchObject({
      approvalId: "approval-1",
      runId: "run-1",
    });

    await act(async () => {
      await result.current.approveTool();
    });

    await act(async () => {
      await result.current.rejectTool();
    });

    expect(approveToolCall).toHaveBeenCalledWith("run-1", "approval-1");
    expect(rejectToolCall).toHaveBeenCalledWith("run-1", "approval-1");
    expect(result.current.agentRunning).toBe(false);
  });

  test("requests stop for the current stream run", async () => {
    readAgentStream.mockImplementation(async (_response, _traceId, handlers) => {
      handlers.setCurrentRunId("run-1");
    });
    const { result } = await renderLoadedHub();

    await act(async () => {
      result.current.setDraft("long task");
    });

    await act(async () => {
      await result.current.sendMessage();
    });

    await act(async () => {
      await result.current.stopRun();
    });

    expect(stopAgentRun).toHaveBeenCalledWith("run-1");
    expect(result.current.status).toBe("Stopping agent...");
  });
});
