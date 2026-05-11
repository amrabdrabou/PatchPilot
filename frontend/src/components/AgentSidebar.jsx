// Lists available agents and their local message counts.
function AgentSidebar({
  agents,
  messages,
  progress,
  selectedAgentId,
  onReset,
  onSelectAgent,
}) {
  return (
    <aside className="hidden h-full w-64 shrink-0 flex-col justify-between border-r border-[#3b494c]/20 bg-black px-4 py-4 md:flex">
      <div>
        <div className="mb-6">
          <span className="font-mono text-[11px] font-medium uppercase tracking-widest text-[#bac9cc]/60">
            System Status
          </span>
          <div className="mt-2 flex items-center gap-2">
            <span className="h-1.5 w-1.5 rounded-full bg-[#79ff5b] shadow-[0_0_12px_#79ff5b]" />
            <span className="font-mono text-sm font-medium uppercase tracking-widest text-[#baffa2]">
              Online
            </span>
          </div>
        </div>

        <nav className="space-y-4">
          <div>
            <div className="mb-2 font-mono text-[11px] font-medium uppercase tracking-widest text-[#bac9cc]/40">
              Agents
            </div>

            <div className="space-y-2">
              {agents.map((agent) => {
                const count = messages.filter(
                  (message) => message.agentId === agent.id
                ).length;

                const isSelected = selectedAgentId === agent.id;

                return (
                  <button
                    key={agent.id}
                    onClick={() => onSelectAgent(agent.id)}
                    className={`group w-full border-l px-3 py-1 text-left transition ${
                      isSelected
                        ? "border-[#00e5ff] bg-[#00e5ff]/5"
                        : "border-transparent opacity-60 hover:border-[#3b494c] hover:opacity-100"
                    }`}
                  >
                    <div className="flex items-baseline justify-between gap-3">
                      <span className={`font-mono text-sm font-medium ${agent.color}`}>
                        {agent.name}
                      </span>
                      <span className="font-mono text-[11px] text-[#bac9cc]/45">
                        {count} msgs
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </nav>
      </div>

      <div className="border-t border-[#3b494c]/20 pt-4">
        <div className="mb-3 space-y-1 font-mono text-[11px] uppercase tracking-widest">
          <div className="flex items-center justify-between text-[#bac9cc]/45">
            <span>Status</span>
            <span className="text-[#baffa2]">{progress.status}</span>
          </div>
          <div className="flex items-center justify-between text-[#bac9cc]/45">
            <span>Steps</span>
            <span>{progress.stepsUsed}/{progress.maxSteps}</span>
          </div>
          <div className="flex items-center justify-between text-[#bac9cc]/45">
            <span>Tools</span>
            <span>{progress.toolCallsUsed}/{progress.maxToolCalls}</span>
          </div>
          <div className="flex items-center justify-between text-[#bac9cc]/45">
            <span>Model Calls</span>
            <span>{progress.modelCalls}</span>
          </div>
        </div>
        <div className="flex flex-col gap-2">
          <button
            onClick={onReset}
            className="text-left font-mono text-sm font-medium uppercase tracking-widest text-[#bac9cc]/70 transition hover:text-[#00e5ff]"
          >
            Reset
          </button>
        </div>
      </div>
    </aside>
  );
}

export default AgentSidebar;
