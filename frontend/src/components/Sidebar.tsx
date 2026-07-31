import { useCallback, useEffect, useRef, useState } from 'react';
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

// NOTE: /index and /upload are assumed endpoint names — swap these to
// match whatever your backend actually exposes for "start indexing a
// repo" and "index an uploaded archive". Everything else here (the
// loading/success/error states, re-fetching stats on completion) will
// keep working once the URLs are right.
type IndexState = 'idle' | 'working' | 'error';

export default function Sidebar({
  repoUrl,
  onRepoUrlChange,
}: {
  repoUrl: string;
  onRepoUrlChange: (value: string) => void;
}) {
  const [stats, setStats] = useState<StatsResponse | null>(null);
  const [statsError, setStatsError] = useState(false);
  const [indexState, setIndexState] = useState<IndexState>('idle');
  const [indexError, setIndexError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchStats = useCallback(() => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 8000);

    fetch(`${API_BASE}/stats`, { signal: controller.signal })
      .then((r) => r.json())
      .then((d: StatsResponse) => {
        setStats(d);
        setStatsError(false);
      })
      .catch(() => setStatsError(true))
      .finally(() => clearTimeout(timeoutId));

    return () => {
      clearTimeout(timeoutId);
      controller.abort();
    };
  }, []);

  useEffect(() => fetchStats(), [fetchStats]);

  async function handleIndexRepo() {
    if (!repoUrl.trim() || indexState === 'working') return;
    setIndexState('working');
    setIndexError(null);
    try {
      const res = await fetch(`${API_BASE}/index`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: repoUrl.trim() }),
      });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      setIndexState('idle');
      fetchStats();
    } catch (e) {
      setIndexState('error');
      setIndexError(e instanceof Error ? e.message : 'Indexing failed');
    }
  }

  async function handleUploadFile(file: File) {
    if (indexState === 'working') return;
    setIndexState('working');
    setIndexError(null);
    try {
      const form = new FormData();
      form.append('file', file);
      const res = await fetch(`${API_BASE}/upload`, { method: 'POST', body: form });
      if (!res.ok) throw new Error(`Server returned ${res.status}`);
      setIndexState('idle');
      fetchStats();
    } catch (e) {
      setIndexState('error');
      setIndexError(e instanceof Error ? e.message : 'Upload failed');
    }
  }

  const indexedUrl = stats?.indexed_repo_url ?? null;
  const mismatch =
    !!indexedUrl && !!repoUrl.trim() && normalizeRepoUrl(indexedUrl) !== normalizeRepoUrl(repoUrl);

  return (
    <aside className="flex h-full w-72 shrink-0 flex-col border-r border-border bg-surface">
      <div className="border-b border-border px-4 py-4">
        <div className="flex items-center gap-2">
          <Logo size={18} />
          <h1 className="font-mono text-sm font-semibold tracking-tight text-ink">RepoSage</h1>
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
              className="min-w-0 flex-1 rounded-md border border-border bg-surface-raised px-2.5 py-1.5 text-xs text-ink
                         placeholder:text-muted focus:border-accent-retrieval outline-none"
            />
            <button
              type="button"
              onClick={handleIndexRepo}
              disabled={!repoUrl.trim() || indexState === 'working'}
              title="Fetch and index this repo"
              className="shrink-0 rounded-md border border-accent-retrieval-dim bg-accent-retrieval-dim/40 px-2.5 py-1.5
                         font-mono text-xs text-accent-retrieval hover:bg-accent-retrieval-dim transition-colors
                         disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
            >
              {indexState === 'working' ? '…' : 'Index'}
            </button>
          </div>
          <p className="mt-1.5 text-[0.7rem] leading-snug text-muted">
            Fetches and indexes this repo. Also sets where citation chips link on GitHub.
          </p>
        </div>

        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleUploadFile(file);
              e.target.value = '';
            }}
          />
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={indexState === 'working'}
            className="flex w-full items-center justify-center gap-2 rounded-md border border-dashed border-border
                       bg-surface-raised/40 px-3 py-2.5 font-mono text-xs text-muted hover:border-accent-retrieval
                       hover:text-accent-retrieval transition-colors disabled:opacity-40 disabled:cursor-not-allowed
                       cursor-pointer"
          >
            <UploadIcon />
            {indexState === 'working' ? 'Indexing…' : 'Upload codebase (.zip)'}
          </button>
          {indexState === 'error' && indexError && (
            <p className="mt-1.5 text-[0.7rem] leading-snug text-accent-danger">{indexError}</p>
          )}
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
              <span className="font-mono">{indexedUrl}</span>, not what you typed. Click{' '}
              <span className="font-mono">Index</span> to switch repos.
            </p>
          </div>
        )}
      </div>

      <div className="mt-auto border-t border-border px-4 py-3">
        <p className="text-[0.7rem] leading-snug text-muted">
          Hybrid retrieval (vector + BM25) on every question. Toggle{' '}
          <span className="text-accent-retrieval">agentic mode</span> below the chat input to route through
          multi-hop decomposition.
        </p>
      </div>
    </aside>
  );
}

function UploadIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M12 16V4M12 4L7 9M12 4L17 9M4 16V18a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}