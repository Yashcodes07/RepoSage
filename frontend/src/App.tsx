import { useState } from 'react';
import Sidebar from './components/Sidebar';
import ChatThread from './components/ChatThread';
import ChatInput from './components/ChatInput';
import { useChat } from './hooks/useChat';

function App() {
  const [repoUrl, setRepoUrl] = useState('');
  const [agenticMode, setAgenticMode] = useState(false);
  const { messages, ask, busy } = useChat();

  return (
    <div className="flex h-screen bg-bg text-ink">
      <Sidebar repoUrl={repoUrl} onRepoUrlChange={setRepoUrl} />

      <main className="flex min-w-0 flex-1 flex-col">
        <div className="min-h-0 flex-1 overflow-y-auto">
          <ChatThread messages={messages} repoUrl={repoUrl || null} />
        </div>

        <ChatInput
          onSubmit={(q) => ask(q, agenticMode)}
          disabled={busy}
          agenticMode={agenticMode}
          onToggleAgentic={setAgenticMode}
        />
      </main>
    </div>
  );
}

export default App;
