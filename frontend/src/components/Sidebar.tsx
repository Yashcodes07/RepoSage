import { useEffect, useState } from 'react';
import Logo from './Logo';

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api';

interface StatsResponse {
  chunk_count: number | null;
  indexed_repo_url: string | null;
  indexed_at: string | null;
}

// Loosely compares two repo URLs regardless of trailing slash, .git
// suffix, or http/https — good enough to warn on a real mismatch
// without being noisy about trivial formatting differences.
function normalizeRepoUrl(url: string): string {
  return url.trim().replace(/\.git$/, '').replace(/\/$/, '').replace(/^https?:\/\//, '').toLowerCase();
}

export default function Sidebar({
  repoUrl,
  onRepoUrlChange,
}: {
  repoUrl: string;
  onRepoUrlChange: (value: string) => void;
}) {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [statsError, setStatsError] = useState(false);

  useEffect(() => {
    let ignore = false;
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);

    fetch(`${API_BASE}/stats`, { signal: controller.signal })
      .then((r) => r.json())
      .then((d: StatsResponse) => {
        if (!ignore) setStats(d);
      })
      .catch(() => {
        if (!ignore) setStatsError(true);
      })
      .finally(() => clearTimeout(timeoutId));

    return () => {
      // React StrictMode (dev only) runs this effect twice — mount,
      // cleanup, mount again — to help surface exactly this class of
      // bug. Without `ignore`, the first run's aborted fetch rejects
      // into .catch() and sets statsError=true permanently, even
      // though the second run's fetch succeeds moments later. Setting
      // `ignore` here means a stale run's result is dropped instead
      // of overwriting the real one.
      ignore = true;
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, []);

  const indexedUrl = stats?.indexed_repo_url ?? null;
  const mismatch =
    !!indexedUrl && !!repoUrl.trim() && normalizeRepoUrl(indexedUrl) !== normalizeRepoUrl(repoUrl);

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
            Repo URL (for citation links)
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
            Only controls where citation chips link on GitHub — it does
            NOT change what's indexed. See "Actually indexed" below for
            what you're really querying.
          </p>
        </div>

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

        {mismatch && (
          <div className="rounded-md border border-accent-danger/40 bg-accent-danger/10 px-3 py-2">
            <p className="text-[0.7rem] leading-snug text-accent-danger">
              This doesn't match the repo URL above — answers are about{' '}
              <span className="font-mono">{indexedUrl}</span>, not what you typed.
              Re-run the ingestion + indexing CLI scripts to switch repos.
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