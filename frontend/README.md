# Boussole frontend (Phase 8)

Next.js 15 (App Router) · React 19 · Tailwind CSS 4 · Inter Tight · Framer Motion.

The UI mirrors the Ceres Broker website conventions: dark, Apple-inspired,
typographic, no chrome. Every visible string is in `src/content.json` under
`fr` / `en`; FR is primary.

## Run

The backend must be reachable. Two paths:

```bash
# 1. Backend with in-memory store (no Postgres needed)
cd ..
make dev-backend-fake

# 2. Frontend (proxies /api/* to http://localhost:8000 by default)
cd frontend
npm install
npm run dev
```

Override the API origin with `BOUSSOLE_API_ORIGIN=https://...` before
`next dev` / `next build`.

## Surface

- `/` — intake form + report view in the same scroll. Once the agent
  returns, the report fades in and the page scrolls to it.
- The report panel includes the classification, obligations (with citation
  chips linking to EUR-Lex), gap analysis, drafted documents, the
  glass-box trace timeline, and the retrieved passages.

## Glass-box trace

The trace panel calls `GET /trace/{run_id}` and renders the OTel-equivalent
event stream emitted by the agent: every node start/end, every tool call,
every grounding check, with latency and (where applicable) token counts.
Each event is expandable to show its `attributes` payload verbatim.

## Layout

```
frontend/
├── src/
│   ├── content.json          # single source of truth for copy
│   ├── app/
│   │   ├── layout.tsx        # Inter Tight font, LanguageProvider
│   │   ├── page.tsx          # intake + report composition
│   │   └── globals.css       # Tailwind v4 tokens + utilities
│   ├── lib/
│   │   ├── language.tsx      # FR-primary i18n hook (mirrors the website)
│   │   ├── api.ts            # /api/assess + /api/trace client
│   │   ├── types.ts          # AssessmentReport / TraceEvent shapes
│   │   └── utils.ts          # cn()
│   ├── components/
│   │   ├── ui/               # button, card, textarea, select, badge, label
│   │   ├── citation-chip.tsx
│   │   ├── tier-pill.tsx
│   │   ├── language-switcher.tsx
│   │   └── animate-in-view.tsx
│   └── sections/
│       ├── nav.tsx
│       ├── hero.tsx
│       ├── intake.tsx
│       ├── report.tsx        # composes the six report subsections
│       ├── report-header.tsx
│       ├── classification-card.tsx
│       ├── obligations-list.tsx
│       ├── gaps-list.tsx
│       ├── drafted-docs-list.tsx
│       ├── retrieved-passages.tsx
│       ├── trace-panel.tsx
│       ├── clarifications.tsx
│       └── failures.tsx
└── next.config.ts             # /api/* -> BOUSSOLE_API_ORIGIN rewrites
```
