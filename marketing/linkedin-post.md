# DocMind — LinkedIn launch post (Phase 1)

Build-in-public announcement. Angle: **problem-first / vision**.

## Assets in this folder

| File | Use |
|---|---|
| `DocMind-LinkedIn-Carousel.pdf` | Upload to LinkedIn as a **document** post → renders as a native swipeable carousel. 6 pages, 4:5 (1080×1350). |
| `linkedin-carousel.html` | Editable source. Open in Chrome → `Ctrl+P` → Save as PDF to regenerate. |
| `slides/*.png` | Individual slides at 1080×1350. `01-hero-cover.png` doubles as the standalone hero image. |

## How to post

1. LinkedIn → **Start a post** → click the **document icon** (not the image icon)
2. Upload `DocMind-LinkedIn-Carousel.pdf`
3. Title it: **The answer is already written down.**
4. Paste the caption below
5. Post

## Caption

> Every answer you need is already written down.
>
> It's just buried on page 147 of a contract nobody has time to read.
>
> That's the thing that's been bugging me. We digitized everything — contracts, research, reports, manuals — and then handed people Ctrl+F. But search matches strings, not meaning. So we skim. We miss the clause that mattered. We re-ask questions someone already answered on page 30.
>
> So I'm building DocMind: upload a document, ask in plain English, get an answer with the exact source cited.
>
> The "cited" part is the whole point. An AI that confidently invents something about your contract is worse than no AI at all. Every claim traces back to a page you can check.
>
> Under the hood it's not one-size-fits-all RAG — an agent routes each question to the right strategy: simple retrieval, multi-hop reasoning, or table Q&A. Slide 4 has the architecture.
>
> Phase 1 shipped this week: auth, database, backend, frontend — tested end-to-end.
>
> One honest bug for the builders: login only worked after I switched token verification from HS256 to ES256/JWKS. Building in public means showing the messy parts too.
>
> Next up: the ingestion pipeline — parse, chunk, embed.
>
> Follow if you want to watch an AI product go from zero to real — wins and bugs included.
>
> #buildinpublic #AI #RAG #softwareengineering

## Slide arc

1. **Hero** — "The answer is already written down." (doubles as the standalone post image)
2. **Problem** — Ctrl+F finds words, not answers
3. **Vision** — chat mock with `[1] [2]` inline citations
4. **Architecture** — the agentic RAG flow (credibility slide)
5. **Shipped** — Phase 1 checklist + the honest ES256 bug
6. **CTA** — follow the build

## Design notes

Visual identity is built on a **citation-bracket motif** (`[ 02 / 06 ]`, `[1]`, mono labels) — citations *are* the product. Serif display (Georgia) against a mono utility face (Consolas), indigo for the system, mint for the cited answer. Committed single dark theme: it's a fixed social asset, not a themeable UI.

All non-ASCII punctuation is written as HTML entities so the slides render correctly regardless of how the file is served.
