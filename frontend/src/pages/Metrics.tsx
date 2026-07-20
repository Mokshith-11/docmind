import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../lib/api";
import type { Workspace } from "../lib/types";

interface Metrics {
  queries: number;
  avg_latency_ms: number;
  p50_latency_ms: number;
  p95_latency_ms: number;
  cache_hits: number;
  cache_hit_rate: number;
  est_cost_usd: number;
  tokens_in: number;
  tokens_out: number;
  routes: { route: string; count: number }[];
  per_day: { day: string; queries: number; cost: number }[];
  evals: { ran_at: string; faithfulness: number | null; answer_relevance: number | null }[];
}

const ROUTE_COLORS: Record<string, string> = {
  simple: "#818cf8",
  multihop: "#f6c177",
  table: "#5eead4",
  cache: "#94a3b8",
};

function Stat({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      {sub && <p className="text-xs text-slate-500">{sub}</p>}
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-4">
      <p className="mb-3 text-sm font-medium text-slate-300">{title}</p>
      {children}
    </div>
  );
}

export default function Metrics() {
  const [m, setM] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Workspace[]>("/api/workspaces")
      .then((ws) => (ws[0] ? api<Metrics>(`/api/metrics?workspace=${ws[0].id}`) : null))
      .then((data) => data && setM(data))
      .catch((e) => setError(String(e)));
  }, []);

  const latestEval = m?.evals?.[0];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="flex items-center justify-between border-b border-slate-800 px-8 py-4">
        <h1 className="text-xl font-semibold">Observability</h1>
        <Link to="/app" className="text-sm text-slate-400 hover:text-slate-200">← Back</Link>
      </header>

      <main className="mx-auto max-w-4xl space-y-6 p-8">
        {error && <p className="text-sm text-red-400">{error}</p>}
        {!m ? (
          <p className="text-slate-500">Loading…</p>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
              <Stat label="Queries" value={String(m.queries)} />
              <Stat label="Avg latency" value={`${(m.avg_latency_ms / 1000).toFixed(1)}s`}
                    sub={`p95 ${(m.p95_latency_ms / 1000).toFixed(1)}s`} />
              <Stat label="Cache hit rate" value={`${Math.round(m.cache_hit_rate * 100)}%`}
                    sub={`${m.cache_hits} hits`} />
              <Stat label="Est. cost" value={`$${m.est_cost_usd.toFixed(4)}`}
                    sub={`${m.tokens_in + m.tokens_out} tokens`} />
            </div>

            {latestEval && (
              <div className="grid grid-cols-2 gap-4">
                <Stat label="Faithfulness (RAGAS)"
                      value={latestEval.faithfulness != null ? latestEval.faithfulness.toFixed(2) : "—"}
                      sub="answer grounded in sources" />
                <Stat label="Answer relevance (RAGAS)"
                      value={latestEval.answer_relevance != null ? latestEval.answer_relevance.toFixed(2) : "—"}
                      sub="answer addresses the question" />
              </div>
            )}

            <div className="grid gap-4 md:grid-cols-2">
              <Panel title="Route distribution">
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={m.routes}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="route" stroke="#64748b" fontSize={12} />
                    <YAxis stroke="#64748b" fontSize={12} allowDecimals={false} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b" }} />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {m.routes.map((r) => (
                        <Cell key={r.route} fill={ROUTE_COLORS[r.route] ?? "#818cf8"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Panel>

              <Panel title="Queries per day">
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={m.per_day}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="day" stroke="#64748b" fontSize={11} />
                    <YAxis stroke="#64748b" fontSize={12} allowDecimals={false} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #1e293b" }} />
                    <Line type="monotone" dataKey="queries" stroke="#5eead4" strokeWidth={2} dot />
                  </LineChart>
                </ResponsiveContainer>
              </Panel>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
