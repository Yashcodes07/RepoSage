import { useCallback, useEffect, useState } from 'react';
import Logo from './Logo';
import { indexRepo, ApiError } from '../api/client';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api';

interface StatsResponse {
  chunk_count: number | null;
  indexed_repo_url: string | null;
  indexed_at: string | null;
}

function normalizeRepoUrl(url: string): string {
  return url.trim().replace(/\.git$/, '').replace(/\/$/, '').replace(/^https?:\/\//, '').toLowerCase();
}

type IndexingState = 'idle' | 'indexing' | 'error';

export default function Sidebar({
  repoUrl,
  onRepoUrlChange,
}: {
  repoUrl: string;
  onRepoUrlChange: (value: string) => void;
}) {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [statsError, setStatsError] = useState(false);
  const [indexingState, setIndexingState] = useState<IndexingState>('idle');
  const [indexingError, setIndexingError] = useState<string | null>(null);

  const fetchStats = useCallback((ignoreRef?: { current: boolean }) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);

    fetch(`${API_BASE}/stats`, { signal: controller.signal })
      .then((r) => r.json())
      .then((d: StatsResponse) => {
        if (!ignoreRef?.current) {
          setStats(d);
          setStatsError(false);
        }
      })
      .catch(() => {
        if (!ignoreRef?.current) setStatsError(true);
      })
      .finally(() => clearTimeout(timeoutId));

    return () => {
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, []);

  useEffect(() => {
    const ignoreRef = { current: false };
    const cleanup = fetchStats(ignoreRef);
    return () => {
      ignoreRef.current = true;
      cleanup();
    };
  }, [fetchStats]);

  async function handleIndex() {
    if (!repoUrl.trim() || indexingState === 'indexing') return;
    setIndexingState('indexing');
    setIndexingError(null);
    try {
      const result = await indexRepo(repoUrl.trim());
      setStats({
        chunk_count: result.chunk_count,
        indexed_repo_url: result.repo_url,
        indexed_at: result.indexed_at,
      });
      setStatsError(false);
      setIndexingState('idle');
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Failed to reach the backend.';
      setIndexingError(message);
      setIndexingState('error');
    }
  }

  const indexedUrl = stats?.indexed_repo_url ?? null;
  const mismatch =
    !!indexedUrl && !!repoUrl.trim() && normalizeRepoUrl(indexedUrl) !== normalizeRepoUrl(repoUrl);
  const isIndexing = indexingState === 'indexing';

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col border-r border-border bg-surface">
      <div className="border-b border-border px-4 py-4">
        <div className="flex items-center gap-2">
          <Logo size={18} />
          <h1 className="font-mono text-sm font-semibold tracking-tight text-ink">
            RepoSage
          </h1>
        </div>
        <p className="mt-1 text-xs text-muted">Codebase RAG agent</p>
      </div>

      <div className="flex flex-col gap-4 px-4 py-4">
        <div>
          <label className="mb-1.5 block font-mono text-xs uppercase tracking-wide text-muted">
            Repo URL
          </label>
          <div className="flex gap-1.5">
            <input
              type="text"
              value={repoUrl}
              onChange={(e) => onRepoUrlChange(e.target.value)}
              placeholder="https://github.com/user/repo"
              disabled={isIndexing}
              className="w-full rounded-md border border-border bg-surface-raised px-2.5 py-1.5 text-xs text-ink
                         placeholder:text-muted focus:border-accent-retrieval outline-none disabled:opacity-50"
            />
            <button
              type="button"
              onClick={handleIndex}
              disabled={isIndexing || !repoUrl.trim()}
              className="shrink-0 rounded-md bg-accent-retrieval px-2.5 py-1.5 font-mono text-xs font-medium text-bg
                         hover:bg-accent-retrieval/90 disabled:opacity-40 disabled:cursor-not-allowed
                         transition-colors cursor-pointer"
            >
              {isIndexing ? '…' : 'Index'}
            </button>
          </div>
          <p className="mt-1.5 text-[0.7rem] leading-snug text-muted">
            {isIndexing
              ? 'Cloning and indexing — usually a few seconds, longer for large repos.'
              : 'Click Index to clone + index this repo, or just re-link citations to an already-indexed one.'}
          </p>
        </div>

        {indexingState === 'error' && indexingError && (
          <div className="rounded-md border border-accent-danger/40 bg-accent-danger/10 px-3 py-2">
            <p className="text-[0.7rem] leading-snug text-accent-danger">{indexingError}</p>
          </div>
        )}

        <div className="rounded-md border border-border bg-surface-raised px-3 py-2.5">
          <p className="font-mono text-xs uppercase tracking-wide text-muted">Index status</p>

          {statsError ? (
            <p className="mt-1.5 font-mono text-sm text-accent-danger">backend unreachable</p>
          ) : stats === null ? (
            <p className="mt-1.5 font-mono text-sm text-accent-retrieval">loading…</p>
          ) : (
            <>
              <p className="mt-1.5 font-mono text-sm text-accent-retrieval">
                {stats.chunk_count ?? '—'} chunks indexed
              </p>
              <p className="mt-1 text-[0.7rem] leading-snug text-muted">
                Actually indexed:{' '}
                <span className="font-mono text-ink/80">
                  {indexedUrl ?? 'unknown (pre-existing index, or built before repo tracking was added)'}
                </span>
              </p>
            </>
          )}
        </div>

        {mismatch && !isIndexing && (
          <div className="rounded-md border border-accent-danger/40 bg-accent-danger/10 px-3 py-2">
            <p className="text-[0.7rem] leading-snug text-accent-danger">
              This doesn't match the repo URL above — answers are about{' '}
              <span className="font-mono">{indexedUrl}</span>, not what you typed.
              Click Index to switch, or edit the URL back to match.
            </p>
          </div>
        )}
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
