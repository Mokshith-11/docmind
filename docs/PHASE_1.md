# Phase 1 — Skeleton: run it end-to-end

Goal: FastAPI (with Supabase JWT auth) + React (with Supabase auth) running
locally, one protected round-trip (`/api/me`) working, schema applied.

## 0. Prereqs
- Python 3.11 + [uv](https://docs.astral.sh/uv/)
- Node 18+
- A Supabase project (you have `docmind`)

## 1. Apply the database schema
Supabase → **SQL Editor** → paste all of `infra/schema.sql` → **Run**.
Then Authentication → Providers → make sure **Email** is enabled (it is by default).

## 2. Fill secrets
Root `.env` (backend) — from Supabase → Project Settings:
```
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_SERVICE_KEY=<service_role key — "Legacy anon, service_role API keys" tab>
SUPABASE_JWT_SECRET=<Project Settings → JWT Keys → JWT secret (legacy)>
```
`frontend/.env` — copy from `frontend/.env.example`:
```
VITE_SUPABASE_URL=https://<ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<publishable / anon key>
VITE_API_URL=http://localhost:8000
```

## 3. Backend
```bash
cd backend
uv sync
uv run pytest                 # health tests should pass
uv run uvicorn app.main:app --reload --port 8000
```
Check: http://localhost:8000/api/health → `{"status":"ok"}`, and http://localhost:8000/docs

## 4. Frontend
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 → **Get started** → sign up with an email+password →
you land on `/app`, which calls `GET /api/me` with your Supabase JWT and shows
your user id/email from the backend. That green JSON block = Phase 1 done.

## 5. Deploy (hello-world)
- **Backend → Railway:** new project from the `docmind` repo, root = `backend/`,
  add the same env vars, deploy. Uses `railway.json` / `Procfile`.
- **Frontend → Vercel:** import repo, root = `frontend/`, add the `VITE_*` env
  vars (set `VITE_API_URL` to the Railway URL), deploy. Uses `vercel.json`.

## Phase 1 exit checklist
- [ ] `infra/schema.sql` applied, RLS enabled on all tables
- [ ] `uv run pytest` green
- [ ] Sign up / sign in works
- [ ] `/app` shows the `/api/me` payload from the backend (auth verified end-to-end)
- [ ] Backend on Railway + frontend on Vercel reachable
