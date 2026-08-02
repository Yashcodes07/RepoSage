/**
 * One small looping animation per pipeline step, in the site's own
 * red/white palette. These are original inline SVG + CSS-keyframe
 * animations — inspired by the *pattern* of a reference site (an
 * icon animation paired with each step), not copies of its actual
 * GIF assets, which are that site's own artwork.
 */

export function IngestAnimation() {
  return (
    <svg viewBox="0 0 200 140" className="h-full w-full max-w-[220px]" aria-hidden="true">
      <rect x="4" y="4" width="192" height="132" rx="10" fill="none" stroke="var(--color-border)" strokeWidth="1" />
      {/* repo icon sliding right into the index */}
      <g className="animate-ingest-file">
        <rect x="20" y="52" width="30" height="36" rx="3" fill="var(--color-surface-raised)" stroke="var(--color-accent-retrieval)" strokeWidth="2" />
        <line x1="26" y1="62" x2="44" y2="62" stroke="var(--color-accent-retrieval)" strokeWidth="2" strokeLinecap="round" />
        <line x1="26" y1="70" x2="44" y2="70" stroke="var(--color-accent-retrieval)" strokeWidth="2" strokeLinecap="round" />
        <line x1="26" y1="78" x2="38" y2="78" stroke="var(--color-accent-retrieval)" strokeWidth="2" strokeLinecap="round" />
      </g>
      <path d="M60 70 H140" stroke="var(--color-border)" strokeWidth="2" strokeDasharray="4 4" />
      <path d="M132 62 L142 70 L132 78" fill="none" stroke="var(--color-accent-citation)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
      {/* index/store cylinder, ticks appearing on loop */}
      <g transform="translate(150 40)">
        <ellipse cx="20" cy="8" rx="20" ry="7" fill="none" stroke="var(--color-accent-citation)" strokeWidth="2" />
        <path d="M0 8 V52 A20 7 0 0 0 40 52 V8" fill="none" stroke="var(--color-accent-citation)" strokeWidth="2" />
        <path d="M0 26 A20 7 0 0 0 40 26" fill="none" stroke="var(--color-accent-citation)" strokeWidth="1.5" />
        <path
          className="animate-ingest-check"
          d="M11 30 L17 36 L29 22"
          fill="none"
          stroke="var(--color-accent-retrieval)"
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </g>
    </svg>
  );
}

export function IndexAnimation() {
  const lines = [0, 1, 2, 3, 4];
  return (
    <svg viewBox="0 0 200 140" className="h-full w-full max-w-[220px]" aria-hidden="true">
      <rect x="4" y="4" width="192" height="132" rx="10" fill="none" stroke="var(--color-border)" strokeWidth="1" />
      {/* one long block of lines splitting into three grouped chunks */}
      <g className="animate-index-split">
        {lines.map((i) => (
          <rect key={i} x="30" y={30 + i * 16} width={140 - (i % 2) * 20} height="6" rx="3" fill="var(--color-accent-retrieval)" opacity={0.85 - i * 0.1} />
        ))}
      </g>
      <g className="animate-index-chunks" opacity={0}>
        <rect x="20" y="30" width="45" height="6" rx="3" fill="var(--color-accent-retrieval)" />
        <rect x="20" y="42" width="35" height="6" rx="3" fill="var(--color-accent-retrieval)" />
        <rect x="80" y="30" width="45" height="6" rx="3" fill="var(--color-accent-citation)" />
        <rect x="80" y="42" width="38" height="6" rx="3" fill="var(--color-accent-citation)" />
        <rect x="140" y="30" width="40" height="6" rx="3" fill="var(--color-accent-retrieval)" />
        <rect x="140" y="42" width="30" height="6" rx="3" fill="var(--color-accent-retrieval)" />
      </g>
    </svg>
  );
}

