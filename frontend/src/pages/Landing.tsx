import { Link } from "react-router-dom";

export default function Landing() {
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center gap-6 px-6">
      <h1 className="text-5xl font-bold tracking-tight">DocMind</h1>
      <p className="text-lg text-slate-400 max-w-xl text-center">
        Upload your documents and chat with them. Agentic retrieval, inline citations,
        team workspaces.
      </p>
      <Link
        to="/login"
        className="rounded-lg bg-indigo-500 px-6 py-3 font-medium text-white hover:bg-indigo-400 transition"
      >
        Get started
      </Link>
    </div>
  );
}
