import { useState, type FormEvent } from 'react';

export default function ChatInput({
  onSubmit,
  disabled,
  agenticMode,
  onToggleAgentic,
}: {
  onSubmit: (question: string) => void;
  disabled: boolean;
  agenticMode: boolean;
  onToggleAgentic: (value: boolean) => void;
}) {
  const [value, setValue] = useState('');

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue('');
  }

  return (
    <form onSubmit={handleSubmit} className="border-t border-border bg-surface px-4 py-3">
      <div className="flex items-center gap-3">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ask something about the codebase…"
          disabled={disabled}
          className="flex-1 rounded-md border border-border bg-surface-raised px-3 py-2 text-sm text-ink
                     placeholder:text-muted focus:border-accent-retrieval outline-none disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="rounded-md bg-accent-retrieval px-4 py-2 text-sm font-medium text-bg
                     hover:bg-accent-retrieval/90 disabled:opacity-40 disabled:cursor-not-allowed
                     transition-colors cursor-pointer"
        >
          Ask
        </button>
      </div>

      <label className="mt-2 flex w-fit cursor-pointer items-center gap-2 font-mono text-xs text-muted">
        <input
          type="checkbox"
          checked={agenticMode}
          onChange={(e) => onToggleAgentic(e.target.checked)}
          className="accent-accent-retrieval"
        />
        Agentic mode (routes + decomposes multi-part questions)
      </label>
    </form>
  );
}
