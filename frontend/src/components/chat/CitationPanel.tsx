import type { Citation } from "../../lib/types";

export default function CitationPanel({ citations }: { citations: Citation[] }) {
  if (!citations.length) return null;

  return (
    <div className="mt-3 space-y-2">
      <p className="text-xs uppercase tracking-wide text-slate-500">Sources</p>
      {citations.map((c) => (
        <details
          key={c.n}
          className="group rounded-lg border border-slate-800 bg-slate-900/60 px-3 py-2"
        >
          <summary className="cursor-pointer list-none text-sm text-slate-300 marker:hidden">
            <span className="mr-2 font-mono text-emerald-400">[{c.n}]</span>
            {c.filename}
            {c.page != null && <span className="text-slate-500"> · p.{c.page}</span>}
            {c.chunk_type === "table" && (
              <span className="ml-2 rounded bg-indigo-500/15 px-1.5 py-0.5 text-xs text-indigo-300">
                table
              </span>
            )}
          </summary>
          <p className="mt-2 whitespace-pre-wrap border-l-2 border-slate-700 pl-3 text-xs leading-relaxed text-slate-400">
            {c.excerpt}
          </p>
        </details>
      ))}
    </div>
  );
}
