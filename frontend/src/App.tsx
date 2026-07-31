import { useState } from 'react';
import Sidebar from './components/Sidebar';
import ChatThread from './components/ChatThread';
import ChatInput from './components/ChatInput';
import Hero from './components/Hero';
import { useChat } from './hooks/useChat';

function App() {
  const [repoUrl, setRepoUrl] = useState('');
  const [agenticMode, setAgenticMode] = useState(false);
  const { messages, ask, busy } = useChat();

  const hasStarted = messages.length > 0;

  return (
    <div className="flex h-screen bg-bg text-ink">
      <Sidebar repoUrl={repoUrl} onRepoUrlChange={setRepoUrl} />

      <main className="flex min-w-0 flex-1 flex-col">
        {hasStarted ? (
          <>
            <div className="min-h-0 flex-1 overflow-y-auto">
              <ChatThread messages={messages} repoUrl={repoUrl || null} />
            </div>
            <ChatInput
              onSubmit={(q) => ask(q, agenticMode)}
              disabled={busy}
              agenticMode={agenticMode}
              onToggleAgentic={setAgenticMode}
              variant="docked"
            />
          </>
        ) : (
          <Hero
            onSubmit={(q) => ask(q, agenticMode)}
            disabled={busy}
            agenticMode={agenticMode}
            onToggleAgentic={setAgenticMode}
          />
        )}
      </main>
    </div>
  );
}

export default App;