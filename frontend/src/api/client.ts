import type { AskResponse, AgenticAskResponse } from '../types';

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

export interface IndexResult {
  repo_url: string;
  chunk_count: number;
  indexed_at: string;
}

export async function indexRepo(repoUrl: string): Promise<IndexResult> {
  // Indexing can genuinely take longer than a typical request for a
  // large repo — 2 minutes is generous headroom beyond the few
  // seconds typical repos have taken in testing.
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 120_000);
  try {
    const res = await fetch(`${API_BASE}/index`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ repo_url: repoUrl }),
      signal: controller.signal,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const errBody = await res.json();
        detail = errBody.detail ?? detail;
      } catch {
        // not JSON — fall back to statusText
      }
      throw new ApiError(detail, res.status);
    }
    return res.json() as Promise<IndexResult>;
  } finally {
    clearTimeout(timeoutId);
  }
}

export function githubFileUrl(repoUrl: string, filePath: string, startLine: number, endLine: number): string {
  const cleaned = repoUrl.replace(/\.git$/, '').replace(/\/$/, '');
  return `${cleaned}/blob/main/${filePath}#L${startLine}-L${endLine}`;
}

export { ApiError };
