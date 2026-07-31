// Mirrors api/schemas.py — kept in sync manually since this is a
// small project without a shared schema generator. If you add fields
// to CitationOut/AskResponse/AgenticAskResponse in the backend,
// update these too.

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

// One entry in the chat thread. `mode` records which endpoint answered
// it, since a user can toggle agentic mode mid-conversation.
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