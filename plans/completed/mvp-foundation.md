# First reviewable Vikram MVP vertical slice

## Purpose and user outcome

This plan delivers the first coherent, reviewable Vikram workflow. A new contributor can start a local FastAPI service and secure Electron desktop, create an engineering project, explicitly choose one PDF or Markdown source, ask a question whose answer cites a stored page or section, record learning feedback, turn that answer into a task, and start, pause, resume, and complete a Pomodoro-style focus session. The same loop works with deterministic fake providers and no credentials.

The milestone proves that Vikram can move from private source evidence to an inspectable explanation and then to deliberate action without giving the renderer direct filesystem, shell, database, or model-provider authority.

## Scope and non-goals

This plan owns:

- a pnpm TypeScript monorepo foundation with `apps/desktop` and a Python package in `services/api`;
- a sandboxed Electron window, context-isolated narrow preload bridge, restricted navigation and permissions, and explicit PDF/Markdown picker;
- the blue-violet dashboard reorganized around project navigation, a selected-project engineering workspace, today/focus controls, and a visible assistant/recording dock;
- a versioned `/api/v1` contract, SQLite migrations, repository and provider interfaces, deterministic fake model/embedding/speech/storage/retrieval providers, and local content storage;
- Markdown and text-based PDF ingestion with immutable evidence locators, deterministic retrieval, grounded answers, learning feedback, tasks, and focus transitions;
- focused unit/integration/security tests, a desktop-to-API smoke path, and exact contributor setup documentation.

This plan does not add authentication or collaboration, autonomous submissions/messages, generic shell access, unrestricted filesystem crawling, always-on audio, native CAD/EDA editing, OCR for scanned PDFs, job scouting, the constellation, a freeform whiteboard, real paid-provider credentials, a durable independent worker, or scale infrastructure.

## Progress

- [x] 2026-08-07 04:23Z — Read all governing documents, nested instructions, repository manifests, and supplied concepts; confirmed the repository is a planning-only skeleton.
- [x] 2026-08-07 04:23Z — Requested independent dependency/security/licensing research plus frontend and backend implementation maps.
- [x] 2026-08-07 05:07Z — Established tracked API packaging, v1 transport models, local schema/migrations, deterministic providers, Markdown/PDF ingestion, grounded citations, feedback/tasks, and the focus state machine; Ruff, strict mypy, and 5 tests pass.
- [x] 2026-08-07 17:18Z — Established the secure Electron broker, exact renderer allowlist, visible push-to-talk states, and accessible concept-derived React dashboard for the complete loop.
- [x] 2026-08-07 17:23Z — Passed the final combined API, desktop, contract, migration, integration, native smoke, and documented development-launch checks.
- [x] 2026-08-07 17:18Z — Resolved the read-only review's two high and six medium findings and reconciled contributor, architecture, repository-map, and stack documentation.

## Context and repository map

At the start, the repository contains product and architecture documentation, three concept images, root guidance, nested `AGENTS.md` files, and empty `apps/desktop` and `services/api` implementation roots. It has no JavaScript workspace manifest, Python project manifest, source code, migrations, API contract, or tests. The root `.gitignore` incorrectly ignores `apps/`, `services/`, `docs/`, and `plans/`; correcting this is part of the foundation so the implementation and this plan are reviewable.

`apps/desktop/src/main` will own the native window, origin/sender checks, navigation policy, the explicit picker, and upload of selected bytes. `apps/desktop/src/preload` will expose a frozen versioned capability object. `apps/desktop/src/renderer` will own views and ephemeral UI state and will call only the typed preload bridge and loopback HTTP client. `packages/contracts` will contain the checked-in API v1 TypeScript types and runtime validators derived from the API contract. `services/api/src/vikram_api` will keep HTTP routes, domain rules, use-case services, persistence, parsing/retrieval stages, and provider adapters separate. `services/api/migrations` will contain ordered SQLite SQL migrations. Local runtime data will default to `.vikram/`, which remains ignored.

The operative concept is `concepts/App_Layout_v0.png`: keep its rounded blue-violet identity, dominant center, right-side daily work, and bottom listening affordance. The Jarvis/Tron images are mood references only; their dense HUD treatment and unknown reuse rights will not become application assets.

## Interfaces and data contracts

