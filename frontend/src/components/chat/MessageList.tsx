import { useEffect, useRef } from "react";
import type { ChatMessage } from "../../lib/types";
import CitationPanel from "./CitationPanel";

/** Renders [1] [2] markers as superscript pills so citations read inline. */
function withCitations(text: string) {
  return text.split(/(\[\d+\])/g).map((part, i) => {
    const m = part.match(/^\[(\d+)\]$/);
    if (!m) return <span key={i}>{part}</span>;
    return (
      <sup
        key={i}
        className="mx-0.5 rounded bg-emerald-500/15 px-1 font-mono text-[0.7em] text-emerald-300"
      >
        {m[1]}
      </sup>
    );
  });
}

export default function MessageList({ messages }: { messages: ChatMessage[] }) {
  const endRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (!messages.length) {
    return (
      <div className="py-12 text-center text-slate-500">
        <p>Ask a question about your documents.</p>
        <p className="mt-1 text-sm">Every answer cites the page it came from.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {messages.map((m, i) => (
        <div key={i}>
          {m.role === "user" ? (
            <div className="flex justify-end">
              <p className="max-w-[80%] rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-2 text-white">
                {m.content}
              </p>
            </div>
          ) : (
            <div className="max-w-[90%]">
              {m.route && <RouteBadge route={m.route} />}
              <div className="whitespace-pre-wrap leading-relaxed text-slate-100">
                {m.content ? withCitations(m.content) : <Thinking route={m.route} />}
              </div>
              {m.citations && <CitationPanel citations={m.citations} />}
              {m.latency_ms != null && (
                <p className="mt-2 font-mono text-xs text-slate-600">
                  {m.route} · {m.latency_ms} ms
                </p>
              )}
            </div>
          )}
        </div>
      ))}
      <div ref={endRef} />
    </div>
  );
}

const ROUTE_LABEL: Record<string, string> = {
  simple: "Direct lookup",
  multihop: "Multi-step reasoning",
  table: "Table analysis",
};

function RouteBadge({ route }: { route: string }) {
  return (
    <span className="mb-1.5 inline-block rounded bg-slate-800 px-2 py-0.5 font-mono text-[0.7rem] text-slate-400">
      {ROUTE_LABEL[route] ?? route}
    </span>
  );
}

function Thinking({ route }: { route?: string }) {
  const verb = route === "multihop" ? "Breaking down your question" : "Searching your documents";
  return (
    <span className="inline-flex gap-1 text-slate-500">
      <span className="animate-pulse">{verb}</span>
      <span className="animate-bounce">…</span>
    </span>
  );
}