export function RetrieveAnimation() {
  const dots = Array.from({ length: 12 }, (_, i) => ({
    cx: 30 + (i % 4) * 35,
    cy: 35 + Math.floor(i / 4) * 30,
  }));
  return (
    <svg viewBox="0 0 200 140" className="h-full w-full max-w-[220px]" aria-hidden="true">
      <rect x="4" y="4" width="192" height="132" rx="10" fill="none" stroke="var(--color-border)" strokeWidth="1" />
      {dots.map((d, i) => (
        <circle key={i} cx={d.cx} cy={d.cy} r="5" fill={i === 5 || i === 6 ? 'var(--color-accent-retrieval)' : 'var(--color-border)'} />
      ))}
      <g className="animate-retrieve-scan">
        <circle cx="0" cy="0" r="22" fill="none" stroke="var(--color-accent-citation)" strokeWidth="3" />
        <line x1="16" y1="16" x2="30" y2="30" stroke="var(--color-accent-citation)" strokeWidth="3" strokeLinecap="round" />
      </g>
    </svg>
  );
}

export function RouteAnimation() {
  return (
    <svg viewBox="0 0 200 140" className="h-full w-full max-w-[220px]" aria-hidden="true">
      <rect x="4" y="4" width="192" height="132" rx="10" fill="none" stroke="var(--color-border)" strokeWidth="1" />
      <circle cx="30" cy="70" r="10" fill="none" stroke="var(--color-ink)" strokeWidth="2" />
      <path d="M40 70 H70" stroke="var(--color-border)" strokeWidth="2" />
      <path d="M70 70 L110 30 M70 70 L110 70 M70 70 L110 110" fill="none" stroke="var(--color-border)" strokeWidth="2" />
      <circle cx="115" cy="30" r="9" fill="none" stroke="var(--color-border)" strokeWidth="2" />
      <circle cx="115" cy="70" r="9" fill="none" stroke="var(--color-border)" strokeWidth="2" />
      <circle cx="115" cy="110" r="9" fill="none" stroke="var(--color-border)" strokeWidth="2" />
      <g className="animate-route-path-a">
        <path d="M70 70 L110 30" fill="none" stroke="var(--color-accent-retrieval)" strokeWidth="3" strokeLinecap="round" />
        <circle cx="115" cy="30" r="9" fill="var(--color-accent-retrieval)" />
      </g>
      <g className="animate-route-path-b">
        <path d="M70 70 L110 70" fill="none" stroke="var(--color-accent-citation)" strokeWidth="3" strokeLinecap="round" />
        <circle cx="115" cy="70" r="9" fill="var(--color-accent-citation)" />
      </g>
      <g className="animate-route-path-c">
        <path d="M70 70 L110 110" fill="none" stroke="var(--color-accent-danger)" strokeWidth="3" strokeLinecap="round" />
        <circle cx="115" cy="110" r="9" fill="var(--color-accent-danger)" />
      </g>
    </svg>
  );
}

export function SynthesizeAnimation() {
  return (
    <svg viewBox="0 0 200 140" className="h-full w-full max-w-[220px]" aria-hidden="true">
      <rect x="4" y="4" width="192" height="132" rx="10" fill="none" stroke="var(--color-border)" strokeWidth="1" />
      <rect x="30" y="35" width="140" height="50" rx="10" fill="var(--color-surface-raised)" stroke="var(--color-border)" strokeWidth="1.5" />
      <path d="M50 85 L38 100 L62 85 Z" fill="var(--color-surface-raised)" stroke="var(--color-border)" strokeWidth="1.5" />
      <circle className="animate-synth-dot" cx="70" cy="60" r="5" fill="var(--color-accent-retrieval)" />
      <circle className="animate-synth-dot animation-delay-150" cx="90" cy="60" r="5" fill="var(--color-accent-retrieval)" />
      <circle className="animate-synth-dot animation-delay-300" cx="110" cy="60" r="5" fill="var(--color-accent-retrieval)" />
      <g className="animate-synth-cite" opacity={0}>
        <rect x="128" y="50" width="34" height="18" rx="4" fill="var(--color-accent-citation-dim)" stroke="var(--color-accent-citation)" strokeWidth="1.5" />
        <text x="145" y="63" textAnchor="middle" fontSize="9" fontFamily="var(--font-mono)" fill="var(--color-accent-citation)">
          :42
        </text>
      </g>
    </svg>
  );
}