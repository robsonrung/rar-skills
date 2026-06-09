# Explain Architecture — greenspark-aws reference

Read this when the scope is the greenspark-aws repo (or one of its services). It holds the
known service map, seam inventory, layer mapping, and a worked example for that codebase.

## Service map (Step 0 scope options)

One service means one of: `core-api`, `dispatch`, `eda-worker`, `erp-sync-workflow`,
`frontend`, `common`/`gslogic`.

## Seam inventory (Step 1)

- **The seams** — how units communicate: HTTP routes, EventBridge events, shared
  `common` entities/TypeORM, RTK Query API layer, cron/workers.
- **A representative flow** — e.g. frontend action → API route → service → entity/DB →
  emitted event → worker.
- **Cross-cutting** — auth, multi-tenancy (org-scoping), error handling, migrations,
  codegen (OpenAPI → RTK Query).

## Layer mapping (Step 2)

- **Business** — domain rules & invariants: `backend/common` entities/domain, `gslogic`.
- **Application** — software automating the domain: `core-api` routes & services,
  `dispatch`, `eda-worker`, `erp-sync-workflow`, `compliance`, `pdf-generator`, frontend
  RTK/API layer & React app.
- **Technology** — infra plumbing: AWS SAM/Lambda/EventBridge/S3, Postgres/TypeORM,
  Amplify auth, Vite build/deploy.

## Worked example — whole-repo, newcomer viewpoint

> **In one paragraph.** greenspark-aws is a multi-tenant scrap-metal recycling platform: a
> React/Vite frontend and a serverless AWS backend (SAM) split into domain services that
> communicate over EventBridge. All data is org-scoped (multi-tenant). The frontend's API
> layer is generated from the backend's OpenAPI schema, so types flow backend → frontend
> automatically.
>
> **The pieces.**
> - `frontend/client` — React 17 + MUI + Redux Toolkit app; API calls via generated RTK
>   Query endpoints.
> - `backend/core-api` — main REST API, business logic by domain.
> - `backend/common` — shared TypeORM entities & utilities (the data model).
> - `backend/eda-worker` — event-driven processing off EventBridge.
> - `backend/dispatch`, `erp-sync-workflow`, `compliance`, `pdf-generator` — domain
>   services for assets, ERP integration, regulatory reporting, documents.
>
> **How it fits together.** Frontend → core-api over HTTP; services emit/consume
> EventBridge events; everything shares the `common` entities and one Postgres DB; the
> frontend's typed client is regenerated from core-api's OpenAPI schema (`npm run
> generate:api`).
>
> **A flow end-to-end.** (trace a real request through route → service → entity → emitted
> event → worker, with `file:line` cites)
>
> **Where to look next.** Root `CLAUDE.md`, `backend/CLAUDE.md`, `frontend/CLAUDE.md`, then
> `backend/core-api` routes for the domain you care about.

(Replace the flow section with an actual traced request when running the skill — don't ship
the placeholder.)
