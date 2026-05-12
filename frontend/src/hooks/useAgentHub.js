// Orchestrates agent hub state, backend calls, approvals, and stream handling.
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  archiveCurrentConversation,
  approveToolCall,
  deleteConversation,
  getState,
  listConversations,
  loadConversation,
  rejectToolCall,
  resetMessages,
  startAgentRun,
  stopAgentRun,
} from "../api/agentApi";
import { getLocalCommand, handleLocalCommand } from "../utils/localCommands";
import { readAgentStream } from "../utils/readAgentStream";
import { createLocalMessageId } from "../utils/messages";
import { useAgentMessages } from "./useAgentMessages";
import { EMPTY_LIMITS, EMPTY_PROGRESS, useRunProgress } from "./useRunProgress";

export function useAgentHub() {
  const [agentRunning, setAgentRunning] = useState(false);
  const [pendingApproval, setPendingApproval] = useState(null);
  const [agents, setAgents] = useState([]);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [conversations, setConversations] = useState([]);
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState("Loading...");
  const [currentRunId, setCurrentRunId] = useState(null);
  const {
    addLocalMessage,
    appendMessageText,
    finishTraceMessage,
    messages,
    setMessages,
    updateMessage,
  } = useAgentMessages();
  const {
    limits,
    progress,
    runProgress,
    setLimits,
    setRunProgress,
    updateProgressFromEvent,
  } = useRunProgress();

  const agentMap = useMemo(() => {
    return Object.fromEntries(agents.map((agent) => [agent.id, agent]));
  }, [agents]);

  const totalMessages = messages.length;

  const refreshConversations = useCallback(async () => {
    const data = await listConversations();

    setConversations(data.conversations ?? []);
  }, []);

  const streamHandlers = useMemo(
    () => ({
      appendMessageText,
      finishTraceMessage,
      setCurrentRunId,
      setPendingApproval,
      updateProgressFromEvent,
    }),
    [appendMessageText, finishTraceMessage, updateProgressFromEvent]
  );

  const readAgentResponse = useCallback(
    async (response, traceId) => {
      await readAgentStream(response, traceId, streamHandlers);
    },
    [streamHandlers]
  );

  const sendMessage = useCallback(async () => {
    if (!draft.trim() || agentRunning) return;

    const task = draft.trim();
    const command = getLocalCommand(task);

    if (command === "/clear") {
      setDraft("");
      setPendingApproval(null);
      setCurrentRunId(null);
      setRunProgress(EMPTY_PROGRESS);

      try {
        const data = await archiveCurrentConversation(messages);

        setAgents(data.agents);
        setMessages(data.messages);
        setLimits(data.limits ?? EMPTY_LIMITS);
        setConversations(data.conversations ?? []);
        setSelectedAgentId(data.agents[0]?.id ?? "");
        setStatus(data.archived_conversation ? "Conversation archived" : "Messages cleared");
      } catch (error) {
        console.error(error);
        setMessages([]);
        setStatus("Messages cleared locally; archive failed");
      }

      return;
    }

    if (
      handleLocalCommand(command, {
        addLocalMessage,
        agentRunning,
        limits,
        messageCount: messages.length,
        pendingApproval,
        runProgress,
        setDraft,
        setStatus,
        status,
      })
    ) {
      return;
    }

    const traceId = createLocalMessageId();

    setDraft("");
    setAgentRunning(true);
    setStatus("Agent running...");
    setPendingApproval(null);
    setCurrentRunId(null);
    setRunProgress({
      modelCalls: 0,
      status: "running",
      stepsUsed: 0,
      toolCallsUsed: 0,
    });

    addLocalMessage("user", task, "user_task");
    addLocalMessage("backend", "", "agent_trace", traceId);

    try {
      const response = await startAgentRun(task);
      await readAgentResponse(response, traceId);
      setStatus("Agent waiting or finished");
    } catch (error) {
      console.error(error);
      setStatus("Agent run failed");
      updateMessage(traceId, `\n[ERROR]\n${error.message}\n`);
    } finally {
      setAgentRunning(false);
    }
  }, [
    addLocalMessage,
    agentRunning,
    draft,
    limits,
    messages,
    pendingApproval,
    readAgentResponse,
    runProgress,
    setLimits,
    setMessages,
    setRunProgress,
    status,
    updateMessage,
  ]);

  const resetAllMessages = useCallback(async () => {
    try {
      const data = await resetMessages();

      setAgents(data.agents);
      setMessages(data.messages);
      setLimits(data.limits ?? EMPTY_LIMITS);
      setRunProgress(EMPTY_PROGRESS);
      await refreshConversations();
      setSelectedAgentId(data.agents[0]?.id ?? "");
      setDraft("");
      setPendingApproval(null);
      setCurrentRunId(null);
      setStatus("Messages reset");
    } catch (error) {
      setStatus("Failed to reset messages");
      console.error(error);
    }
  }, [refreshConversations, setLimits, setMessages, setRunProgress]);

  const loadSavedConversation = useCallback(async (conversationId) => {
    try {
      const data = await loadConversation(conversationId);

      setAgents(data.agents);
      setMessages(data.messages);
      setLimits(data.limits ?? EMPTY_LIMITS);
      setRunProgress(EMPTY_PROGRESS);
      setSelectedAgentId(data.agents[0]?.id ?? "");
      setDraft("");
      setPendingApproval(null);
      setCurrentRunId(null);
      setStatus("Conversation loaded");
    } catch (error) {
      setStatus("Failed to load conversation");
      console.error(error);
    }
  }, [setLimits, setMessages, setRunProgress]);

  const deleteSavedConversation = useCallback(async (conversationId) => {
    try {
      const data = await deleteConversation(conversationId);

      setConversations(data.conversations ?? []);
      setStatus("Conversation deleted");
    } catch (error) {
      setStatus("Failed to delete conversation");
      console.error(error);
    }
  }, []);

  const approveTool = useCallback(async () => {
    if (!pendingApproval) return;

    setAgentRunning(true);
    setStatus("Approving tool...");

    try {
      const response = await approveToolCall(
        pendingApproval.runId,
        pendingApproval.approvalId
      );

      await readAgentResponse(response, pendingApproval.traceId);
      setStatus("Agent waiting or finished");
    } catch (error) {
      console.error(error);
      setStatus("Approval failed");
    } finally {
      setAgentRunning(false);
    }
  }, [pendingApproval, readAgentResponse]);

  const rejectTool = useCallback(async () => {
    if (!pendingApproval) return;

    setAgentRunning(true);
    setStatus("Rejecting tool...");

    try {
      const response = await rejectToolCall(
        pendingApproval.runId,
        pendingApproval.approvalId
      );

      await readAgentResponse(response, pendingApproval.traceId);
      setStatus("Agent waiting or finished");
    } catch (error) {
      console.error(error);
      setStatus("Rejection failed");
    } finally {
      setAgentRunning(false);
    }
  }, [pendingApproval, readAgentResponse]);

  const stopRun = useCallback(async () => {
    if (!currentRunId) return;

    setStatus("Stopping agent...");

    try {
      const result = await stopAgentRun(currentRunId);

      if (!result.stop_requested) {
        setStatus("Run already finished or not found");
        setAgentRunning(false);
        setCurrentRunId(null);
      }
    } catch (error) {
      setStatus("Stop request failed");
      console.error(error);
    }
  }, [currentRunId]);

  useEffect(() => {
    let ignoreResult = false;

    async function loadInitialState() {
      try {
        const data = await getState();

        if (ignoreResult) return;

        setAgents(data.agents);
        setMessages(data.messages);
        setLimits(data.limits ?? EMPTY_LIMITS);
        setSelectedAgentId(data.agents[0]?.id ?? "");
        await refreshConversations();
        setStatus("Connected to backend");
      } catch (error) {
        if (ignoreResult) return;

        setStatus("Could not connect to backend");
        console.error(error);
      }
    }

    loadInitialState();

    return () => {
      ignoreResult = true;
    };
  }, [refreshConversations, setLimits, setMessages]);

  return {
    agentRunning,
    agents,
    agentMap,
    conversations,
    draft,
    messages,
    pendingApproval,
    progress,
    selectedAgentId,
    status,
    totalMessages,
    approveTool,
    rejectTool,
    deleteSavedConversation,
    loadSavedConversation,
    resetAllMessages,
    sendMessage,
    stopRun,
    setDraft,
    setSelectedAgentId,
  };
}
