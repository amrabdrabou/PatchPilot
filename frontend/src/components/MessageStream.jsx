// Renders the shared message stream and stream-level controls.
import { useEffect, useRef } from "react";
import MessageCard from "./MessageCard";

function MessageStream({ agentMap, messages }) {
  const streamRef = useRef(null);

  useEffect(() => {
    const streamElement = streamRef.current;

    if (!streamElement) return;

    streamElement.scrollTo({
      top: streamElement.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  return (
    <div
      ref={streamRef}
      className="min-h-0 flex-1 overflow-y-auto px-4 py-4 md:px-6"
    >
      <div className="mx-auto max-w-6xl divide-y divide-[#3b494c]/20">
        {messages.length === 0 ? (
          <div className="flex min-h-[36vh] items-center justify-center border border-dashed border-[#3b494c]/25 bg-white/[0.02] p-6 text-center font-mono text-xs uppercase tracking-widest text-[#bac9cc]/40">
            No messages yet. Describe a task to start PatchPilot.
          </div>
        ) : (
          messages.map((message) => (
            <MessageCard
              key={`${message.id}-${message.type}`}
              agentMap={agentMap}
              message={message}
            />
          ))
        )}
      </div>
    </div>
  );
}

export default MessageStream;
