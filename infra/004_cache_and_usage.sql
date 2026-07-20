-- Phase 5 — semantic cache lookup + usage counters.

-- Semantic cache: nearest cached query within a workspace above a similarity
-- threshold. Phase 5 chat checks this before doing any retrieval/generation.
create or replace function public.match_cache(
  query_embedding vector(768),
  ws uuid,
  threshold float default 0.95,
  match_count int default 1
)
returns table (id uuid, query text, answer text, citations jsonb, similarity float)
language sql
stable
as $$
  select c.id, c.query, c.answer, c.citations,
         1 - (c.query_embedding <=> query_embedding) as similarity
  from public.semantic_cache c
  where c.workspace_id = ws
    and c.query_embedding is not null
    and 1 - (c.query_embedding <=> query_embedding) >= threshold
  order by c.query_embedding <=> query_embedding
  limit match_count;
$$;

-- Usage for plan-limit enforcement: total documents + this month's user messages.
create or replace function public.workspace_usage(ws uuid)
returns table (doc_count int, msg_count_month int)
language sql
stable
as $$
  select
    (select count(*)::int from public.documents d where d.workspace_id = ws) as doc_count,
    (select count(*)::int
       from public.messages m
       join public.conversations cv on cv.id = m.conversation_id
      where cv.workspace_id = ws
        and m.role = 'user'
        and m.created_at >= date_trunc('month', now())) as msg_count_month;
$$;
