// Displays one message with styling for user, trace, and final output.
import { useEffect, useRef, useState } from "react";
import { formatMessageTimestamp } from "../utils/messages";

function getTracePreview(text) {
  const lines = text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  const stepCount = lines.filter((line) => line.startsWith("[STEP]")).length;
  const latestLine = lines.at(-1) ?? "Running agent...";

  return {
    latestLine,
    stepCount,
  };
}

function MessageCard({ message, agentMap }) {
  const [stepsOpen, setStepsOpen] = useState(message.type === "agent_trace");
  const stepsRef = useRef(null);

  const agent =
    message.agentId === "user"
      ? {
          name: "User",
          color: "text-zinc-100",
        }
      : agentMap[message.agentId] || {
          name: "PatchPilot",
          color: "text-cyan-300",
        };

  const isTrace = message.type === "agent_trace";
  const isFinalTrace = message.type === "agent_trace_final";
  const isUser = message.type === "user_task";

  const textColor = isTrace || isFinalTrace
    ? "text-[#bac9cc]/65"
    : isUser
    ? "text-[#c3f5ff]"
    : "text-[#dce3f0]/85";

  const tracePreview = getTracePreview(message.text || "");
  const messageTime = formatMessageTimestamp(message.createdAt);

  useEffect(() => {
    const stepsElement = stepsRef.current;

    if (!stepsOpen || !stepsElement) return;

    stepsElement.scrollTo({
      top: stepsElement.scrollHeight,
      behavior: "smooth",
    });
  }, [message.text, stepsOpen]);

  return (
    <article className="group border-l border-[#3b494c]/20 py-3 pl-3 transition hover:border-[#00e5ff]/35">
      <div className="mb-1 flex items-baseline justify-between gap-3">
        <span
          className={`min-w-0 truncate font-mono text-xs font-medium uppercase tracking-widest ${agent.color}`}
        >
          {agent.name}
        </span>
        <span className="shrink-0 font-mono text-[10px] uppercase tracking-widest text-white/70">
          {messageTime}
        </span>
      </div>

      <div className="min-w-0">
        {isTrace || isFinalTrace ? (
          <div className="min-w-0">
            <button
              type="button"
              onClick={() => setStepsOpen((currentValue) => !currentValue)}
              className="flex w-full items-center gap-2 text-left font-mono text-[11px] uppercase tracking-widest text-[#bac9cc]/70 transition hover:text-[#00e5ff]"
              aria-expanded={stepsOpen}
            >
              <span className="w-3 text-[#00e5ff]">
                {stepsOpen ? "-" : "+"}
              </span>
              <span>
                Steps Group
                <span className="ml-2 text-[#bac9cc]/35">
                  {tracePreview.stepCount} steps
                </span>
              </span>
            </button>

            {!stepsOpen && (
              <div className="mt-1 truncate font-mono text-xs text-[#bac9cc]/40">
                {tracePreview.latestLine}
              </div>
            )}

            {stepsOpen && (
              <pre
                ref={stepsRef}
                className={`mt-2 max-h-72 overflow-y-auto whitespace-pre-wrap break-words bg-white/[0.02] p-2 font-mono text-xs leading-5 ${textColor}`}
              >
                {message.text || "Running agent..."}
              </pre>
            )}

            {message.finalText && (
              <div className="mt-2 border-l border-[#00e5ff]/40 pl-3">
                <div className="font-mono text-[10px] font-semibold uppercase tracking-widest text-[#00e5ff]">
                  {message.finalLabel || "FINAL ANSWER"}
                </div>
                <div className="mt-1 whitespace-pre-wrap text-sm leading-6 text-white">
                  {message.finalText}
                </div>
              </div>
            )}
          </div>
        ) : isUser ? (
          <div className={`min-w-0 whitespace-pre-wrap font-mono text-sm uppercase tracking-wider leading-6 ${textColor}`}>
            {message.text}
          </div>
        ) : (
          <div className={`min-w-0 whitespace-pre-wrap text-sm leading-6 ${textColor}`}>
            {message.text}
          </div>
        )}
      </div>
    </article>
  );
}
  
export default MessageCard;
