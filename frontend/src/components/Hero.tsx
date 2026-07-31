import Logo from './Logo';
import ChatInput from './ChatInput';

export default function Hero({
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
  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 px-6">
      <div className="flex flex-col items-center gap-3 text-center">
        <Logo size={36} />
        <h1 className="font-display text-2xl font-semibold tracking-tight text-ink">
          RepoSage
        </h1>
        <p className="max-w-sm text-sm text-muted">
          Ask anything about an indexed codebase — every answer is grounded
          in real, cited source.
        </p>
      </div>

      <ChatInput
        onSubmit={onSubmit}
        disabled={disabled}
        agenticMode={agenticMode}
        onToggleAgentic={onToggleAgentic}
        variant="hero"
      />
    </div>
  );
}