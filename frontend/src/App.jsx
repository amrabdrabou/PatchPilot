// Composes the agent hub page from state and focused UI sections.
import DashboardHeader from "./components/DashboardHeader";
import AgentSidebar from "./components/AgentSidebar";
import MessageStream from "./components/MessageStream";
import MessageComposer from "./components/MessageComposer";
import { useAgentHub } from "./hooks/useAgentHub";

function App() {
  const {
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
    deleteSavedConversation,
    rejectTool,
    loadSavedConversation,
    resetAllMessages,
    sendMessage,
    stopRun,
    setDraft,
    setSelectedAgentId,
  } = useAgentHub();

  return (
    <main className="min-h-screen overflow-hidden bg-black text-[#dce3f0]">
      <div className="flex h-screen">
        <AgentSidebar
          agents={agents}
          conversations={conversations}
          messages={messages}
          progress={progress}
          selectedAgentId={selectedAgentId}
          onReset={resetAllMessages}
          onDeleteConversation={deleteSavedConversation}
          onSelectConversation={loadSavedConversation}
          onSelectAgent={setSelectedAgentId}
        />

        <section className="flex min-w-0 flex-1 flex-col bg-black">
          <DashboardHeader
            agentCount={agents.length}
            progress={progress}
            status={status}
            totalMessages={totalMessages}
          />

          <MessageStream agentMap={agentMap} messages={messages} />

          <MessageComposer
            agentRunning={agentRunning}
            agents={agents}
            draft={draft}
            pendingApproval={pendingApproval}
            selectedAgentId={selectedAgentId}
            onApprove={approveTool}
            onDraftChange={setDraft}
            onReject={rejectTool}
            onSelectAgent={setSelectedAgentId}
            onSend={sendMessage}
            onStop={stopRun}
          />
        </section>
      </div>
    </main>
  );
}

export default App;
