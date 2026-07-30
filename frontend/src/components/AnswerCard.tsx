import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { AskResponse, AgenticAskResponse } from '../types';
import PipelineTrace from './PipelineTrace';
import CitationChip from './CitationChip';

// The backend's system prompt asks the model to cite as
// (file_path:start-end) only — but in live testing, the model
// sometimes used its own native 【file_path:start-end】 full-width
// bracket style instead, which just sits as inert, unstyled text
// alongside the real interactive citation chips rendered below.
// Strips that exact pattern as a defensive second layer, since a
// prompt instruction alone isn't 100% reliable. Targeted at this
// specific shape (a path with an extension, then :line-line) so it
// won't accidentally eat unrelated bracketed content.
function stripRedundantBracketCitations(text: string): string {
  return text
    .replace(/【\S+\.\w+:\d+-\d+】/g, '')
    .replace(/\s+([.,])/g, '$1')
    .replace(/[ \t]{2,}/g, ' ');
}

export default function AnswerCard({
  response,
  repoUrl,
}: {
  response: AskResponse | AgenticAskResponse;
  repoUrl: string | null;
}) {
  const cleanedAnswer = stripRedundantBracketCitations(response.answer);

  return (
    <div className="rounded-lg border border-border bg-surface p-4">
      <div className="prose-answer text-[0.95rem] leading-relaxed text-ink">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{cleanedAnswer}</ReactMarkdown>
      </div>

      {response.citations.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {response.citations.map((c, i) => (
            <CitationChip key={`${c.file_path}:${c.start_line}-${i}`} citation={c} repoUrl={repoUrl} />
          ))}
        </div>
      )}

      <PipelineTrace response={response} />
    </div>
  );
}