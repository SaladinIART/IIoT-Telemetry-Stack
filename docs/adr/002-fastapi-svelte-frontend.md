# ADR-002 — FastAPI + Svelte for the API and Frontend

**Date:** 2026-04-07
**Status:** Accepted

---

## Context

NEXUS needs a user-facing layer that:
- Exposes factory data via a REST API (for integrations with ERP, MES, Power BI)
- Serves a browser dashboard with real-time updates (no page refresh required)
- Runs self-contained on the factory server — no cloud services, no Node.js microservices, no separate reverse proxy for basic use

The key constraint is that the entire platform must deploy with `docker compose up`. The API and frontend must be served from a single container.

---

## Decision

We use **FastAPI** (Python 3.13) for the REST/SSE API, and **Svelte 5** (compiled vanilla JS) for the frontend. FastAPI mounts the compiled Svelte build at `/`, so a single container serves both.

---

## Reasons

**FastAPI:**
- Auto-generates OpenAPI documentation (Swagger UI at `/docs`) with zero extra work. Every endpoint is self-documenting based on Pydantic schemas.
- Native async support with `asyncio` — fits naturally with SSE (Server-Sent Events) for real-time push.
- Already uses Python, matching the rest of the backend stack. No additional language expertise required.
- `psycopg` async driver integrates cleanly with connection pooling (`psycopg_pool`).
- API key authentication is trivial to implement as a dependency injected via `Depends()`.

**Svelte 5:**
- Compiles to vanilla JavaScript — no virtual DOM, no runtime framework overhead. Bundle size is approximately 5× smaller than a comparable React application. This matters on factory networks with limited bandwidth or slow browsers on industrial PCs.
- Svelte stores integrate naturally with SSE via `EventSource` — sensor state updates the store, the component re-renders automatically with zero boilerplate.
- `SvelteKit` routing is file-system based, which maps cleanly to the page structure: `/`, `/assets`, `/alerts`, `/kpis`, `/admin`.
- Less boilerplate than React or Vue for this use case (read-mostly dashboard, reactive to server push).

**Single-container serve pattern:**
- `vite build` outputs compiled JS/CSS/HTML to `services/api/static/`.
- FastAPI mounts `static/` at `/` with `StaticFiles`.
- In development, `vite dev` proxies `/api` to `localhost:8000` — no CORS issues.
- In production (Docker), one `api` container handles both API requests and static file serving. No Nginx required at Tier 1.

---

## Consequences

- Frontend development requires Node.js locally (for `npm run dev`). This is a one-time developer environment setup, not a runtime dependency.
- The Svelte build step must be included in the Docker build for the `api` container, or run as a pre-build step in CI. This is handled in the `api/Dockerfile` multi-stage build.
- SSE is unidirectional (server → client only). For any future bidirectional interaction (e.g., sending commands to machines), WebSockets would be needed. For NEXUS's current scope (monitoring, alerting, acknowledging), SSE is sufficient and simpler.

---

## Rejected Alternatives

**React** — more ecosystem, but 5× larger bundle, more boilerplate, and we have no existing React expertise to leverage.

**Streamlit** — excellent for data scientists building rapid prototypes, but CSS and layout control is limited. Not suitable for a production-looking plant operator UI.

**Separate Nginx container** — adds operational complexity for a single-host deployment with no benefit. Revisit only if the API is deployed behind a multi-host ingress.
