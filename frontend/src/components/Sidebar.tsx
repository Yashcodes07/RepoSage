import { useEffect, useState } from 'react';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api';

export default function Sidebar({
  repoUrl,
  onRepoUrlChange,
}: {
  repoUrl: string;
  onRepoUrlChange: (value: string) => void;
}) {
  const [chunkCount, setChunkCount] = useState<number | null>(null);
  const [statsError, setStatsError] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/stats`)
      .then((r) => r.json())
      .then((d) => setChunkCount(d.chunk_count))
      .catch(() => setStatsError(true));
  }, []);

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col border-r border-border bg-surface">
      <div className="border-b border-border px-4 py-4">
        <h1 className="font-mono text-sm font-semibold tracking-tight text-ink">
          RepoSage
        </h1>
        <p className="mt-1 text-xs text-muted">Codebase RAG agent</p>
      </div>

      <div className="flex flex-col gap-4 px-4 py-4">
        <div>
          <label className="mb-1.5 block font-mono text-xs uppercase tracking-wide text-muted">
            Repo URL
          </label>
          <input
            type="text"
            value={repoUrl}
            onChange={(e) => onRepoUrlChange(e.target.value)}
            placeholder="https://github.com/user/repo"
            className="w-full rounded-md border border-border bg-surface-raised px-2.5 py-1.5 text-xs text-ink
                       placeholder:text-muted focus:border-accent-retrieval outline-none"
          />
          <p className="mt-1.5 text-[0.7rem] leading-snug text-muted">
            Used to link citations to GitHub. Indexing itself runs via the{' '}
            <code className="font-mono">ingestion/</code> and{' '}
            <code className="font-mono">indexing/</code> CLI scripts.
          </p>
        </div>

        <div className="rounded-md border border-border bg-surface-raised px-3 py-2.5">
          <p className="font-mono text-xs uppercase tracking-wide text-muted">Index status</p>
          <p className="mt-1.5 font-mono text-sm text-accent-retrieval">
            {statsError ? (
              <span className="text-accent-danger">backend unreachable</span>
            ) : chunkCount === null ? (
              'loading…'
            ) : (
              `${chunkCount} chunks indexed`
            )}
          </p>
        </div>
      </div>

      <div className="mt-auto border-t border-border px-4 py-3">
        <p className="text-[0.7rem] leading-snug text-muted">
          Hybrid retrieval (vector + BM25) on every question. Toggle{' '}
          <span className="text-accent-retrieval">agentic mode</span> below the
          chat input to route through multi-hop decomposition.
        </p>
      </div>
    </aside>
  );
}
