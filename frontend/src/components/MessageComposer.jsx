// Handles task input and pending tool approval controls.
import ApprovalBox from "./ApprovalBox";

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
}) {
  function handleSubmit(event) {
    event.preventDefault();
    onSend();
  }

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

      <div className="mx-auto grid max-w-6xl gap-2 md:grid-cols-[180px_1fr_auto]">
        <select
          value={selectedAgentId}
          onChange={(event) => onSelectAgent(event.target.value)}
          className="border border-[#3b494c]/30 bg-[#080f17] px-3 py-2 font-mono text-xs uppercase tracking-widest text-[#dce3f0] outline-none transition focus:border-[#00e5ff]"
        >
          {agents.map((agent) => (
            <option key={agent.id} value={agent.id}>
              {agent.name}
            </option>
          ))}
        </select>

        <input
          value={draft}
          onChange={(event) => onDraftChange(event.target.value)}
          placeholder="Execute command..."
          className="border border-[#3b494c]/30 bg-transparent px-3 py-2 font-mono text-sm uppercase tracking-widest text-[#dce3f0] outline-none placeholder:text-[#bac9cc]/25 focus:border-[#00e5ff] focus:ring-0"
        />

        <button
          disabled={agentRunning}
          className="border border-[#00e5ff]/50 bg-[#00e5ff]/10 px-4 py-2 font-mono text-xs font-semibold uppercase tracking-widest text-[#c3f5ff] transition hover:bg-[#00e5ff]/20 disabled:cursor-not-allowed disabled:opacity-40"
          type="submit"
        >
          {agentRunning ? "Running..." : "Send"}
        </button>
      </div>
    </form>
  );
}

export default MessageComposer;
