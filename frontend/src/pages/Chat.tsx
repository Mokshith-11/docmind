import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Composer from "../components/chat/Composer";
import MessageList from "../components/chat/MessageList";
import { api, sse } from "../lib/api";
import type { ChatMessage, Citation, Workspace } from "../lib/types";

export default function Chat() {
  const [workspace, setWorkspace] = useState<Workspace | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Workspace[]>("/api/workspaces")
      .then((ws) => setWorkspace(ws[0] ?? null))
      .catch((e) => setError(String(e)));
  }, []);

  async function ask(question: string) {
    if (!workspace) return;
    setError(null);
    setBusy(true);
    setMessages((m) => [...m, { role: "user", content: question }, { role: "assistant", content: "" }]);

    try {
      for await (const { event, data } of sse("/api/chat", {
        workspace_id: workspace.id,
        message: question,
        conversation_id: conversationId,
      })) {
        if (event === "meta") {
          setConversationId(data.conversation_id as string);
        } else if (event === "sources") {
          const citations = data.citations as Citation[];
          setMessages((m) => {
            const next = [...m];
            next[next.length - 1] = { ...next[next.length - 1], citations };
            return next;
          });
        } else if (event === "token") {
          const text = data.text as string;
          setMessages((m) => {
            const next = [...m];
            const last = next[next.length - 1];
            next[next.length - 1] = { ...last, content: last.content + text };
            return next;
          });
        } else if (event === "done") {
          setMessages((m) => {
            const next = [...m];
            next[next.length - 1] = {
              ...next[next.length - 1],
              latency_ms: data.latency_ms as number,
              route: data.route as string,
            };
            return next;
          });
        } else if (event === "error") {
          setError(String(data.detail));
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-950 text-slate-100">
      <header className="flex items-center justify-between border-b border-slate-800 px-8 py-4">
        <div>
          <h1 className="text-xl font-semibold">DocMind</h1>
          <p className="text-xs text-slate-500">{workspace?.name ?? "Loading…"}</p>
        </div>
        <Link to="/app" className="text-sm text-slate-400 hover:text-slate-200">
          Documents
        </Link>
      </header>

      <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col gap-4 p-8">
        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
            {error}
          </div>
        )}
        <div className="flex-1">
          <MessageList messages={messages} />
        </div>
        <Composer onSend={ask} disabled={busy || !workspace} />
      </main>
    </div>
  );
}
