-- Phase 2 — make chunks.tsv compute itself.
--
-- The initial schema declared `tsv tsvector` as a plain column, which would mean
-- the app has to build the tsvector and keep it in sync. A generated column lets
-- Postgres own it: it's always correct, and inserts only need `content`.
-- Phase 3's hybrid retrieval reads this column for sparse (BM25-substitute) search.

drop index if exists chunks_tsv_gin;
alter table public.chunks drop column if exists tsv;

alter table public.chunks
  add column tsv tsvector
  generated always as (to_tsvector('english', content)) stored;

create index chunks_tsv_gin on public.chunks using gin (tsv);
