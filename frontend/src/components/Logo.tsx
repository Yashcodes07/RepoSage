export default function Logo({ size = 28 }: { size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      <path
        d="M12 8 L6 17 M12 8 L18 17"
        stroke="var(--color-border)"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
      <circle cx="12" cy="6" r="2.5" fill="var(--color-accent-retrieval)" />
      <circle cx="6" cy="18.5" r="2.5" fill="var(--color-accent-citation)" />
      <circle cx="18" cy="18.5" r="2.5" fill="var(--color-accent-citation)" />
    </svg>
  );
}