import Logo from '../components/Logo';
import ChatApp from '../ChatApp';
import {
  IngestAnimation,
  IndexAnimation,
  RetrieveAnimation,
  RouteAnimation,
  SynthesizeAnimation,
} from '../components/ProcessAnimations';

const DEMO_VIDEO_URL = ''; // fill in once you have a real demo recording

const PROCESS_STEPS = [
  {
    title: 'Ingest',
    body: 'The repo is cloned and every file is parsed with tree-sitter into function- and class-level chunks — not naive fixed-size text splitting, so a chunk is always a complete, coherent unit of code.',
    Animation: IngestAnimation,
  },
  {
    title: 'Index',
    body: 'Each chunk is embedded into a vector store, and a parallel BM25 keyword index is built over the same chunks — catching both conceptual matches and exact identifier lookups.',
    Animation: IndexAnimation,
  },
  {
    title: 'Retrieve',
    body: 'A question runs against both indexes at once. Results are merged with Reciprocal Rank Fusion, so a chunk either retriever is confident about rises to the top.',
    Animation: RetrieveAnimation,
  },
  {
    title: 'Route',
    body: 'An agent classifies the question: a direct lookup, a question that spans multiple parts of the code and needs decomposing, or one too vague to search for — asking to clarify instead of guessing.',
    Animation: RouteAnimation,
  },
  {
    title: 'Synthesize',
    body: 'Retrieved code is passed to an LLM, which answers with every claim cited back to an exact file and line range — so you can verify it, not just trust it.',
    Animation: SynthesizeAnimation,
  },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-bg text-ink">
      <Nav />
      <HeroSection />
      <ProcessSection />
      <ChatSection />
      <AboutSection />
      <Footer />
    </div>
  );
}

function Nav() {
  return (
    <header className="sticky top-0 z-10 border-b border-border bg-bg/90 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-6">
        <div className="flex items-center ">
          <Logo size={34} />
                <span className="text-accent-retrieval">Repo</span>
            <span className="text-ink">Sage</span>
        </div>
        <nav className="flex items-center gap-6 text-sm">
          <a href="#about" className="text-muted hover:text-ink transition-colors">About</a>
          <a href="#how-it-works" className="text-muted hover:text-ink transition-colors">How it works</a>
          {DEMO_VIDEO_URL && (
            <a href="#demo" className="text-muted hover:text-ink transition-colors">Demo</a>
          )}
          <a
            href="#chat"
            className="rounded-md bg-accent-retrieval px-4 py-1.5 font-medium text-white hover:bg-accent-citation transition-colors"
          >
            Try it out
          </a>
        </nav>
      </div>
    </header>
  );
}

