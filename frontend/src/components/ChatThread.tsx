import { useEffect, useRef } from 'react';
import type { ChatMessage } from '../types';
import MessageBubble from './MessageBubble';

export default function ChatThread({ messages, repoUrl }: { messages: ChatMessage[]; repoUrl: string | null }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [messages.length, messages[messages.length - 1]?.status]);

  return (
    <div className="flex flex-col gap-6 px-6 py-6">
      {messages.map((m) => (
        <MessageBubble key={m.id} message={m} repoUrl={repoUrl} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}