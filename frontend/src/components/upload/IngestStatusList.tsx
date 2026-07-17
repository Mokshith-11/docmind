import { api } from "../../lib/api";
import type { DocumentOut } from "../../lib/types";

const STATUS: Record<string, { label: string; cls: string }> = {
  processing: { label: "Processing", cls: "bg-amber-500/15 text-amber-300 border-amber-500/30" },
  ready: { label: "Ready", cls: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" },
  failed: { label: "Failed", cls: "bg-red-500/15 text-red-300 border-red-500/30" },
};

export default function IngestStatusList({
  docs,
  onChanged,
}: {
  docs: DocumentOut[];
  onChanged: () => void;
}) {
  async function remove(id: string) {
    await api(`/api/documents/${id}`, { method: "DELETE" }).catch(() => {});
    onChanged();
  }

  if (!docs.length) {
    return <p className="text-slate-500 text-sm">No documents yet. Upload one to get started.</p>;
  }

  return (
    <ul className="divide-y divide-slate-800 rounded-xl border border-slate-800 overflow-hidden">
      {docs.map((d) => {
        const s = STATUS[d.status] ?? STATUS.processing;
        return (
          <li key={d.id} className="flex items-center gap-4 bg-slate-900/60 px-4 py-3">
            <div className="min-w-0 flex-1">
              <p className="truncate text-slate-100">{d.filename}</p>
              <p className="text-xs text-slate-500">
                {d.status === "ready"
                  ? `${d.page_count ?? "?"} pages${d.has_tables ? " · tables extracted" : ""}`
                  : d.status === "failed"
                    ? "Could not be processed"
                    : "Parsing, chunking, embedding…"}
              </p>
            </div>
            <span className={`rounded-full border px-2.5 py-0.5 text-xs ${s.cls}`}>
              {d.status === "processing" && (
                <span className="mr-1.5 inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-amber-300 align-middle" />
              )}
              {s.label}
            </span>
            <button
              onClick={() => remove(d.id)}
              className="text-xs text-slate-500 hover:text-red-400"
              aria-label={`Delete ${d.filename}`}
            >
              Delete
            </button>
          </li>
        );
      })}
    </ul>
  );
}
