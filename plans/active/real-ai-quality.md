# Nebius grounded-AI quality milestone

## Purpose and user outcome

Vikram already proves the complete local-first engineering loop with deterministic fake providers. This milestone adds an optional, explicitly consented Nebius path that gives a user higher-quality semantic retrieval and generated explanations while preserving citations, local storage, and the secure desktop boundary. A project remains local unless the user enables remote AI for that project and attests that Zero Data Retention (ZDR) is enabled for their Nebius account.

The observable outcome is that a contributor can run the existing fake-provider workflow without secrets, or configure a Nebius key locally, opt one project into remote AI, ask a question over imported sources, and receive only claims that survive a separate evidence-verification pass. Provider failures are visible and do not silently fall back to another provider or persist an unverified answer.

## Scope and non-goals

This plan owns the project-level remote-AI policy, Nebius model and embedding adapters, hybrid local retrieval, two-pass grounded generation and verification, answer-run provenance, typed failure behavior, desktop consent and status UI, synthetic evaluations, documentation, and end-to-end verification.

The fake providers remain the default and continue to require no credentials. The renderer still has no provider, secret, Node.js, filesystem, or shell access. The loopback API remains the only product-data boundary used by the UI.

This milestone does not add streaming, a general agent framework, cloud storage, shared workspaces, Supabase, long-running workers, source crawling, OCR, repository ingestion, job automation, native CAD/EDA editing, or packaged distribution. Voice stays deterministic and push-to-talk. A later voice-provider milestone will evaluate local STT and TTS with optional NVIDIA CUDA acceleration, a CPU fallback, explicit installation/VRAM requirements, and accuracy, quality, latency, package-size, and licensing benchmarks; ElevenLabs may remain an optional adapter during that migration. It will not introduce an always-on microphone or wake word.

## Progress

- [x] 2026-08-15 05:00Z — Re-read repository instructions, product/architecture/UI/stack documents, and inspected the current tree, manifests, accepted MVP, and Git state.
- [x] 2026-08-15 05:00Z — Record product, privacy, retrieval, provider, and delivery decisions in this active ExecPlan.
- [x] 2026-08-15 05:03Z — Freeze the v1 policy/runtime/provenance/problem contract additions, add the `0002_real_ai_quality.sql` migration, prove upgrade from `0001`, and verify both migrations are packaged in the wheel.
- [ ] Implement project-level consent/ZDR policy and safe runtime/provider configuration.
- [ ] Implement Nebius embeddings, hybrid retrieval, structured generation, claim verification, failure classification, and provenance persistence.
- [ ] Add API unit, integration, security/privacy, migration, and synthetic evaluation coverage.
- [ ] Implement the desktop opt-in, ZDR attestation, remote-AI status, activity, cancellation, verified-answer, and classified-error experience.
- [ ] Run fake and mocked-provider repository checks, then run the opt-in live Nebius evaluation when a locally configured key is available.
- [ ] Request read-only owner review, resolve findings, update documentation and this plan, and move it to `plans/completed/` only after acceptance passes.

## Context and repository map

The current implementation is a pnpm/uv monorepo. `scripts/dev.mjs` generates a per-launch loopback capability and starts the FastAPI service plus Electron. The renderer client in `apps/desktop/src/renderer/api.ts` calls only `/api/v1`; Electron main retains the explicit source picker and audio permission broker. Checked-in Zod schemas in `packages/contracts/src/index.ts` mirror Pydantic models in `services/api/src/vikram_api/contracts.py`.

`services/api/src/vikram_api/app_factory.py` currently rejects every provider mode except `fake`. It wires deterministic adapters from `providers/fake.py` into `WorkspaceService`. The service retrieves local evidence, asks the model adapter for claims, verifies that each returned evidence identifier exists, and persists the resulting answer and citations. SQLite persistence lives in `repositories/sqlite.py`; migrations are ordered `.sql` files under `services/api/migrations/`, with `0001_mvp.sql` as the accepted baseline. Runtime data remains under ignored `.vikram/`.