function HeroSection() {
  return (
    <section className="relative flex min-h-[88vh] items-center overflow-hidden">
      <div className="pointer-events-none absolute inset-0 bg-hero-dots" />
      <div className="relative mx-auto max-w-5xl px-6 py-20 text-center">
        <div
          className="animate-fade-in-up mb-8 flex justify-center opacity-0"
          style={{ animationDelay: '0ms' }}
        >
          <span className="font-mono text-6xl font-semibold tracking-tight">
            <span className="text-accent-retrieval">Repo</span>
            <span className="text-ink">Sage</span>
          </span>
        </div>

        <div
          className="animate-fade-in-up mb-6 flex justify-center opacity-0"
          style={{ animationDelay: '80ms' }}
        >
          <span className="inline-flex items-center gap-2 rounded-full border border-border bg-surface px-4 py-1.5 font-mono text-xs text-muted">
            <span className="h-1.5 w-1.5 rounded-full bg-accent-retrieval" />
            Tired of grepping through code to answer one question?
          </span>
        </div>

        <h1
          className="animate-fade-in-up font-display text-5xl font-semibold tracking-tight opacity-0 sm:text-6xl lg:text-7xl"
          style={{ animationDelay: '160ms' }}
        >
          Ask your codebase, <span className="text-accent-retrieval">get cited answers</span>
        </h1>
        <p
          className="animate-fade-in-up mx-auto mt-6 max-w-2xl text-xl text-muted opacity-0"
          style={{ animationDelay: '260ms' }}
        >
          Point RepoSage at any GitHub repo. Every answer is grounded in real
          retrieved code — file, line range, and all — powered by hybrid search
          and an agentic router underneath.
        </p>
        <div
          className="animate-fade-in-up mt-10 flex items-center justify-center gap-3 opacity-0"
          style={{ animationDelay: '360ms' }}
        >
          <a
            href="#chat"
            className="rounded-md bg-accent-retrieval px-7 py-3 text-lg font-medium text-white transition-all hover:-translate-y-0.5 hover:bg-accent-citation hover:shadow-lg hover:shadow-accent-retrieval/20"
          >
            Try it out
          </a>
          {DEMO_VIDEO_URL ? (
            <a
              href={DEMO_VIDEO_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="rounded-md border border-border px-7 py-3 text-lg font-medium text-ink hover:bg-surface transition-colors"
            >
              Watch demo
            </a>
          ) : (
            <span
              className="rounded-md border border-border px-7 py-3 text-lg font-medium text-muted cursor-not-allowed"
              title="Demo video coming soon"
            >
              Demo coming soon
            </span>
          )}
        </div>

        <a
          href="#how-it-works"
          className="animate-fade-in-up mt-16 inline-flex flex-col items-center gap-1.5 text-xs text-muted opacity-0 hover:text-ink transition-colors"
          style={{ animationDelay: '460ms' }}
        >
          See how it works
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" className="animate-bounce">
            <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </a>
      </div>
    </section>
  );
}

function AboutSection() {
  return (
    <section id="about" className="border-y border-border bg-surface">
      <div className="mx-auto max-w-3xl px-6 py-16 text-center">
        <h2 className="font-display text-sm font-semibold uppercase tracking-wide text-accent-retrieval">
          About
        </h2>
        <p className="mt-4 text-2xl font-medium tracking-tight text-ink sm:text-3xl">
          A production-grade RAG agent for exploring any codebase in plain English.
        </p>
        <p className="mt-5 text-base leading-relaxed text-muted">
          Most code search tools give you keyword matches. RepoSage retrieves
          real, coherent chunks of code via hybrid search, decomposes complex
          questions across multiple files when needed, and answers with every
          claim traceable back to an exact line — so you can verify it
          instead of just trusting it.
        </p>
      </div>
    </section>
  );
}

function ProcessSection() {
  return (
    <section id="how-it-works" className="mx-auto max-w-4xl px-6 py-20">
      <div className="text-center">
        <h2 className="font-display text-sm font-semibold uppercase tracking-wide text-accent-retrieval">
          How it works
        </h2>
        <p className="mt-3 text-2xl font-medium tracking-tight sm:text-3xl">
          From a repo URL to a cited answer
        </p>
      </div>

      <div className="mt-16 space-y-16">
        {PROCESS_STEPS.map((step, i) => {
          const Animation = step.Animation;
          const iconFirst = i % 2 === 0;
          return (
            <div key={step.title}>
              <div className={`flex flex-col items-center gap-6 sm:gap-10 ${iconFirst ? 'sm:flex-row' : 'sm:flex-row-reverse'}`}>
                <div className="flex h-36 w-full shrink-0 items-center justify-center sm:w-56">
                  <Animation />
                </div>
                <div className="w-full rounded-lg border border-dashed border-accent-retrieval/50 bg-surface px-5 py-4 sm:flex-1">
                  <span className="font-mono text-xs text-accent-citation">
                    {String(i + 1).padStart(2, '0')}
                  </span>
                  <h3 className="mt-0.5 text-lg font-semibold text-ink">{step.title}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted">{step.body}</p>
                </div>
              </div>
              {i < PROCESS_STEPS.length - 1 && <div className="mx-auto mt-16 h-px w-full bg-border" />}
            </div>
          );
        })}
      </div>
    </section>
  );
}

// The chat app embedded directly in the page, not a separate route —
// scrolling here via "Try it out" replaces the old navigate-to-/app
// jump. scroll-mt-20 offsets the sticky nav so the section heading
// isn't hidden behind it when landed on via anchor link. The app
// itself keeps its normal Sidebar + thread layout, just bounded to a
// fixed height and framed in a card instead of owning the full
// viewport.
function ChatSection() {
  return (
    <section id="chat" className="scroll-mt-20 border-t border-border bg-surface py-20">
      <div className="mx-auto max-w-5xl px-6">
        <div className="mb-10 text-center">
          <h2 className="font-display text-sm font-semibold uppercase tracking-wide text-accent-retrieval">
            Try it now
          </h2>
          <p className="mt-3 text-2xl font-medium tracking-tight sm:text-3xl">
            Index a repo, ask it anything
          </p>
        </div>
        <div className="h-[640px] overflow-hidden rounded-xl border border-border bg-bg shadow-xl shadow-black/5">
          <ChatApp />
        </div>
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer className="border-t border-border">
      <div className="mx-auto max-w-5xl px-6 py-10 text-center">
        <p className="text-sm text-muted">
          Built with FastAPI, LangGraph, ChromaDB, BM25, and Groq.
        </p>
        <a href="#chat" className="mt-4 inline-block text-sm font-medium text-accent-retrieval hover:underline">
          Try RepoSage →
        </a>
      </div>
    </footer>
  );
}