The HTTP base is `/api/v1`. Transport payloads are validated by Pydantic on the API and by runtime TypeScript guards before renderer use. IDs are UUID strings and stored timestamps are UTC ISO-8601 values.

- `GET /health` returns local service and contract status.
- `GET|POST /api/v1/projects` lists or creates projects.
- `GET /api/v1/projects/{project_id}` returns a project workspace aggregate.
- `POST /api/v1/projects/{project_id}/sources` accepts multipart bytes plus filename/media type, never a client filesystem path, and synchronously returns parsed source metadata for this bounded demo.
- `POST /api/v1/projects/{project_id}/answers` accepts a question and returns answer text, grounding status, and structured citations.
- `PUT /api/v1/answers/{answer_id}/feedback` records exactly one of `understood`, `unclear`, or `review_later` as an editable evidence-backed observation.
- `POST /api/v1/answers/{answer_id}/tasks` creates a project task from the answer; project task listing is part of the workspace aggregate.
- `POST /api/v1/tasks/{task_id}/focus-sessions` starts a configured session.
- `POST /api/v1/focus-sessions/{session_id}/transitions` accepts `pause`, `resume`, or `complete` with an expected revision and returns authoritative timing state.

A citation identifies the immutable evidence unit and source version, shows a safe excerpt, and has one discriminated locator: PDF `page` (one-based) or Markdown `section` with heading and line bounds. A grounded answer may use only evidence returned by retrieval; if nothing supports the question, it returns an explicit insufficient-evidence result rather than an uncited factual answer.

The preload bridge is `window.vikramDesktop.v1` with purpose-specific values and operations only: the validated loopback API connection capability, `chooseAndImportSource(projectId)`, and `microphone.requestPermission()`. Picker cancellation is a normal discriminated result. The main process validates sender, the exact renderer target, project ID, extension, MIME type, file size, and API response. It never exposes `ipcRenderer`, `invoke(channel)`, `fs`, `shell`, arbitrary paths, general environment access, or provider credentials. The renderer is configured with `nodeIntegration: false`, `contextIsolation: true`, and `sandbox: true`. Navigation, new windows, external protocols, and permissions are denied unless explicitly allowlisted; microphone permission is audio-only and triggered by the visible push-to-talk control.

Python provider ports cover model generation, embeddings, speech-to-text, text-to-speech, blob storage, and candidate retrieval. An Electron OS-capability port covers explicit selection and microphone permission. Provider selection is configuration-driven. The checked-in runtime defaults to deterministic fakes and starts without secrets; real adapters are not enabled in this milestone.

The first migration creates projects, sources, source versions, evidence units, answers, answer citations, learning observations, tasks, focus sessions, focus events, and schema version records. Raw blobs, extracted evidence, and generated answers are stored separately. Deleting sources is not exposed in this milestone.

Failure behavior is typed: validation and unsupported media return 4xx responses; missing cross-owner records return 404; optimistic focus conflicts return 409; provider and parsing failures return classified, non-secret errors; renderer HTTP calls have timeouts and present offline/error states. Private source text and credentials are never written to logs.

## Milestones

### 1. Tracked foundation and backend domain loop

Correct `.gitignore`; add root pnpm scripts, Python packaging, a checked-in v1 contract, and an ordered SQLite migration runner. Implement vendor-independent entities, repositories, fake providers, format-aware parsing, deterministic retrieval, citation verification, answer/task/feedback/focus services, thin routes, and fixtures.

Verification: create a clean temporary data directory, run migrations, run API formatting/lint/type/unit/integration checks, and exercise the full ASGI loop. Expected observation: the answer contains a stored page/section citation and the completed focus session has valid revision/timing events. Safe stopping point: the API is independently usable and deterministic.

### 2. Secure desktop and dashboard

Add Electron, React, strict TypeScript, Tailwind, query/state boundaries, and the concept-derived layout. Implement only the exact preload capabilities above, plus CSP/origin/navigation/permission policies. Connect create/import/ask/citation/feedback/task/focus UI states to the fake API. Recording states are visible as idle, requesting, recording, processing, denied, or error with an immediate stop control; audio capture is push-to-talk only.

