export interface Citation {
  file_path: string;
  start_line: number;
  end_line: number;
  name: string;
  code: string;
  github_url?: string | null;
}

export interface AskResponse {
  question: string;
  answer: string;
  citations: Citation[];
  retrieved_chunk_count: number;
}

export type AgentRoute = 'simple' | 'multi_hop' | 'clarify';

export interface AgenticAskResponse extends AskResponse {
  route: AgentRoute;
  sub_questions: string[] | null;
  needs_clarification: boolean;
}

export interface ChatMessage {
  id: string;
  question: string;
  status: 'pending' | 'done' | 'error';
  mode: 'standard' | 'agentic';
  response?: AskResponse | AgenticAskResponse;
  error?: string;
}

export interface IndexStats {
  chunkCount: number | null;
  indexedRepoUrl: string | null;
  indexedAt: string | null;
}
