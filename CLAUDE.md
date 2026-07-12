# DocMind — CLAUDE.md (placeholder)

> ⚠️ **Placeholder.** Replace this entire file with the CLAUDE.md you intended to
> drop in the root. This stub only records the project's known shape so the repo
> isn't empty; it is not the real project spec.

## What this is
DocMind — a document Q&A / RAG application.

## Stack (from setup)
- **Supabase** — database + auth (uses `SUPABASE_JWT_SECRET`) and storage
- **Gemini** — LLM (aistudio.google.com)
- **Groq** — fast LLM inference (console.groq.com)
- **Cohere** — embeddings + rerank (dashboard.cohere.com)

## Environment variables
Declared in `.env.example`; real values live in `.env` (gitignored):

| Variable | Source |
|---|---|
| `SUPABASE_URL` | Supabase → Project Settings → API |
| `SUPABASE_ANON_KEY` | Supabase → Project Settings → API |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase → Project Settings → API |
| `SUPABASE_JWT_SECRET` | Supabase → Project Settings → API → JWT Settings |
| `GEMINI_API_KEY` | aistudio.google.com |
| `GROQ_API_KEY` | console.groq.com |
| `COHERE_API_KEY` | dashboard.cohere.com |

## Setup
1. `cp .env.example .env`
2. Fill in every value in `.env`.
