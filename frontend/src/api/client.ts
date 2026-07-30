import type { AskResponse, AgenticAskResponse } from '../types';

// In dev, Vite proxies /api/* to http://localhost:8000 (see
// vite.config.ts). In production, set VITE_API_BASE_URL to your
// deployed backend's URL (e.g. your Railway/Render app).
const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api';

class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
    this.name = 'ApiError';
  }
}

async function postJson<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const errBody = await res.json();
      detail = errBody.detail ?? detail;
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    throw new ApiError(detail, res.status);
  }

  return res.json() as Promise<T>;
}

export function askStandard(question: string, topK = 6): Promise<AskResponse> {
  return postJson<AskResponse>('/ask', { question, top_k: topK });
}

export function askAgentic(question: string): Promise<AgenticAskResponse> {
  return postJson<AgenticAskResponse>('/ask/agentic', { question });
}

export function githubFileUrl(repoUrl: string, filePath: string, startLine: number, endLine: number): string {
  // Normalizes a repo URL (with or without .git) into a GitHub
  // blob link with a line range, so citation chips link straight to
  // the exact code instead of just naming it.
  const cleaned = repoUrl.replace(/\.git$/, '').replace(/\/$/, '');
  return `${cleaned}/blob/main/${filePath}#L${startLine}-L${endLine}`;
}

export { ApiError };
