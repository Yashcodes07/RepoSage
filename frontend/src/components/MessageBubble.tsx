import type { ChatMessage } from '../types';
import AnswerCard from './AnswerCard';

export default function MessageBubble({ message, repoUrl }: { message: ChatMessage; repoUrl: string | null }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-start gap-2">
        <span className="mt-0.5 shrink-0 rounded border border-border px-1.5 py-0.5 font-mono text-[0.65rem] uppercase tracking-wide text-muted">
          {message.mode === 'agentic' ? 'agent' : 'ask'}
        </span>
        <p className="text-[0.95rem] font-medium text-ink">{message.question}</p>
      </div>

      {message.status === 'pending' && (
        <div className="ml-1 flex items-center gap-2 font-mono text-xs text-muted">
          <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-accent-retrieval" />
          {message.mode === 'agentic' ? 'routing and retrieving…' : 'retrieving…'}
        </div>
      )}

      {message.status === 'error' && (
        <div className="ml-1 rounded-md border border-accent-danger/40 bg-accent-danger/10 px-3 py-2 font-mono text-xs text-accent-danger">
          {message.error ?? 'Something went wrong answering this question.'}
        </div>
      )}

      {message.status === 'done' && message.response && (
        <AnswerCard response={message.response} repoUrl={repoUrl} />
      )}
    </div>
  );
}
