// Displays the top-level hub status and summary metrics.
function StatBlock({ label, value }) {
  return (
    <div className="min-w-20 border-l border-[#3b494c]/30 px-3 py-1">
      <div className="font-mono text-[10px] font-medium uppercase tracking-widest text-[#bac9cc]/45">
        {label}
      </div>
      <div className="font-mono text-sm font-semibold text-[#c3f5ff]">
        {value}
      </div>
    </div>
  );
}

function DashboardHeader({ agentCount, progress, status, totalMessages }) {
  return (
    <header className="flex min-h-16 items-center justify-between border-b border-[#3b494c]/20 bg-black px-6">
      <div className="min-w-0">
        <div className="font-mono text-[11px] font-medium uppercase tracking-[0.32em] text-[#00e5ff]">
          PatchPilot
        </div>
        <h1 className="mt-0.5 truncate text-xl font-semibold tracking-tight text-[#dce3f0]">
          Developer Agent
        </h1>
        <p className="mt-0.5 font-mono text-[11px] uppercase tracking-widest text-[#bac9cc]/50">
          Backend: {status}
        </p>
      </div>

      <div className="hidden items-center md:flex">
        <StatBlock label="Agents" value={agentCount} />
        <StatBlock label="Messages" value={totalMessages} />
        <StatBlock
          label="Steps"
          value={`${progress.stepsUsed}/${progress.maxSteps}`}
        />
        <StatBlock
          label="Tools"
          value={`${progress.toolCallsUsed}/${progress.maxToolCalls}`}
        />
      </div>
    </header>
  );
}

export default DashboardHeader;
