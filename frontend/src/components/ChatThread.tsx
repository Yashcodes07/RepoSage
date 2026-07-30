import { useEffect, useRef } from 'react';
import type { ChatMessage } from '../types';
import MessageBubble from './MessageBubble';

export default function ChatThread({ messages, repoUrl }: { messages: ChatMessage[]; repoUrl: string | null }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages.length, messages[messages.length - 1]?.status]);

  if (messages.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center">
        <p className="font-mono text-sm text-muted">No questions yet.</p>
        <p className="max-w-sm text-sm text-muted">
          Index a repo on the left, then ask something like{' '}
          <span className="font-mono text-accent-retrieval">"where is auth handled"</span>.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6 px-6 py-6">
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} repoUrl={repoUrl} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
