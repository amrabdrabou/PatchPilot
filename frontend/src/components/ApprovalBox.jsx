// Shows approval controls for tool calls that need user permission.
function ApprovalBox({ pendingApproval, agentRunning, onApprove, onReject }) {
    if (!pendingApproval) {
      return null;
    }
  
    return (
      <div className="mx-auto mb-4 max-w-5xl border border-[#e9b3ff]/35 bg-[#e9b3ff]/10 p-4">
        <div className="font-mono text-xs font-semibold uppercase tracking-widest text-[#e9b3ff]">
          Approval Required
        </div>
  
        <div className="mt-3 font-mono text-xs uppercase tracking-widest text-[#bac9cc]/70">
          Tool:{" "}
          <span className="text-[#f6d9ff]">
            {pendingApproval.toolName}
          </span>
        </div>
  
        <pre className="mt-3 whitespace-pre-wrap break-words border border-[#3b494c]/20 bg-black p-3 font-mono text-xs text-[#bac9cc]/70">
          {JSON.stringify(pendingApproval.arguments, null, 2)}
        </pre>
  
        <div className="mt-4 flex gap-3">
          <button
            onClick={onApprove}
            disabled={agentRunning}
            className="border border-[#79ff5b]/40 bg-[#79ff5b]/10 px-4 py-2 font-mono text-xs font-semibold uppercase tracking-widest text-[#baffa2] hover:bg-[#79ff5b]/20 disabled:opacity-50"
          >
            Approve
          </button>
  
          <button
            onClick={onReject}
            disabled={agentRunning}
            className="border border-[#ffb4ab]/40 bg-[#ffb4ab]/10 px-4 py-2 font-mono text-xs font-semibold uppercase tracking-widest text-[#ffb4ab] hover:bg-[#ffb4ab]/20 disabled:opacity-50"
          >
            Reject
          </button>
        </div>
      </div>
    );
  }
  
  export default ApprovalBox;
