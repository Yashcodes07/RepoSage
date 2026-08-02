import type { AskResponse, AgenticAskResponse } from '../types';

function isAgentic(r: AskResponse | AgenticAskResponse): r is AgenticAskResponse {
  return 'route' in r;
}

const ROUTE_LABEL: Record<string, string> = {
  simple: 'Direct retrieval',
  multi_hop: 'Multi-hop decomposition',
  clarify: 'Clarification needed',
};

export default function PipelineTrace({ response }: { response: AskResponse | AgenticAskResponse }) {
  const agentic = isAgentic(response);
  const needsClarification = agentic ? response.needs_clarification : false;

  return (
    <div className="mt-3 rounded-md border border-border bg-surface/60 px-3 py-2 font-mono text-xs text-muted">
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        {agentic ? (
          <>
            <Step label="Router" />
            <Arrow />
            <Step
              label={ROUTE_LABEL[response.route] ?? response.route}
              tone={response.route === 'clarify' ? 'danger' : 'retrieval'}
            />
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
        {!needsClarification && (
          <span className="ml-auto text-muted">
            {response.retrieved_chunk_count} chunk{response.retrieved_chunk_count === 1 ? '' : 's'}
          </span>
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
