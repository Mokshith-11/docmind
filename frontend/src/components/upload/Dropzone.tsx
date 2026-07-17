import { useRef, useState } from "react";
import { apiUpload } from "../../lib/api";

const ACCEPT = ".pdf,.docx";

export default function Dropzone({
  workspaceId,
  onUploaded,
}: {
  workspaceId: string;
  onUploaded: () => void;
}) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function send(files: FileList | null) {
    if (!files?.length) return;
    setError(null);
    setBusy(true);
    try {
      for (const file of Array.from(files)) {
        const form = new FormData();
        form.append("workspace_id", workspaceId);
        form.append("file", file);
        await apiUpload("/api/documents", form);
      }
      onUploaded();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <div className="space-y-2">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setOver(false);
          send(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition ${
          over ? "border-indigo-400 bg-indigo-500/10" : "border-slate-700 hover:border-slate-500"
        } ${busy ? "opacity-60 pointer-events-none" : ""}`}
      >
        <p className="text-slate-200 font-medium">
          {busy ? "Uploading…" : "Drop a PDF or DOCX here"}
        </p>
        <p className="text-sm text-slate-500 mt-1">or click to choose a file · max 25 MB</p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          multiple
          hidden
          onChange={(e) => send(e.target.files)}
        />
      </div>
      {error && <p className="text-sm text-red-400">{error}</p>}
    </div>
  );
}
