import { Link } from "react-router-dom";

const FEATURES = [
  {
    title: "Cited answers",
    body: "Every claim links to the exact page it came from. Trust it, don't just hope.",
  },
  {
    title: "Agentic retrieval",
    body: "A router sends each question to the right strategy — direct lookup, multi-step reasoning, or table analysis.",
  },
  {
    title: "Reads tables & charts",
    body: "Hybrid search plus vision means the answer can live in a table or an infographic, not just prose.",
  },
];

const STEPS = [
  ["Upload", "Drop in a PDF or DOCX. It's parsed, chunked, embedded and indexed."],
  ["Ask", "Type a question in plain English."],
  ["Get a cited answer", "Streamed back with inline [1] [2] sources you can open."],
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      {/* Nav */}
      <nav className="mx-auto flex max-w-5xl items-center justify-between px-6 py-5">
        <span className="font-mono text-lg font-semibold">
          Doc<span className="text-indigo-400">Mind</span>
        </span>
        <Link to="/login" className="text-sm text-slate-300 hover:text-white">
          Sign in
        </Link>
      </nav>

      {/* Hero */}
      <header className="mx-auto max-w-3xl px-6 pt-20 pb-24 text-center">
        <p className="mb-4 font-mono text-xs uppercase tracking-[0.2em] text-indigo-400">
          Agentic document intelligence
        </p>
        <h1 className="text-balance text-5xl font-bold leading-tight tracking-tight md:text-6xl">
          The answer is already written down.
        </h1>
        <p className="mx-auto mt-6 max-w-xl text-lg text-slate-400">
          Upload your documents and chat with them. DocMind finds the answer, reasons across
          sections, and cites the exact page — so you never skim 200 pages again.
        </p>
        <div className="mt-8 flex items-center justify-center gap-4">
          <Link
            to="/login"
            className="rounded-lg bg-indigo-500 px-6 py-3 font-medium text-white transition hover:bg-indigo-400"
          >
            Get started free
          </Link>
          <a
            href="https://github.com/Mokshith-11/docmind"
            className="rounded-lg border border-slate-700 px-6 py-3 font-medium text-slate-200 transition hover:border-slate-500"
          >
            View source
          </a>
        </div>
      </header>

      {/* How it works */}
      <section className="border-t border-slate-900 bg-slate-950">
        <div className="mx-auto grid max-w-5xl gap-8 px-6 py-16 md:grid-cols-3">
          {STEPS.map(([title, body], i) => (
            <div key={title}>
              <span className="font-mono text-sm text-indigo-400">0{i + 1}</span>
              <h3 className="mt-2 text-lg font-semibold">{title}</h3>
              <p className="mt-1 text-sm text-slate-400">{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section className="border-t border-slate-900">
        <div className="mx-auto grid max-w-5xl gap-6 px-6 py-16 md:grid-cols-3">
          {FEATURES.map((f) => (
            <div key={f.title} className="rounded-xl border border-slate-800 bg-slate-900/40 p-5">
              <h3 className="font-semibold text-slate-100">{f.title}</h3>
              <p className="mt-2 text-sm text-slate-400">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-slate-900 py-8 text-center text-sm text-slate-600">
        DocMind · built with FastAPI, Supabase, Gemini, Groq & Cohere
      </footer>
    </div>
  );
}
