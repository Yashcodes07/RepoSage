// An original bolt mark for RepoSage — a plain, generic lightning-bolt
// silhouette (the same basic shape used by countless "speed/energy"
// icons), rendered in the site's own red gradient rather than any
// particular product's branded logo. Animated with a slow pulsing
// glow so it reads as "live" rather than a static mark.
export default function Logo({ size = 28, className = '' }: { size?: number; className?: string }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className={`animate-logo-glow ${className}`}
    >
      <defs>
        <linearGradient id="reposage-bolt-gradient" x1="4" y1="2" x2="20" y2="22" gradientUnits="userSpaceOnUse">
          <stop offset="0%" stopColor="var(--color-accent-retrieval)" />
          <stop offset="100%" stopColor="var(--color-accent-citation)" />
        </linearGradient>
      </defs>
      <path
        d="M13 1.5 L4.5 13.5 H10.5 L9 22.5 L19.5 9.5 H12.5 L14.5 1.5 Z"
        fill="url(#reposage-bolt-gradient)"
        stroke="var(--color-accent-citation)"
        strokeWidth="0.75"
        strokeLinejoin="round"
      />
    </svg>
  );
}