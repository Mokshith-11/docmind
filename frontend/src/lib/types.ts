export type DocStatus = "processing" | "ready" | "failed";

export interface DocumentOut {
  id: string;
  workspace_id: string;
  filename: string;
  storage_path: string;
  status: DocStatus;
  page_count: number | null;
  has_tables: boolean;
  has_images: boolean;
  created_at: string | null;
}

export interface Citation {
  n: number;
  document_id: string;
  filename: string;
  page: number | null;
  chunk_type: string;
  excerpt: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  latency_ms?: number;
  route?: string;
}

export interface Workspace {
  id: string;
  name: string;
  owner_id: string;
  plan: string;
  created_at: string | null;
}
