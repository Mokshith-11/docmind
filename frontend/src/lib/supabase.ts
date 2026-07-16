import { createClient } from "@supabase/supabase-js";

const url = import.meta.env.VITE_SUPABASE_URL;
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!url || !anonKey) {
  // Surfaced early so a missing frontend/.env is obvious in dev.
  console.warn("Missing VITE_SUPABASE_URL or VITE_SUPABASE_ANON_KEY — copy frontend/.env.example to frontend/.env");
}

export const supabase = createClient(url ?? "", anonKey ?? "");