The active implementation will add provider adapters and retrieval stages without importing vendor SDKs into domain modules. The main agent owns this plan, shared contracts, migration shape, integration, documentation, and final verification. The requested `researcher` is read-only. A `backend_ai_engineer` may own bounded API/provider files after contracts are frozen, a `frontend_engineer` may own bounded desktop files after the HTTP contract is frozen, and a `reviewer` will perform the final read-only audit. No two write-capable agents will own overlapping files concurrently.

The working tree contained one pre-existing untracked user file, `examples/EGO_sEMG.md`, at milestone start. It is outside this plan and must not be edited, staged, committed, or removed.

## Interfaces and data contracts

### Runtime configuration

`VIKRAM_PROVIDER_MODE` accepts `fake` (default) or `nebius`. Nebius mode additionally requires `NEBIUS_API_KEY`. The API base URL is fixed in code to `https://api.tokenfactory.nebius.com/v1/`; it is not a renderer-controlled or arbitrary endpoint. Initial model candidates are `Qwen/Qwen3-30B-A3B-Instruct-2507` for generation/verification and `Qwen/Qwen3-Embedding-8B` for embeddings, with server-side environment overrides. Startup validates configuration but does not make a paid request. A live acceptance command validates actual account/model availability and fails visibly rather than silently selecting a different model.

The key stays in the API process environment. It is never accepted through `/api/v1`, returned by health/status, stored in SQLite, logged, written to `.env`, exposed to Electron, or included in evaluation artifacts.

### Project AI policy

Each project has a policy with `mode: local | nebius`, `zdr_attested: boolean`, an optimistic `revision`, and UTC `updated_at`. Existing and newly created projects default to `local`. The new route is:

`PUT /api/v1/projects/{project_id}/ai-policy`

The request contains `mode`, `zdr_attested`, and `expected_revision`. Selecting `nebius` requires `zdr_attested=true` and a server runtime configured for Nebius. Selecting `local` clears the attestation and deletes cached remote embeddings for that project. Revision conflicts return a typed conflict response. The workspace response includes the current policy so reloads preserve the user-visible choice.

The consent dialog states that question text and bounded source excerpts will be transmitted to Nebius. Because Vikram cannot inspect the provider account setting, the user must attest that ZDR is enabled. This is an explicit product/privacy assumption selected by the user. If Nebius changes its privacy terms or ZDR cannot be relied upon, remote AI must remain disabled until this contract is revisited.

### Answering and provenance

For local projects, the existing deterministic path remains unchanged. For Nebius projects, the API embeds missing evidence in bounded batches, creates lexical and vector ranks, fuses them with reciprocal-rank fusion, and sends at most four accepted evidence units to generation. The temporary remote-indexing limit is 256 evidence units per project; exceeding it returns a typed failure instead of issuing unbounded paid requests.

Generation requests structured claims that reference opaque evidence IDs. Retrieved source text is delimited and explicitly treated as untrusted data. A separate Nebius verification request judges each claim against its cited evidence. Generation may be retried once for malformed/unsupported output; transport calls use bounded timeouts and one SDK-level retry for transient failures. The API constructs displayed factual text only from verifier-approved claims. If no claim survives, it returns an insufficient-evidence/verification failure and does not persist an answer.

Persisted answer-run metadata includes provider and model identifiers, embedding model, retrieval strategy and prompt/verifier versions, latency and token usage when supplied, candidate evidence IDs and ranks/scores, and claim verification outcomes. It must not persist full provider request/response bodies or duplicate private source text in telemetry. Existing answer fields stay compatible while the v1 response adds a safe structured provenance summary and verification state.

### Failures, health, and cancellation

RFC 7807 responses gain a stable `code` and `retryable` flag for at least: remote consent required, ZDR attestation required, provider not configured, provider authentication, rate limit, timeout, unavailable, invalid structured output, verification failure, revision conflict, and remote index limit. Provider error bodies are not forwarded verbatim.

Health returns a safe AI runtime descriptor: active server mode, whether Nebius configuration is available, model identifiers, and no secret or account data. The desktop uses this plus project policy to render `Local deterministic` or `Nebius remote · ZDR attested` and provider activity. Requests are cancelable from the client; cancellation stops awaiting the provider and never commits a partial answer. Token streaming is deferred so unverified claims never appear transiently.

## Milestones

### Milestone 1 — Contract, policy, and migration foundation

