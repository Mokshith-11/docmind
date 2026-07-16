import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/api";
import { supabase } from "../lib/supabase";
import { useAuth } from "../hooks/useAuth";

type Me = { id: string; email: string | null };

export default function Dashboard() {
  const { user } = useAuth();
  const nav = useNavigate();
  const [me, setMe] = useState<Me | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api<Me>("/api/me")
      .then(setMe)
      .catch((e) => setError(String(e)));
  }, []);

  async function signOut() {
    await supabase.auth.signOut();
    nav("/");
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-8 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">DocMind</h1>
        <button onClick={signOut} className="text-sm text-slate-400 hover:text-slate-200">
          Sign out
        </button>
      </div>
      <p className="text-slate-400">Signed in as {user?.email}</p>

      <div className="rounded-lg border border-slate-800 bg-slate-900 p-4">
        <p className="text-sm text-slate-500 mb-2">Backend /api/me response:</p>
        {error ? (
          <pre className="text-red-400 text-sm">{error}</pre>
        ) : (
          <pre className="text-emerald-400 text-sm">{JSON.stringify(me, null, 2)}</pre>
        )}
      </div>
    </div>
  );
}
