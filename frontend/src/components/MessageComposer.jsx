// Handles task input and pending tool approval controls.
import ApprovalBox from "./ApprovalBox";

export const MAX_DRAFT_LENGTH = 4000;

function MessageComposer({
  agentRunning,
  agents,
  draft,
  pendingApproval,
  selectedAgentId,
  onApprove,
  onDraftChange,
  onReject,
  onSelectAgent,
  onSend,
  onStop,
}) {
  function handleSubmit(event) {
    event.preventDefault();
    onSend();
  }

  function handleDraftKeyDown(event) {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      onSend();
    }
  }

  const draftLength = draft.length;

  return (
    <form
      className="border-t border-[#3b494c]/20 bg-black px-4 py-3 md:px-6"
      onSubmit={handleSubmit}
    >
      <ApprovalBox
        agentRunning={agentRunning}
        onApprove={onApprove}
        onReject={onReject}
        pendingApproval={pendingApproval}
      />

      <div className="mx-auto grid max-w-6xl gap-2 md:grid-cols-[180px_1fr_auto_auto]">
        <select
          value={selectedAgentId}
          onChange={(event) => onSelectAgent(event.target.value)}
          className="h-20 border border-[#3b494c]/30 bg-[#080f17] px-3 py-2 font-mono text-xs uppercase tracking-widest text-[#dce3f0] outline-none transition focus:border-[#00e5ff]"
        >
          {agents.map((agent) => (
            <option key={agent.id} value={agent.id}>
              {agent.name}
            </option>
          ))}
        </select>

        <div className="min-w-0">
          <textarea
            value={draft}
            maxLength={MAX_DRAFT_LENGTH}
            onChange={(event) => onDraftChange(event.target.value)}
            onKeyDown={handleDraftKeyDown}
            placeholder="Describe a task or type /help..."
            rows={3}
            className="h-20 w-full resize-none border border-[#3b494c]/30 bg-transparent px-3 py-2 font-mono text-sm leading-5 text-[#dce3f0] outline-none placeholder:text-[#bac9cc]/25 focus:border-[#00e5ff] focus:ring-0"
          />
          <div className="mt-1 text-right font-mono text-[10px] uppercase tracking-widest text-[#bac9cc]/35">
            {draftLength}/{MAX_DRAFT_LENGTH}
          </div>
        </div>

        <button
          disabled={agentRunning}
          className="h-20 border border-[#00e5ff]/50 bg-[#00e5ff]/10 px-4 py-2 font-mono text-xs font-semibold uppercase tracking-widest text-[#c3f5ff] transition hover:bg-[#00e5ff]/20 disabled:cursor-not-allowed disabled:opacity-40"
          type="submit"
        >
          {agentRunning ? "Running..." : "Send"}
        </button>

        <button
          disabled={!agentRunning}
          onClick={onStop}
          className="h-20 border border-[#ffb4ab]/45 bg-[#ffb4ab]/10 px-4 py-2 font-mono text-xs font-semibold uppercase tracking-widest text-[#ffb4ab] transition hover:bg-[#ffb4ab]/20 disabled:cursor-not-allowed disabled:opacity-40"
          type="button"
        >
          Stop
        </button>
      </div>
    </form>
  );
}

export default MessageComposer;
