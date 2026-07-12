# DocMind

A document Q&A / RAG application.

## Stack
- **Supabase** — Postgres, auth (JWT), storage
- **Gemini** — LLM
- **Groq** — fast LLM inference
- **Cohere** — embeddings + rerank

## Setup
1. Clone the repo.
2. Copy the env template and fill in your keys:
   ```bash
   cp .env.example .env
   ```
3. Get the keys (all have free tiers):
   - **Supabase** → create a project, then Project Settings → API for
     `SUPABASE_URL` / `SUPABASE_SERVICE_KEY`, and API → JWT Settings for
     `SUPABASE_JWT_SECRET`.
   - **Gemini** → https://aistudio.google.com
   - **Groq** → https://console.groq.com
   - **Cohere** → https://dashboard.cohere.com
   - **Lemon Squeezy** (billing, Phase 5+) → API key, webhook secret, variant ID.

> `.env` is gitignored — never commit real keys. See `.env.example` for the full
> list of required variables.
