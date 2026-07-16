-- DocMind — full database schema + RLS (Supabase / Postgres)
-- Run in Supabase SQL Editor. Idempotent-ish: safe to re-run in a fresh project.

-- ── Extensions ─────────────────────────────────────────────────────────────
create extension if not exists vector;
create extension if not exists pg_trgm;

-- ── Helper: is the current user a member of the given workspace? ────────────
-- SECURITY DEFINER so RLS on workspace_members doesn't recurse.
create or replace function public.is_workspace_member(ws uuid)
returns boolean
language sql
security definer
stable
set search_path = public
as $$
  select exists (
    select 1 from public.workspace_members m
    where m.workspace_id = ws and m.user_id = auth.uid()
  );
$$;

-- ── Tables ─────────────────────────────────────────────────────────────────
create table if not exists public.workspaces (
  id         uuid primary key default gen_random_uuid(),
  name       text not null,
  owner_id   uuid not null references auth.users(id) on delete cascade,
  plan       text not null default 'free' check (plan in ('free','pro')),
  created_at timestamptz not null default now()
);

create table if not exists public.workspace_members (
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  user_id      uuid not null references auth.users(id) on delete cascade,
  role         text not null check (role in ('owner','editor','viewer')),
  created_at   timestamptz not null default now(),
  primary key (workspace_id, user_id)
);

create table if not exists public.documents (
  id           uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  filename     text not null,
  storage_path text not null,
  status       text not null default 'processing' check (status in ('processing','ready','failed')),
  page_count   int,
  has_tables   bool not null default false,
  has_images   bool not null default false,
  created_at   timestamptz not null default now()
);

create table if not exists public.chunks (
  id           uuid primary key default gen_random_uuid(),
  document_id  uuid not null references public.documents(id) on delete cascade,
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  content      text not null,
  embedding    vector(768),
  tsv          tsvector,
  page         int,
  chunk_index  int,
  chunk_type   text not null default 'text' check (chunk_type in ('text','table','image_desc')),
  table_json   jsonb
);

create table if not exists public.conversations (
  id           uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  user_id      uuid not null references auth.users(id) on delete cascade,
  title        text,
  created_at   timestamptz not null default now()
);

create table if not exists public.messages (
  id              uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  role            text not null check (role in ('user','assistant')),
  content         text not null,
  citations       jsonb,
  route           text,
  latency_ms      int,
  tokens_in       int,
  tokens_out      int,
  cost_usd        numeric,
  cache_hit       bool not null default false,
  created_at      timestamptz not null default now()
);

create table if not exists public.semantic_cache (
  id              uuid primary key default gen_random_uuid(),
  workspace_id    uuid not null references public.workspaces(id) on delete cascade,
  query           text not null,
  query_embedding vector(768),
  answer          text not null,
  citations       jsonb,
  created_at      timestamptz not null default now()
);

create table if not exists public.eval_runs (
  id               uuid primary key default gen_random_uuid(),
  ran_at           timestamptz not null default now(),
  faithfulness     numeric,
  answer_relevance numeric,
  notes            text
);

-- ── Indexes ────────────────────────────────────────────────────────────────
create index if not exists chunks_embedding_hnsw
  on public.chunks using hnsw (embedding vector_cosine_ops);
create index if not exists chunks_tsv_gin
  on public.chunks using gin (tsv);
create index if not exists chunks_document_id_idx  on public.chunks (document_id);
create index if not exists chunks_workspace_id_idx on public.chunks (workspace_id);
create index if not exists documents_workspace_idx on public.documents (workspace_id);
create index if not exists messages_conversation_idx on public.messages (conversation_id);
create index if not exists semcache_workspace_hnsw
  on public.semantic_cache using hnsw (query_embedding vector_cosine_ops);

-- ── Auto-add workspace owner as an 'owner' member ──────────────────────────
create or replace function public.add_owner_as_member()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.workspace_members (workspace_id, user_id, role)
  values (new.id, new.owner_id, 'owner')
  on conflict do nothing;
  return new;
end;
$$;

drop trigger if exists trg_add_owner_as_member on public.workspaces;
create trigger trg_add_owner_as_member
  after insert on public.workspaces
  for each row execute function public.add_owner_as_member();

-- ── Row Level Security ─────────────────────────────────────────────────────
alter table public.workspaces       enable row level security;
alter table public.workspace_members enable row level security;
alter table public.documents        enable row level security;
alter table public.chunks           enable row level security;
alter table public.conversations    enable row level security;
alter table public.messages         enable row level security;
alter table public.semantic_cache   enable row level security;
alter table public.eval_runs        enable row level security;

-- workspaces: members can read; any authenticated user can create (must own it);
-- only owner can update/delete.
drop policy if exists workspaces_select on public.workspaces;
create policy workspaces_select on public.workspaces
  for select using (public.is_workspace_member(id));

drop policy if exists workspaces_insert on public.workspaces;
create policy workspaces_insert on public.workspaces
  for insert with check (owner_id = auth.uid());

drop policy if exists workspaces_update on public.workspaces;
create policy workspaces_update on public.workspaces
  for update using (owner_id = auth.uid());

drop policy if exists workspaces_delete on public.workspaces;
create policy workspaces_delete on public.workspaces
  for delete using (owner_id = auth.uid());

-- workspace_members: members of the workspace can read the membership list.
drop policy if exists members_select on public.workspace_members;
create policy members_select on public.workspace_members
  for select using (public.is_workspace_member(workspace_id));

-- (Insert/update/delete of members handled server-side via service key in Phase 5.)

-- documents / chunks / conversations / messages / semantic_cache:
-- full access scoped to workspace membership.
drop policy if exists documents_all on public.documents;
create policy documents_all on public.documents
  for all using (public.is_workspace_member(workspace_id))
  with check (public.is_workspace_member(workspace_id));

drop policy if exists chunks_all on public.chunks;
create policy chunks_all on public.chunks
  for all using (public.is_workspace_member(workspace_id))
  with check (public.is_workspace_member(workspace_id));

drop policy if exists conversations_all on public.conversations;
create policy conversations_all on public.conversations
  for all using (public.is_workspace_member(workspace_id))
  with check (public.is_workspace_member(workspace_id));

-- messages: scoped via their conversation's workspace.
drop policy if exists messages_all on public.messages;
create policy messages_all on public.messages
  for all using (
    exists (
      select 1 from public.conversations c
      where c.id = conversation_id and public.is_workspace_member(c.workspace_id)
    )
  )
  with check (
    exists (
      select 1 from public.conversations c
      where c.id = conversation_id and public.is_workspace_member(c.workspace_id)
    )
  );

drop policy if exists semcache_all on public.semantic_cache;
create policy semcache_all on public.semantic_cache
  for all using (public.is_workspace_member(workspace_id))
  with check (public.is_workspace_member(workspace_id));

-- eval_runs: global, read-only to authenticated users (writes via service key).
drop policy if exists eval_runs_select on public.eval_runs;
create policy eval_runs_select on public.eval_runs
  for select using (auth.role() = 'authenticated');
