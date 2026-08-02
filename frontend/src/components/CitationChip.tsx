import { useState } from 'react';
import type { Citation } from '../types';
import { githubFileUrl } from '../api/client';

export default function CitationChip({ citation, repoUrl }: { citation: Citation; repoUrl: string | null }) {
  const [open, setOpen] = useState(false);
  const label = `${citation.file_path}:${citation.start_line}-${citation.end_line}`;

  return (
    <span className="inline-block align-baseline">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="inline-flex items-center gap-1 rounded border border-accent-citation-dim bg-accent-citation-dim/40
                   px-1.5 py-0.5 font-mono text-xs text-accent-citation hover:bg-accent-citation-dim
                   transition-colors cursor-pointer"
        title={citation.name ? `${citation.name} — click to preview` : 'click to preview'}
      >
        {label}
      </button>

      {open && (
        <span className="block my-2 rounded-md border border-border bg-surface-raised overflow-hidden not-italic">
          <span className="flex items-center justify-between border-b border-border bg-surface px-3 py-1.5">
            <span className="font-mono text-xs text-muted">
              {citation.name || 'code'}
            </span>
            {repoUrl && (
              <a
                href={githubFileUrl(repoUrl, citation.file_path, citation.start_line, citation.end_line)}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono text-xs text-accent-retrieval hover:underline"
              >
                Open on GitHub ↗
              </a>
            )}
          </span>
          <code className="block whitespace-pre-wrap break-words px-3 py-2 font-mono text-xs text-ink/90 overflow-x-auto">
            {citation.code
              ? citation.code
              : '(no preview available — open on GitHub to view)'}
          </code>
        </span>
      )}
    </span>
  );
}
