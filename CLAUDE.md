# DocMind — Agentic Document Intelligence Platform

## What this is
A production-grade SaaS: users upload documents (PDF/DOCX, including scanned files and files with tables/charts), then chat with them. Queries are routed by an agent to the right strategy (simple retrieval, multi-hop reasoning, or table-QA). Answers stream with inline citations. Includes team workspaces, billing, semantic caching, and a built-in eval/observability dashboard.

## Tech stack (do not substitute)
- **Backend:** FastAPI, Python 3.11, uv for dependency management
- **Frontend:** React 18 + Vite + TypeScript + Tailwind CSS
- **Database/Auth/Storage:** Supabase (Postgres + pgvector + Auth + Storage buckets)
- **LLMs:** Google Gemini 2.0 Flash (generation + vision), Groq Llama-3.3-70B (router + fast paths)
- **Embeddings:** Gemini text-embedding-004 (768 dims)
- **Reranking:** Cohere Rerank v3 (free tier)
- **Sparse retrieval:** Postgres full-text search (tsvector) as BM25 substitute
- **Payments:** Lemon Squeezy (checkout overlay + webhooks)
- **Deploy:** Railway (backend), Vercel (frontend)

## Repository structure
```
docmind/
├── CLAUDE.md
├── backend/
│   ├── pyproject.toml
│   ├── app/
│   │   ├── main.py                 # FastAPI app, CORS, routers
│   │   ├── config.py               # pydantic-settings, all env vars
│   │   ├── deps.py                 # auth dependency (Supabase JWT verify)
│   │   ├── routers/
│   │   │   ├── documents.py        # upload, list, delete, status
│   │   │   ├── chat.py             # POST /chat (SSE streaming)
│   │   │   ├── workspaces.py       # CRUD + member management
│   │   │   ├── billing.py          # checkout link + LS webhook
│   │   │   └── metrics.py          # observability dashboard data
│   │   ├── ingestion/
│   │   │   ├── parser.py           # PyMuPDF text, python-docx, table extraction
│   │   │   ├── ocr.py              # pytesseract fallback for scanned pages
│   │   │   ├── vision.py           # Gemini vision: describe images/charts
│   │   │   ├── chunker.py          # semantic chunking, 500 tok / 50 overlap
│   │   │   └── indexer.py          # embed + upsert to pgvector + tsvector
│   │   ├── retrieval/
│   │   │   ├── hybrid.py           # dense + sparse search, RRF fusion
│   │   │   ├── rerank.py           # Cohere rerank top-20 → top-5
│   │   │   └── cache.py            # semantic cache (cosine > 0.95 → hit)
│   │   ├── agents/
│   │   │   ├── router.py           # classify query: simple | multihop | table
│   │   │   ├── multihop.py         # decompose → retrieve per sub-q → synthesize
│   │   │   └── table_qa.py         # answer over extracted table JSON
│   │   ├── evals/
│   │   │   ├── golden_set.json     # 25 Q/A pairs over sample docs
│   │   │   └── run_evals.py        # RAGAS: faithfulness, answer relevance
│   │   └── models.py               # pydantic schemas
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── pages/                  # Landing, Login, Workspace, Chat, Dashboard, Billing
│   │   ├── components/
│   │   │   ├── chat/               # MessageList, Composer, CitationPanel
│   │   │   ├── upload/             # Dropzone, IngestStatusList
│   │   │   └── metrics/            # CostChart, LatencyChart, EvalScores
│   │   ├── lib/supabase.ts
│   │   ├── lib/api.ts              # typed fetch wrapper + SSE reader
│   │   └── hooks/
│   └── ...
└── infra/
    └── schema.sql                  # full DB schema + RLS policies
```

## Database schema (Supabase / Postgres)
```sql
-- extensions: vector, pg_trgm
workspaces(id uuid pk, name text, owner_id uuid, plan text default 'free', created_at)
workspace_members(workspace_id fk, user_id uuid, role text check in ('owner','editor','viewer'))
documents(id uuid pk, workspace_id fk, filename text, storage_path text,
          status text check in ('processing','ready','failed'), page_count int,
          has_tables bool, has_images bool, created_at)
chunks(id uuid pk, document_id fk, workspace_id fk, content text,
       embedding vector(768), tsv tsvector, page int, chunk_index int,
       chunk_type text check in ('text','table','image_desc'),
       table_json jsonb null)
conversations(id uuid pk, workspace_id fk, user_id uuid, title text, created_at)
messages(id uuid pk, conversation_id fk, role text, content text,
         citations jsonb, route text, latency_ms int, tokens_in int,
         tokens_out int, cost_usd numeric, cache_hit bool, created_at)
semantic_cache(id uuid pk, workspace_id fk, query text, query_embedding vector(768),
               answer text, citations jsonb, created_at)
eval_runs(id uuid pk, ran_at timestamptz, faithfulness numeric,
          answer_relevance numeric, notes text)
```
- Enable RLS on every table; policy = user must be a member of the row's workspace.
- Indexes: HNSW on chunks.embedding, GIN on chunks.tsv, ivfflat NOT used.

