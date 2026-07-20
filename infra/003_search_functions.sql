-- Phase 3 — retrieval functions.
--
-- PostgREST can't express vector math or full-text ranking over plain REST, so
-- hybrid search lives in SQL functions the API calls via /rest/v1/rpc/<name>.
--
-- SECURITY INVOKER (the default): these run with the caller's privileges, so RLS
-- on `chunks` still applies. The backend calls them with the service key and
-- enforces workspace membership itself (services/supa.is_member).

-- ── Dense: cosine similarity over pgvector (uses the HNSW index) ────────────
create or replace function public.match_chunks(
  query_embedding vector(768),
  ws uuid,
  match_count int default 20
)
returns table (
  id uuid,
  document_id uuid,
  content text,
  page int,
  chunk_type text,
  similarity float
)
language sql
stable
as $$
  select c.id, c.document_id, c.content, c.page, c.chunk_type,
         1 - (c.embedding <=> query_embedding) as similarity
  from public.chunks c
  where c.workspace_id = ws
    and c.embedding is not null
  order by c.embedding <=> query_embedding   -- <=> is cosine distance
  limit match_count;
$$;

-- ── Sparse: Postgres full-text ranking (uses the GIN index on tsv) ──────────
-- websearch_to_tsquery handles natural input ("setup cost", quoted phrases, OR)
-- without throwing on punctuation the way to_tsquery does.
create or replace function public.search_chunks(
  query_text text,
  ws uuid,
  match_count int default 20
)
returns table (
  id uuid,
  document_id uuid,
  content text,
  page int,
  chunk_type text,
  rank float
)
language sql
stable
as $$
  select c.id, c.document_id, c.content, c.page, c.chunk_type,
         ts_rank(c.tsv, websearch_to_tsquery('english', query_text)) as rank
  from public.chunks c
  where c.workspace_id = ws
    and c.tsv @@ websearch_to_tsquery('english', query_text)
  order by rank desc
  limit match_count;
$$;
