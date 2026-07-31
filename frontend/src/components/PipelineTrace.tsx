import { useState } from 'react';
import type { AskResponse, AgenticAskResponse } from '../types';

function isAgentic(r: AskResponse | AgenticAskResponse): r is AgenticAskResponse {
  return 'route' in r;
}

const ROUTE_LABEL: Record<string, string> = {
  simple: 'Direct retrieval',
  multi_hop: 'Multi-hop decomposition',
  clarify: 'Clarification needed',
};

/**
 * Shows the actual pipeline that produced this answer — router
 * decision, sub-questions if decomposed, chunk count — instead of
 * hiding that behind a generic "thinking..." spinner. The whole point
 * of this project is the retrieval engineering underneath, so this
 * stays available on every answer.
 *
 * Collapsed by default: on a long thread this was previously always-on
 * and ate as much vertical space as the answer itself. Now it reads as
 * one summary line (route + chunk count) that expands into the full
 * trace on click — the detail is still one click away, not gone.
 */
export default function PipelineTrace({ response }: { response: AskResponse | AgenticAskResponse }) {
  const [open, setOpen] = useState(false);
  const agentic = isAgentic(response);
  const needsClarification = agentic ? response.needs_clarification : false;
  const routeLabel = agentic ? ROUTE_LABEL[response.route] ?? response.route : 'Hybrid retrieval';

  return (
    <div className="mt-3 rounded-md border border-border/70 font-mono text-xs text-muted">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 px-3 py-1.5 text-left hover:bg-surface-raised/50 transition-colors cursor-pointer"
      >
        <span className={agentic && response.route === 'clarify' ? 'text-accent-danger' : 'text-accent-retrieval'}>
          {routeLabel}
        </span>
        {!needsClarification && (
          <span className="text-muted">
            · {response.retrieved_chunk_count} chunk{response.retrieved_chunk_count === 1 ? '' : 's'}
          </span>
        )}
        <span className="ml-auto text-muted">{open ? '▾' : '▸'}</span>
      </button>

      {open && (
        <div className="border-t border-border/70 px-3 py-2">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            {agentic ? (
              <>
                <Step label="Router" />
                <Arrow />
                <Step label={routeLabel} tone={response.route === 'clarify' ? 'danger' : 'retrieval'} />
                {response.sub_questions && response.sub_questions.length > 0 && (
                  <>
                    <Arrow />
                    <Step label={`${response.sub_questions.length} sub-questions`} tone="retrieval" />
                  </>
                )}
                {!response.needs_clarification && (
                  <>
                    <Arrow />
                    <Step label="Hybrid retrieval" tone="retrieval" />
                    <Arrow />
                    <Step label="Synthesize" tone="citation" />
                  </>
                )}
              </>
            ) : (
              <>
                <Step label="Hybrid retrieval" tone="retrieval" />
                <Arrow />
                <Step label="Synthesize" tone="citation" />
              </>
            )}
          </div>

          {agentic && response.sub_questions && response.sub_questions.length > 0 && (
            <ul className="mt-2 space-y-0.5 border-t border-border pt-2 pl-3">
              {response.sub_questions.map((q, i) => (
                <li key={i} className="list-disc marker:text-accent-retrieval">
                  {q}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function Step({ label, tone = 'muted' }: { label: string; tone?: 'retrieval' | 'citation' | 'danger' | 'muted' }) {
  const toneClass = {
    retrieval: 'text-accent-retrieval',
    citation: 'text-accent-citation',
    danger: 'text-accent-danger',
    muted: 'text-muted',
  }[tone];
  return <span className={toneClass}>{label}</span>;
}

function Arrow() {
  return <span className="text-border">→</span>;
}