// Owns local message creation and trace-message mutation helpers.
import { useCallback, useState } from "react";
import { createLocalMessageId, createMessageTimestamp } from "../utils/messages";

export function useAgentMessages() {
  const [messages, setMessages] = useState([]);

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

  return {
    addLocalMessage,
    appendMessageText,
    finishTraceMessage,
    messages,
    setMessages,
    updateMessage,
  };
}