Add the v1 Pydantic/Zod policy, runtime, provenance, and problem schemas. Add `0002_real_ai_quality.sql` for project policies, float32 embedding cache, answer-run metadata, retrieval candidates, and claim verification. Make migration discovery work from an installed wheel. Implement repository methods and policy routes with optimistic revisions, explicit consent validation, safe revocation, and existing-project defaults.

Verification: run formatter/lint/type checks, contract tests, policy route tests, and a migration test that initializes `0001`, inserts accepted-MVP data, applies `0002`, and observes `local` policy without data loss. Safe stopping point: fake mode and the original vertical slice remain fully functional with the new schema and contract.

### Milestone 2 — Nebius provider and grounded pipeline

Add only the official OpenAI Python SDK as a production dependency. Implement async Nebius embedding/model adapters behind the provider interfaces, provider failure classification, float32 cache serialization, lexical/vector ranking and reciprocal-rank fusion, structured generation, separate structured verification, and answer-run persistence. Keep provider selection in app wiring/configuration rather than domain logic.

Verification: unit tests use an injected mock transport and never make network calls. Cover caching, ranking determinism, malformed output, prompt-injection-shaped evidence, auth/rate-limit/timeout/unavailable classification, cancellation, one controlled retry, unsupported claims, all-negative questions, index limits, no-call-without-consent, no partial persistence, and redacted logs. Safe stopping point: fake mode passes all prior tests; mocked Nebius mode proves the full API answer path.

### Milestone 3 — Evaluation harness

Add redacted synthetic fixtures with at least 12 answerable and 4 unanswerable questions. Report retrieval recall@4, grounded-answer success, negative refusal behavior, citation validity, and verification acceptance separately. Store live reports only under ignored `.vikram/evals/`; committed fixtures contain no user source content.

Verification: deterministic/mock evaluation is part of normal tests. The live command, when `NEBIUS_API_KEY` is set locally, must achieve recall@4 of at least 90%, grounded verified answers on at least 10 of 12 answerable cases, insufficient-evidence behavior on all 4 negatives, and 100% stored citation validity/verification for emitted claims. Safe stopping point: results identify provider/model/prompt versions and can be rerun without changing application data.

### Milestone 4 — Desktop remote-AI experience

Add a project settings control and confirmation dialog that names transmitted data and requires a distinct ZDR attestation checkbox. Display the safe runtime and per-project policy, retrieval/generation/verification activity, cancellation, verified grounding state, and actionable classified provider errors. Revocation returns the project to deterministic local mode. The renderer never receives the key, chooses arbitrary provider URLs/models, or calls providers directly.

Verification: React tests cover opt-in, missing attestation, revision conflict, unavailable configuration, revocation, cancellation, verified-answer rendering, and continued local behavior. The Electron security and boundary smoke tests remain unchanged and passing. Safe stopping point: a user can distinguish local versus remote processing at all times.

### Milestone 5 — Acceptance, review, and delivery

Document exact setup, environment, fake run, live run, evaluation, privacy, revocation, and troubleshooting commands actually executed. Run all root checks, the deterministic smoke, the live eval, and a manual two-source opt-in remote flow when the user has configured the key locally. Request the required read-only owner review and resolve correctness, security, privacy, provenance, migration, and test findings.

Verification: a new contributor can run fake mode without secrets and Nebius mode with a locally supplied key; existing source/task/focus behavior remains intact; only verified cited claims are shown and stored. Update this plan's progress, decisions, discoveries, and outcome. Move it to `plans/completed/real-ai-quality.md` only after every observable acceptance criterion passes.

## Validation and acceptance

Run from the repository root with the documented environment:

```powershell
corepack pnpm format:check
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm smoke
```

Add and run focused API migration, policy, provider, retrieval, verification, privacy, and evaluation tests plus focused desktop tests during each milestone. The live evaluation command must require `NEBIUS_API_KEY` from the process environment and write only a redacted report under `.vikram/evals/`.

