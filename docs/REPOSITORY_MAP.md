# Repository map

Vikram now uses a pnpm/uv monorepo so desktop, API, contracts, migrations, and evaluation fixtures change together while retaining strict process boundaries. The table marks the current MVP foundation and planned expansion points; a path described as later may not exist yet.

| Planned path | Responsibility |
| --- | --- |
| `AGENTS.md`, `PLANS.md`, `CODEX_PROMPT.md` | Repository guidance, long-running plan format, and initial build prompt. |
| `package.json`, `pnpm-workspace.yaml`, `pnpm-lock.yaml` | Verified contributor entry points, exact JavaScript dependency graph, and lifecycle-script allowlist. |
| `.codex/config.toml` | Project-scoped Codex behavior. |
| `.codex/agents/` | Project-scoped custom subagent TOML files. |
| `apps/desktop/src/main/` | Electron main process and capability broker. |
| `apps/desktop/src/preload/` | Narrow typed bridge between renderer and main process. |
| `apps/desktop/src/renderer/` | React application and visual workspaces. |
| `services/api/src/vikram_api/routes/` | Authenticated HTTP transport layer. |
| `services/api/src/vikram_api/domain/` | Vendor-independent domain entities and rules. |
| `services/api/src/vikram_api/services/` | Use-case orchestration. |
| `services/api/src/vikram_api/repositories/` | Persistence interfaces and implementations. |
| `services/api/src/vikram_api/providers/` | Model, voice, parser, retrieval, storage, and tool adapters. |
| `services/api/tests/` | Unit, contract, integration, authorization, and failure-path tests. |
| `services/worker/` | Scheduled or resource-heavy work; add when it needs an independent lifecycle. |
| `packages/contracts/` | Checked-in Zod transport schemas and inferred TypeScript types; generation is deferred. |
| `packages/ui/` | Shared React components after genuine reuse appears. |
| `packages/test-fixtures/` | Redacted and synthetic cross-language test inputs. |
| `supabase/migrations/` | Versioned database schema and row-level security. |
| `supabase/seed.sql` | Local development seed data. |
| `evals/retrieval/` | Retrieval candidate and ranking evaluations. |
| `evals/grounded_answers/` | Citation and answer-grounding evaluations. |
| `evals/approval_gates/` | Tests that side effects cannot bypass review. |
| `docs/` | Product, architecture, UI, decision, and operating documentation. |
| `plans/active/`, `plans/completed/` | Living and historical ExecPlans. |

For the current slice, `packages/contracts` contains checked-in Zod runtime schemas and inferred TypeScript types that mirror the Pydantic `/api/v1` models. Automated OpenAPI-to-TypeScript generation is a follow-up; the runtime validators are not generated output. `services/api/migrations/0001_mvp.sql` creates the accepted local slice and `0002_real_ai_quality.sql` adds project AI policies, remote embedding cache, retrieval candidates, and verification provenance. `evals/grounded_answers/fixture_v1.json` is synthetic and safe to commit; live reports stay under ignored `.vikram/evals/`. `supabase/migrations` is intentionally absent until the shared-workspace/auth/RLS milestone.

## Boundary rules

- `apps/desktop/src/renderer` imports only UI code and typed clients.
- `apps/desktop/src/preload` exposes a small stable capability surface.
- `apps/desktop/src/main` validates IPC and owns native operations.
- `services/api/routes` maps transport models to domain use cases; it does not contain retrieval or authorization logic.
- `services/api/domain` has no imports from FastAPI, Supabase clients, Electron, or model SDKs.
- `services/api/providers` contains vendor adapters selected through configuration.
- `packages/contracts` runtime-validates the versioned API contract. When generation is introduced, generated files remain reproducible and contain no business logic.
- `evals` contains redacted or synthetic fixtures safe to commit.

## Tooling direction

Use the pinned Corepack `pnpm` workspace for TypeScript packages and `uv` for Python dependency management. Root scripts are the contributor entry points for development, formatting, linting, typing, tests, and the native smoke test. Add contract generation or another task runner only when it replaces a manual step or root scripts become materially difficult to maintain.

Do not add a separate microservice for each domain. Extract `services/worker` only when scheduled or resource-heavy work needs an independent lifecycle.
