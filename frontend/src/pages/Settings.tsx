import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import type { Member, Usage, Workspace } from "../lib/types";

function Meter({ label, used, limit }: { label: string; used: number; limit: number | null }) {
  const pct = limit ? Math.min(100, (used / limit) * 100) : 0;
  const full = limit != null && used >= limit;
  return (
    <div>
      <div className="mb-1 flex justify-between text-sm">
        <span className="text-slate-300">{label}</span>
        <span className={full ? "text-red-400" : "text-slate-400"}>
          {used}
          {limit != null ? ` / ${limit}` : " · unlimited"}
        </span>
      </div>
      {limit != null && (
        <div className="h-2 overflow-hidden rounded-full bg-slate-800">
          <div
            className={`h-full ${full ? "bg-red-500" : "bg-indigo-500"}`}
            style={{ width: `${pct}%` }}
          />
        </div>
      )}
    </div>
  );
}

export default function Settings() {
  const [ws, setWs] = useState<Workspace | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [email, setEmail] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  const load = useCallback(async (id: string) => {
    const [u, m] = await Promise.all([
      api<Usage>(`/api/workspaces/${id}/usage`),
      api<Member[]>(`/api/workspaces/${id}/members`).catch(() => [] as Member[]),
    ]);
    setUsage(u);
    setMembers(m);
  }, []);

  useEffect(() => {
    api<Workspace[]>("/api/workspaces").then((list) => {
      const first = list[0] ?? null;
      setWs(first);
      if (first) load(first.id);
    });
  }, [load]);

  async function addMember(e: React.FormEvent) {
    e.preventDefault();
    if (!ws || !email.trim()) return;
    setMsg(null);
    try {
      await api(`/api/workspaces/${ws.id}/members`, {
        method: "POST",
        body: JSON.stringify({ email: email.trim(), role: "viewer" }),
      });
      setEmail("");
      await load(ws.id);
    } catch (err) {
      setMsg(err instanceof Error ? err.message : String(err));
    }
  }

  async function removeMember(id: string) {
    if (!ws) return;
    await api(`/api/workspaces/${ws.id}/members/${id}`, { method: "DELETE" }).catch(() => {});
    await load(ws.id);
  }

  async function upgrade() {
    if (!ws) return;
    try {
      const { url } = await api<{ url: string }>(
        `/api/billing/checkout?workspace_id=${ws.id}`,
        { method: "POST" },
      );
      window.location.href = url;
    } catch {
      setMsg("Billing isn't set up yet (Lemon Squeezy keys pending).");
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="flex items-center justify-between border-b border-slate-800 px-8 py-4">
        <h1 className="text-xl font-semibold">Settings</h1>
        <Link to="/app" className="text-sm text-slate-400 hover:text-slate-200">
          ← Back
        </Link>
      </header>

      <main className="mx-auto max-w-2xl space-y-8 p-8">
        {/* Plan + usage */}
        <section className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/50 p-5">
          <div className="flex items-center justify-between">
            <h2 className="font-medium">
              Plan:{" "}
              <span className={usage?.plan === "pro" ? "text-emerald-400" : "text-slate-300"}>
                {usage?.plan?.toUpperCase() ?? "…"}
              </span>
            </h2>
            {usage?.plan !== "pro" && (
              <button
                onClick={upgrade}
                className="rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-medium hover:bg-indigo-500"
              >
                Upgrade to Pro
              </button>
            )}
          </div>
          {usage && (
            <div className="space-y-3">
              <Meter label="Documents" used={usage.doc_count} limit={usage.doc_limit} />
              <Meter label="Messages this month" used={usage.msg_count_month} limit={usage.msg_limit} />
            </div>
          )}
        </section>

        {/* Members */}
        <section className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/50 p-5">
          <h2 className="font-medium">Members</h2>
          <ul className="divide-y divide-slate-800">
            {members.map((m) => (
              <li key={m.user_id} className="flex items-center justify-between py-2 text-sm">
                <span className="text-slate-200">{m.email ?? m.user_id.slice(0, 8)}</span>
                <span className="flex items-center gap-3">
                  <span className="rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-400">
                    {m.role}
                  </span>
                  {m.role !== "owner" && (
                    <button
                      onClick={() => removeMember(m.user_id)}
                      className="text-xs text-slate-500 hover:text-red-400"
                    >
                      Remove
                    </button>
                  )}
                </span>
              </li>
            ))}
          </ul>
          <form onSubmit={addMember} className="flex gap-2">
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="teammate@email.com"
              className="flex-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
            />
            <button className="rounded-lg bg-slate-700 px-4 text-sm hover:bg-slate-600">Invite</button>
          </form>
          {msg && <p className="text-sm text-amber-400">{msg}</p>}
        </section>
      </main>
    </div>
  );
}