Manual acceptance uses two non-sensitive Markdown sources in a new project. In fake mode, complete the accepted MVP loop. In Nebius mode, first observe the disclosure, attest ZDR, enable remote AI, ask one answerable and one unanswerable question, inspect source-section citations and verification state, cancel an in-flight request once, convert the verified answer to a task, and complete a focus transition. Revoke remote AI and confirm the project returns to local mode. Inspect Git status and logs to verify no key, source content, `.vikram` data, or user-owned `examples/EGO_sEMG.md` was staged.

## Rollback and recovery

Provider exposure is reversible per project by setting policy to `local`; this deletes the project's remote embedding cache but preserves sources, answers, tasks, and focus history. Removing `NEBIUS_API_KEY` or starting with `VIKRAM_PROVIDER_MODE=fake` prevents remote calls. A failed batch is safe to retry because embeddings are keyed by provider/model/evidence/content hash and answer persistence occurs only after verification succeeds.

SQLite migrations are forward-only in normal use. Before manual rollback, copy the local database, start the previous application version against a database created before `0002`, and retain imported blobs. Do not drop `0002` tables in place because answer provenance may reference them. Contract additions are backward-compatible where possible; the desktop and API are released from the monorepo together.

## Decisions

- 2026-08-14, user/main agent — Use Nebius Token Factory as the first real model and embedding provider. Alternatives were OpenAI directly or another gateway; Nebius matches the planned Qwen evaluation target and exposes an OpenAI-compatible API.
- 2026-08-14, user/main agent — Remote processing is opt-in per project, not a global toggle. This keeps private projects local and makes the data boundary visible.
- 2026-08-14, user/main agent — Require user attestation that Nebius ZDR is enabled before remote AI can be selected. Vikram cannot verify the provider-account flag, so false attestation remains an explicit user-controlled risk rather than a hidden assumption.
- 2026-08-14, user/main agent — Use two-pass generation plus verification and fail closed. The extra latency/cost is acceptable because unsupported engineering claims must not be displayed or stored as grounded answers.
- 2026-08-14, main agent — Preserve `fake` as the default runtime and never silently fall back from a consented remote request. Silent fallback would obscure both quality and the active data boundary.
- 2026-08-14, main agent — Use local SQLite vector caching and bounded in-process hybrid fusion for this milestone. A vector database or worker is unnecessary below the explicit 256-unit limit and would add infrastructure before evaluation proves the need.
- 2026-08-14, main agent — Delay streaming until verification can gate all visible text. This prevents transient unsupported claims from appearing in the UI.
- 2026-08-14, main agent — Add the provider SDK only to `services/api/pyproject.toml` and remove the obsolete root `requirements.txt` when lock/update verification passes, leaving one authoritative Python manifest.

## Discoveries

- 2026-08-14 — The accepted MVP is present on `main` and `origin/main`; the full manual workflow was independently exercised by the user with two Markdown sources.
- 2026-08-14 — The existing domain/provider boundaries already separate parsing, embeddings, retrieval, model claims, and citation validation, but provider protocols and workspace orchestration are synchronous. Remote calls require an async/cancellation-aware evolution without regressing deterministic fakes.
- 2026-08-14 — The renderer currently hardcodes the `Local · fake providers` status; a safe server runtime descriptor and project policy must replace that label.
- 2026-08-14 — `requirements.txt` contains an unbounded historical OpenAI dependency while `services/api/pyproject.toml` and `uv.lock` are the actual environment. The duplicate manifest must not remain authoritative.
- 2026-08-14 — One user-owned untracked file, `examples/EGO_sEMG.md`, exists and is excluded from milestone changes.
- 2026-08-14 — Nebius retired the initially considered `BAAI/bge-en-icl` public endpoint on 2026-04-13. The implementation candidate changed to the currently documented `Qwen/Qwen3-Embedding-8B`; authenticated model-list validation remains required before live acceptance.

## Outcome and follow-ups

Implementation is in progress. Completion requires the fake and mocked-provider checks, live Nebius evaluation with a locally configured key, manual remote acceptance, read-only review, documentation, and plan closure.

Separate follow-up ExecPlans should cover durable background indexing beyond the temporary cap, Postgres/pgvector shared workspaces with authentication/RLS, OCR and layout-aware PDF provenance, generated API clients, streaming with verification-safe presentation, packaged sidecar supervision, and the dedicated local STT/TTS evaluation and migration (optional CUDA, CPU fallback, no always-on capture).