## Core flows

### Ingestion (async via FastAPI BackgroundTasks)
1. Upload → Supabase Storage → documents row status='processing'
2. Parse per page: text via PyMuPDF; if page text < 50 chars → OCR fallback
3. Tables → extract with pdfplumber → store as chunk_type='table' with table_json
4. Images/charts → Gemini Vision one-line + detailed description → chunk_type='image_desc'
5. Chunk text semantically (500 tokens, 50 overlap, respect headings)
6. Embed batch → upsert chunks with embedding + tsv → status='ready'

### Query (POST /chat, SSE stream)
1. Check semantic cache (embed query, cosine > 0.95 within workspace) → if hit, stream cached answer, mark cache_hit
2. Router (Groq, JSON mode): {"route": "simple" | "multihop" | "table"}
3. simple: hybrid search (top-20 dense + top-20 sparse → RRF) → Cohere rerank → top-5
   multihop: decompose into 2-4 sub-queries → retrieve per sub-query → dedupe → rerank
   table: retrieve table chunks → answer over table_json with Gemini
4. Generate with Gemini, stream tokens via SSE. Prompt requires citations as [n] markers mapped to chunk ids.
5. Persist message with route, latency, tokens, cost, citations.

### Billing
- Free: 3 documents per workspace, 50 messages/month. Pro: unlimited.
- Lemon Squeezy hosted checkout; webhook `subscription_created`/`expired` updates workspaces.plan. Verify webhook signature.

### Observability dashboard (frontend /dashboard)
- Cards: total queries, avg latency, total cost, cache hit rate
- Charts (recharts): cost/day, latency p50/p95, route distribution
- Eval section: latest RAGAS run scores + history

## API contract (summary)
```
POST   /api/documents            multipart upload → {id, status}
GET    /api/documents?workspace= → list with status
DELETE /api/documents/{id}
POST   /api/chat                 {workspace_id, conversation_id?, message} → SSE
GET    /api/conversations?workspace=
GET    /api/metrics?workspace=   → dashboard payload
POST   /api/billing/checkout     → {url}
POST   /api/billing/webhook      (Lemon Squeezy)
```

## Build phases (do them in order, each phase must run end-to-end before the next)
1. **Phase 1 — Skeleton:** repo scaffold, Supabase schema + RLS, FastAPI with auth dep, React app with Supabase auth, deploy hello-world to Railway/Vercel.
2. **Phase 2 — Ingestion:** upload → parse → chunk → embed → indexed. UI: dropzone + status list.
3. **Phase 3 — Simple RAG:** hybrid retrieval + rerank + streaming chat with citations. UI: chat page + citation panel.
4. **Phase 4 — Agents:** router, multihop, table-QA, vision ingestion, OCR fallback.
5. **Phase 5 — Product:** workspaces/members, semantic cache, billing + limits.
6. **Phase 6 — Eval + observability:** golden set, RAGAS runner, metrics dashboard.
7. **Phase 7 — Polish:** landing page, error states, rate limiting (slowapi), README + architecture diagram.

## Conventions
- Type everything: pydantic v2 models backend, no `any` in TS.
- All secrets via env vars; never commit keys. `.env.example` maintained.
- Every router function ≤ 40 lines; business logic lives in modules, not routers.
- Errors: structured JSON {error, detail}; frontend shows toast.
- Write tests for chunker, RRF fusion, and router classification (pytest).
- Commit per feature with conventional commits (feat:, fix:).

## Environment variables
```
SUPABASE_URL, SUPABASE_SERVICE_KEY, SUPABASE_JWT_SECRET
GEMINI_API_KEY, GROQ_API_KEY, COHERE_API_KEY
LEMONSQUEEZY_API_KEY, LEMONSQUEEZY_WEBHOOK_SECRET, LEMONSQUEEZY_VARIANT_ID
FRONTEND_URL
```
