// Owns agent hub state, backend calls, and stream handling.
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  approveToolCall,
  getState,
  rejectToolCall,
  resetMessages,
  startAgentRun,
  stopAgentRun,
} from "../api/agentApi";
import {
  buildPendingApproval,
  extractFinalAnswer,
  formatTraceLine,
  isTraceEvent,
} from "../utils/agentStream";
import { createLocalMessageId, createMessageTimestamp } from "../utils/messages";

const EMPTY_LIMITS = {
  maxSteps: 0,
  maxToolCalls: 0,
};

const EMPTY_PROGRESS = {
  modelCalls: 0,
  status: "idle",
  stepsUsed: 0,
  toolCallsUsed: 0,
};

const HELP_MESSAGE = [
  "Available commands:",
  "/help - Show local UI commands.",
  "/status - Show current run status and limits.",
  "/clear - Clear the message stream.",
  "",
  "PatchPilot can inspect files, search text, run allowlisted commands, show git status/diff, and edit sandbox files after approval.",
].join("\n");

export function useAgentHub() {
  const [agentRunning, setAgentRunning] = useState(false);
  const [pendingApproval, setPendingApproval] = useState(null);
  const [agents, setAgents] = useState([]);
  const [messages, setMessages] = useState([]);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [draft, setDraft] = useState("");
  const [status, setStatus] = useState("Loading...");
  const [limits, setLimits] = useState(EMPTY_LIMITS);
  const [runProgress, setRunProgress] = useState(EMPTY_PROGRESS);
  const [currentRunId, setCurrentRunId] = useState(null);

  const agentMap = useMemo(() => {
    return Object.fromEntries(agents.map((agent) => [agent.id, agent]));
  }, [agents]);

  const totalMessages = messages.length;
  const progress = useMemo(
    () => ({
      ...runProgress,
      maxSteps: limits.maxSteps,
      maxToolCalls: limits.maxToolCalls,
    }),
    [limits, runProgress]
  );

  const updateMessage = useCallback((messageId, newText) => {
    setMessages((currentMessages) =>
      currentMessages.map((message) =>
        message.id === messageId ? { ...message, text: newText } : message
      )
    );
  }, []);

  const appendMessageText = useCallback((messageId, addedText, nextType) => {
    setMessages((currentMessages) =>
      currentMessages.map((message) =>
        message.id === messageId
          ? {
              ...message,
              text: `${message.text}${addedText}`,
              type: nextType ?? message.type,
            }
          : message
      )
    );
  }, []);

  const finishTraceMessage = useCallback((messageId, finalText, finalLabel) => {
    setMessages((currentMessages) =>
      currentMessages.map((message) =>
        message.id === messageId
          ? {
              ...message,
              finalLabel,
              finalText,
              type: "agent_trace_final",
            }
          : message
      )
    );
  }, []);

  const updateProgressFromEvent = useCallback((event) => {
    const hasProgress =
      event.step !== undefined ||
      event.model_calls !== undefined ||
      event.tool_calls !== undefined ||
      event.max_steps !== undefined ||
      event.max_tool_calls !== undefined;

    if (!hasProgress) return;

    setRunProgress((currentProgress) => ({
      ...currentProgress,
      modelCalls: event.model_calls ?? currentProgress.modelCalls,
      status:
        event.type === "final" || event.type === "stopped"
          ? "finished"
          : event.type === "approval_required"
          ? "waiting"
          : "running",
      stepsUsed: event.step ?? currentProgress.stepsUsed,
      toolCallsUsed: event.tool_calls ?? currentProgress.toolCallsUsed,
    }));

    setLimits((currentLimits) => ({
      maxSteps: event.max_steps ?? currentLimits.maxSteps,
      maxToolCalls: event.max_tool_calls ?? currentLimits.maxToolCalls,
    }));
  }, []);

  const addLocalMessage = useCallback(
    (agentId, text, type = "message", customId = null) => {
      const newMessage = {
        id: customId ?? createLocalMessageId(),
        agentId,
        createdAt: createMessageTimestamp(),
        text,
        type,
      };

      setMessages((currentMessages) => [...currentMessages, newMessage]);

      return newMessage.id;
    },
    []
  );

  const readAgentStream = useCallback(
    async (response, traceId) => {
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
          if (!part.startsWith("data: ")) continue;

          let event;

          try {
            event = JSON.parse(part.replace("data: ", ""));
          } catch (error) {
            console.error(error);
            appendMessageText(traceId, "\n[ERROR]\nMalformed stream event skipped.\n");
            continue;
          }

          if (event.run_id) {
            setCurrentRunId(event.run_id);
          }

          updateProgressFromEvent(event);

          if (isTraceEvent(event)) {
            appendMessageText(traceId, formatTraceLine(event));
          }

          if (event.type === "approval_required") {
            setPendingApproval(buildPendingApproval(event, traceId));
          }

          if (event.type === "approval_decision") {
            setPendingApproval(null);
          }

          if (event.type === "final" || event.type === "stopped") {
            const label = event.type === "final" ? "FINAL ANSWER" : "STOPPED";

            finishTraceMessage(traceId, extractFinalAnswer(event.content), label);
            setPendingApproval(null);
            setCurrentRunId(null);
          }
        }
      }
    },
    [appendMessageText, finishTraceMessage, updateProgressFromEvent]
  );

  const sendMessage = useCallback(async () => {
    if (!draft.trim() || agentRunning) return;

    const task = draft.trim();
    const command = task.toLowerCase();

    if (command === "/help") {
      setDraft("");
      addLocalMessage("backend", HELP_MESSAGE, "message");
      setStatus("Help shown");
      return;
    }

    if (command === "/status") {
      setDraft("");
      addLocalMessage(
        "backend",
        [
          `Status: ${status}`,
          `Run state: ${agentRunning ? "running" : runProgress.status}`,
          `Steps: ${runProgress.stepsUsed} / ${limits.maxSteps}`,
          `Tool calls: ${runProgress.toolCallsUsed} / ${limits.maxToolCalls}`,
          `Model calls: ${runProgress.modelCalls}`,
          `Pending approval: ${pendingApproval ? "yes" : "no"}`,
          `Messages: ${messages.length}`,
        ].join("\n"),
        "message"
      );
      setStatus("Status shown");
      return;
    }

    if (command === "/clear") {
      setDraft("");
      setPendingApproval(null);
      setCurrentRunId(null);
      setRunProgress(EMPTY_PROGRESS);

      try {
        const data = await resetMessages();

        setAgents(data.agents);
        setMessages(data.messages);
        setLimits(data.limits ?? EMPTY_LIMITS);
        setSelectedAgentId(data.agents[0]?.id ?? "");
        setStatus("Messages cleared");
      } catch (error) {
        console.error(error);
        setMessages([]);
        setStatus("Messages cleared locally");
      }

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
      await readAgentStream(response, traceId);
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
    messages.length,
    pendingApproval,
    readAgentStream,
    runProgress,
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
      setSelectedAgentId(data.agents[0]?.id ?? "");
      setDraft("");
      setPendingApproval(null);
      setCurrentRunId(null);
      setStatus("Messages reset");
    } catch (error) {
      setStatus("Failed to reset messages");
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

      await readAgentStream(response, pendingApproval.traceId);
      setStatus("Agent waiting or finished");
    } catch (error) {
      console.error(error);
      setStatus("Approval failed");
    } finally {
      setAgentRunning(false);
    }
  }, [pendingApproval, readAgentStream]);

  const rejectTool = useCallback(async () => {
    if (!pendingApproval) return;

    setAgentRunning(true);
    setStatus("Rejecting tool...");

    try {
      const response = await rejectToolCall(
        pendingApproval.runId,
        pendingApproval.approvalId
      );

      await readAgentStream(response, pendingApproval.traceId);
      setStatus("Agent waiting or finished");
    } catch (error) {
      console.error(error);
      setStatus("Rejection failed");
    } finally {
      setAgentRunning(false);
    }
  }, [pendingApproval, readAgentStream]);

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
  }, []);

  return {
    agentRunning,
    agents,
    agentMap,
    draft,
    messages,
    pendingApproval,
    progress,
    selectedAgentId,
    status,
    totalMessages,
    approveTool,
    rejectTool,
    resetAllMessages,
    sendMessage,
    stopRun,
    setDraft,
    setSelectedAgentId,
  };
}
