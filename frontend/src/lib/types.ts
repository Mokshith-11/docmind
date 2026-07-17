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

export interface Workspace {
  id: string;
  name: string;
  owner_id: string;
  plan: string;
  created_at: string | null;
}
