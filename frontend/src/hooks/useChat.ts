import { useCallback, useState } from 'react';
import type { ChatMessage } from '../types';
import { askStandard, askAgentic, ApiError } from '../api/client';

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);

  const ask = useCallback(async (question: string, agentic: boolean) => {
    const id = crypto.randomUUID();
    setMessages((prev) => [
      ...prev,
      { id, question, status: 'pending', mode: agentic ? 'agentic' : 'standard' },
    ]);
    setBusy(true);

    try {
      const response = agentic ? await askAgentic(question) : await askStandard(question);
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, status: 'done', response } : m))
      );
    } catch (err) {
      const message = err instanceof ApiError ? err.message : 'Failed to reach the backend.';
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, status: 'error', error: message } : m))
      );
    } finally {
      setBusy(false);
    }
  }, []);

  return { messages, ask, busy };
}
