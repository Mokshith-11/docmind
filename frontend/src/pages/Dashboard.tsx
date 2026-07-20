import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import Dropzone from "../components/upload/Dropzone";
import IngestStatusList from "../components/upload/IngestStatusList";
import { useAuth } from "../hooks/useAuth";
import { api } from "../lib/api";
import { supabase } from "../lib/supabase";
import type { DocumentOut, Workspace } from "../lib/types";

const POLL_MS = 2000;

export default function Dashboard() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [docs, setDocs] = useState<DocumentOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<number | null>(null);

  const loadDocs = useCallback(async (wsId: string) => {
    try {
      setDocs(await api<DocumentOut[]>(`/api/documents?workspace=${wsId}`));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    api<Workspace[]>("/api/workspaces")
      .then((ws) => {
        const first = ws[0] ?? null;
        setWorkspace(first);
        if (first) loadDocs(first.id);
      })
      .catch((e) => setError(String(e)));
  }, [loadDocs]);

  // Poll only while something is still being ingested.
  useEffect(() => {
    const pending = docs.some((d) => d.status === "processing");
    if (!workspace || !pending) return;
    timer.current = window.setTimeout(() => loadDocs(workspace.id), POLL_MS);
    return () => {
      if (timer.current) window.clearTimeout(timer.current);
    };
  }, [docs, workspace, loadDocs]);

  async function signOut() {
    await supabase.auth.signOut();
    nav("/");
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <header className="flex items-center justify-between border-b border-slate-800 px-8 py-4">
        <div>
          <h1 className="text-xl font-semibold">DocMind</h1>
          <p className="text-xs text-slate-500">
            {workspace ? workspace.name : "Loading workspace…"} · {user?.email}
          </p>
        </div>
        <div className="flex items-center gap-5">
          <Link
            to="/chat"
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500"
          >
            Ask your documents
          </Link>
          <Link to="/metrics" className="text-sm text-slate-400 hover:text-slate-200">
            Metrics
          </Link>
          <Link to="/settings" className="text-sm text-slate-400 hover:text-slate-200">
            Settings
          </Link>
          <button onClick={signOut} className="text-sm text-slate-400 hover:text-slate-200">
            Sign out
          </button>
        </div>
      </header>

      <main className="mx-auto max-w-3xl space-y-8 p-8">
        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
            {error}
          </div>
        )}

        <section className="space-y-3">
          <h2 className="text-sm font-medium uppercase tracking-wide text-slate-400">
            Upload a document
          </h2>
          {workspace && (
            <Dropzone workspaceId={workspace.id} onUploaded={() => loadDocs(workspace.id)} />
          )}
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-medium uppercase tracking-wide text-slate-400">
            Your documents
          </h2>
          <IngestStatusList
            docs={docs}
            onChanged={() => workspace && loadDocs(workspace.id)}
          />
        </section>
      </main>
    </div>
  );
}
