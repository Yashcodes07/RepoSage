import type { ChatMessage } from '../types';
import AnswerCard from './AnswerCard';

// A "turn" here is one Q+A pair. Rather than the question and its
// eventual answer just stacking as separate flat elements (the old
// layout — a label, a line of text, then whatever floats below it),
// each turn is one visually contained unit: a quiet question row on
// top, connected directly into the answer beneath it, so a thread of
// many turns reads as a sequence of distinct exchanges rather than
// one undifferentiated scroll of text.
export default function MessageBubble({ message, repoUrl }: { message: ChatMessage; repoUrl: string | null }) {
  return (
    <div className="rounded-lg border border-border/70 bg-surface-raised/40">
      <div className="flex items-start gap-2.5 px-4 py-3.5">
        <span
          className={
            'mt-0.5 shrink-0 rounded border px-1.5 py-0.5 font-mono text-[0.65rem] uppercase tracking-wide ' +
            (message.mode === 'agentic'
              ? 'border-accent-retrieval-dim bg-accent-retrieval-dim/40 text-accent-retrieval'
              : 'border-border text-muted')
          }
        >
          {message.mode === 'agentic' ? 'agent' : 'ask'}
        </span>
        <p className="text-[0.95rem] font-medium leading-snug text-ink">{message.question}</p>
      </div>

      {message.status === 'pending' && (
        <div className="flex items-center gap-2 border-t border-border/70 px-4 py-3 font-mono text-xs text-muted">
          <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-accent-retrieval" />
          {message.mode === 'agentic' ? 'routing and retrieving…' : 'retrieving…'}
        </div>
      )}

      {message.status === 'error' && (
        <div className="border-t border-accent-danger/30 bg-accent-danger/5 px-4 py-3 font-mono text-xs text-accent-danger">
          {message.error ?? 'Something went wrong answering this question.'}
        </div>
      )}

      {message.status === 'done' && message.response && (
        <div className="border-t border-border/70 p-4">
          <AnswerCard response={message.response} repoUrl={repoUrl} />
        </div>
      )}
    </div>
  );
}