Verification: run formatter, lint, TypeScript, component, IPC/security, and preload-surface checks. Start API and desktop development processes. Expected observation: the complete loop is keyboard operable, citations expose page/section evidence, `window.require` is unavailable, and no generic privileged method exists. Safe stopping point: contributors can review the vertical slice without credentials.

### 3. Cross-process acceptance, review, and handoff

Add one automated desktop-to-real-fake-API smoke test, exercise the visible acceptance path, inspect the rendered dashboard at desktop and constrained widths, fix defects, request a read-only security/correctness review, and reconcile `README.md`, architecture/repository/stack docs, and this plan.

Verification: use only commands present in manifests, run the full relevant suite from a clean local-data directory, review `git diff`, and follow setup commands as written. Expected observation: every acceptance action succeeds and the diff contains no secrets, unrestricted capability, broken provenance, unsafe migration, or unrelated feature. Safe stopping point: the plan can move to `plans/completed/` only when all observable criteria pass.

## Validation and acceptance

Commands will be finalized in `README.md` after they have actually run. The intended root entry points are `pnpm install`, `pnpm api:install`, `pnpm dev`, `pnpm format:check`, `pnpm lint`, `pnpm typecheck`, `pnpm test`, and `pnpm smoke`. Python-specific checks run through the environment declared by `services/api/pyproject.toml`.

Acceptance requires:

1. From empty local data, start the API and desktop using documented commands without provider secrets.
2. Create a project and see it selected in the left rail and named in the central workspace.
3. Explicitly select a supported Markdown or text-based PDF; cancellation and unsupported media remain safe and visible.
4. Ask a question and inspect at least one structured citation whose source/version/evidence exists and whose page or Markdown section is correct.
5. Record each supported feedback value without producing a permanent proficiency label.
6. Convert the answer to a task and see it in Today.
7. Start, pause, resume, and complete its focus session; reload-derived timing must not depend only on a renderer interval.
8. Verify the renderer lacks Node, shell, raw filesystem, raw IPC, credentials, and direct provider/database access. Unexpected navigation, windows, screen/video permission, malformed IPC, oversized files, and untrusted paths are rejected.
9. Run migration-from-empty, API unit/integration, renderer component, IPC security, contract, and desktop-to-API smoke checks successfully.
10. Inspect the final diff and contributor setup on the supported local environment.

## Rollback and recovery

All runtime state is local under the configured data directory. During development, a failed disposable demo database can be moved aside and recreated by rerunning ordered migrations; no command will delete user-selected source files. Source import is content-hash based and can be retried without silently crawling or modifying the original. Migrations are append-only; if a migration fails, the transaction rolls back and its schema version is not recorded.

The UI is not coupled to SQLite. A later Supabase/Postgres migration can add a repository adapter and data export/import while keeping API/domain contracts. Electron capabilities are versioned, so a problematic method can be removed from the v1 allowlist without exposing a generic fallback. Fake providers remain the safe recovery mode if a configured real provider is unavailable.

## Decisions

- 2026-08-07, owner: main agent — Use single-user local SQLite plus content-addressed local blobs for this local-first review slice. The documented Supabase/Postgres shared system of record requires authentication, RLS, and a local platform stack that are not necessary to prove this loop. Repository interfaces, versioned contracts, and portable IDs keep the change reversible; shared storage/auth is a later security ExecPlan.
- 2026-08-07, owner: main agent — Import bytes through Electron main after one explicit picker action; never send an absolute path to the renderer or API. A bounded file size avoids unbounded IPC memory use in this milestone.
- 2026-08-07, owner: main agent — Run bounded ingestion synchronously for one source. An independent worker and durable job lifecycle are deferred until measured parsing latency requires them; the service remains stage-separated so this can change without altering the UI contract.
- 2026-08-07, owner: main agent — Use deterministic extractive fake answering and token/embedding retrieval. Fake output must still pass the same citation verifier expected of a real model.
- 2026-08-07, owner: main agent — Treat `App_Layout_v0.png` as layout direction and the Jarvis/Tron images only as unshipped mood references because their licensing and dense visual language are unsuitable for the calm accessible MVP.
- 2026-08-07, owner: main agent — Use `electron-vite` 5 with Vite 7 for the desktop foundation. Electron Forge's Vite plugin remains experimental; the selected tool keeps main, preload, and renderer builds explicit without widening the capability boundary.
- 2026-08-07, owner: main agent — Use BSD-3-Clause `pypdf` for initial page-level extraction instead of PyMuPDF. PyMuPDF's AGPL/commercial terms are incompatible with silently making it a default Apache-licensed dependency; OCR, layout coordinates, and complex tables remain follow-ups.
- 2026-08-07, owner: main agent — Authenticate the loopback API with a 256-bit capability generated in memory for each canonical dev/smoke launch. Packaged `file:` renderers have an opaque `Origin: null`, so CORS alone cannot protect private evidence; the exact allowlisted renderer receives only this bounded API connection value through preload.
- 2026-08-07, owner: main agent — Keep checked-in Zod runtime validators as the TypeScript v1 contract for this slice rather than introducing a generator dependency. Pydantic remains the server boundary, the native smoke crosses both validators, and automated OpenAPI generation is a documented follow-up.

