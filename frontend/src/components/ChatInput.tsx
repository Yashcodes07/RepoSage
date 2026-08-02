import { useState, type FormEvent } from 'react';

export default function ChatInput({
  onSubmit,
  disabled,
  agenticMode,
  onToggleAgentic,
  variant = 'docked',
}: {
  onSubmit: (question: string) => void;
  disabled: boolean;
  agenticMode: boolean;
  onToggleAgentic: (value: boolean) => void;
  variant?: 'hero' | 'docked';
}) {
  const [value, setValue] = useState('');

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue('');
  }

  const isHero = variant === 'hero';

  return (
    <form
      onSubmit={handleSubmit}
      className={
        isHero
          ? 'w-full max-w-2xl rounded-xl border border-border bg-surface px-4 py-3 shadow-lg shadow-black/20'
          : 'border-t border-border bg-surface px-4 py-3'
      }
    >
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Ask something about the codebase…"
        disabled={disabled}
        autoFocus={isHero}
        className={
          isHero
            ? 'w-full bg-transparent text-base text-ink placeholder:text-muted outline-none disabled:opacity-50'
            : 'w-full rounded-md border border-border bg-surface-raised px-3 py-2 text-sm text-ink ' +
              'placeholder:text-muted focus:border-accent-retrieval outline-none disabled:opacity-50'
        }
      />

      <div className={isHero ? 'mt-3 flex items-center justify-between' : 'mt-2 flex items-center justify-between'}>
        <label className="flex cursor-pointer items-center gap-2 font-mono text-xs text-muted">
          <input
            type="checkbox"
            checked={agenticMode}
            onChange={(e) => onToggleAgentic(e.target.checked)}
            className="accent-accent-retrieval"
          />
          Agentic mode
        </label>

        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="rounded-md bg-accent-retrieval px-4 py-1.5 text-sm font-medium text-bg
                     hover:bg-accent-retrieval/90 disabled:opacity-40 disabled:cursor-not-allowed
                     transition-colors cursor-pointer"
        >
          Ask
        </button>
      </div>
    </form>
  );
}