## Discoveries

- 2026-08-07 — The implementation roots are empty and there are no manifests, contracts, migrations, or tests; this is a greenfield foundation rather than an incremental feature.
- 2026-08-07 — Root `.gitignore` ignores every planned implementation and plan directory. It must be corrected before work is reviewable.
- 2026-08-07 — The host has Node 24.13 and Python 3.14.6, but `pnpm` and `uv` are not initially available; PowerShell blocks `npm.ps1`, while `npm.cmd` may remain usable. Setup must use verified commands and record supported versions.
- 2026-08-07 — Scanned PDFs require OCR and are explicitly outside this slice; text-based PDF parsing must fail clearly when no evidence text is extractable.
- 2026-08-07 — FastAPI 0.139.2 currently emits a Starlette deprecation warning for `TestClient` using `httpx`; the 7 API tests pass, but this dependency transition should be monitored rather than hidden.
- 2026-08-07 — Electron's sandboxed preload must be emitted as one CommonJS bundle; leaving runtime Zod imports external causes the native preload to fail even though unit tests pass.
- 2026-08-07 — pnpm 11 replaced the old lifecycle allowlist setting with `allowBuilds`; only Electron and esbuild are permitted to run install scripts.
- 2026-08-07 — The in-app browser had no controllable tab in this session. Native Playwright launched the real built Electron window instead and exercised the rendered workflow; visual screenshot inspection remains a manual review aid, not an unreported passing check.
- 2026-08-07 — The reviewer found false grounding at zero retrieval support and unauthenticated opaque-origin API access. Both were release blockers: retrieval now fails closed to `insufficient_evidence`, and every versioned API request requires the per-launch capability. Atomic blob writes, exact renderer paths, isolated app construction, shared endpoint configuration, normalized external strings, and an owned ephemeral-port smoke resolved all medium findings.

## Outcome and follow-ups

The reviewable slice is complete. `corepack pnpm format:check`, `corepack pnpm lint`, and `corepack pnpm typecheck` pass without warnings or errors. `corepack pnpm test` passes 2 contract tests, 5 desktop tests, and 7 API tests; the only emitted warning is the recorded upstream Starlette `TestClient` transition. `corepack pnpm smoke` builds the native application and passes its one full desktop-to-real-API acceptance test. The canonical `corepack pnpm dev` command also started both Electron and a healthy loopback API before the bounded launch check stopped them.

The native smoke generated a 256-bit capability and nondefault ephemeral port, created the project through the rendered UI, persisted and reloaded the imported source, returned and inspected a Markdown section citation, recorded feedback, created a task, and started, paused, resumed, and completed focus. It also asserted that renderer Node globals are absent and that the preload surface contains only the versioned connection, source, and microphone capabilities. The read-only reviewer found two high and six medium issues; all were resolved and regression-tested before this outcome was recorded.

Known limitations are explicit: PDF support is text-only; recorded audio is visible and safely stopped but not sent to a real provider; the local API capability is single-user process authentication, not multi-user identity/RLS; the Python wheel does not yet package migrations; and real-model claim entailment needs evaluation before an adapter can be enabled. Follow-ups are Supabase/auth/RLS, durable ingestion jobs, real provider evaluation, packaged microphone validation, OCR, generated OpenAPI clients, structured React Flow plans, and later whiteboard/constellation surfaces.
