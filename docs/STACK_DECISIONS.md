# Stack decisions

These are starting decisions, not permanent commitments. Provider-specific code stays behind interfaces and every material replacement should be justified by an evaluation or operational need.

## Keep

| Choice | Decision | Reason |
| --- | --- | --- |
| Electron + React + TypeScript | Keep for MVP | Best fit with the intended web-style desktop UI and mature desktop packaging. The renderer must follow Electron’s security guidance: context isolation, sandboxing, no Node integration, narrow IPC, restricted navigation, and a content security policy. |
| Tailwind CSS | Keep | Fast visual iteration and consistent tokens; pair it with accessible primitives rather than hand-rolling every interaction. |
| FastAPI + Python | Keep | Strong fit for document parsing, embeddings, evaluation, scientific tooling, and typed HTTP contracts. Accept the packaging cost of a Python sidecar and test process supervision early. |
| Supabase | Keep for the first shared workspace, not the local review slice | Postgres, Auth, Storage, Realtime, row-level security, full-text search, and pgvector remain the intended shared system of record. The current single-user MVP uses SQLite/local blobs behind repository interfaces so setup needs no Docker or secrets. |
| ElevenLabs | Keep behind voice interfaces | Suitable for the selected Vikram voice. Start with push-to-talk; provide deterministic fakes and leave room for a local STT option. |
| Nebius-hosted Qwen | Keep as an opt-in evaluated provider, not a hard dependency | `Qwen/Qwen3-30B-A3B-Instruct-2507` and `Qwen/Qwen3-Embedding-8B` are configuration defaults, not assumed capabilities. Account model discovery and private task-specific evals gate live use; projects remain local until explicit ZDR attestation. |

## Add now

| Library or pattern | Use |
| --- | --- |
| electron-vite 5 | Selected for the foundation because Electron Forge's Vite plugin remains experimental. Packaging, fuse flipping, signing, and release channels are separate work. |
| TanStack Query | Server-state fetching, caching, invalidation, and mutations in the renderer. |
| Zustand | Small local UI stores for canvas selection, assistant dock, recording state, and focus controls. Do not mirror all server data into it. |
| Accessible UI primitives | Use Radix-based or equivalent primitives plus a project-owned component layer. |
| pypdf plus a Markdown section parser | BSD-licensed page/section extraction for text-based MVP sources. PyMuPDF is AGPL/commercial and is not a default dependency; OCR, layout coordinates, tables, and scans remain explicit evaluation work. |
| Fake providers | Deterministic local development and tests without paid credentials. |
| HTTPX 0.28 | Small direct async adapter for the fixed Nebius OpenAI-compatible endpoint, with explicit total deadlines, one retry, cancellation, and sanitized failures. This avoids adding an AI framework or a second HTTP stack. |

## Add later, when the named need appears

| Choice | Trigger |
| --- | --- |
| tldraw | Add for the AI-readable brainstorming board after the structured plan slice works. It is technically well matched, but verify the production license before shipping. |
| React Flow | Add when the central workspace gains editable structured plans, dependencies, subsystem trees, and stable project nodes. The MVP only reserves that surface. |
| Postgres full-text search + pgvector + reciprocal-rank fusion | Add with the shared data platform and retrieval evaluations. The local fake baseline currently uses deterministic lexical/hash retrieval. |
| OpenTelemetry-compatible tracing | Add with cross-process request/job traces after defining private-content redaction and a real trace consumer. |
| Sigma.js + Graphology | Add for the later large constellation graph. React Flow remains better for editable structured plans; Sigma is optimized for large graph visualization. |
| LangGraph | Add when a workflow truly needs durable state, pause/resume, human approval, or multi-step recovery. Do not use it for simple request/response chat. |
| Temporal | Consider when important cloud workflows must survive process and infrastructure failure for long periods. It is excessive for the first local MVP. |
| Tree-sitter | Add for symbol-aware source-code ingestion and exact code citations. |
| CAD/EDA format tools | Add one adapter at a time after defining supported exports and licensing. Start with renders, reports, BOMs, and netlists. |
| Local STT/TTS | Evaluate in a dedicated voice-provider milestone after push-to-talk privacy and latency are measured. Require a CPU fallback, optional user-installed NVIDIA CUDA acceleration, and accuracy, quality, latency, VRAM, install-size, and licensing benchmarks; keep ElevenLabs as an optional adapter during migration. |
| Wake word | Always-on listening remains a separate explicit feature and is not implied by local speech support. |

## Do not add yet

- A large agent framework solely to make ordinary service calls.
- Multiple vector databases beside Postgres.
- Kubernetes, Kafka, or a service mesh.
- Separate frontend, API, and “API-dev” agents editing overlapping contracts.
- An autonomous browser that submits job applications without per-action approval.
- Direct dependency on consumer NotebookLM behavior.

## Production RAG interpretation

The supplied “death of simple RAG” article is directionally useful, but do not cargo-cult every stage. Build a measurable pipeline: format-aware parsing, provenance, hybrid candidates, filters, fusion, deduplication, optional reranking, grounded generation, and separate retrieval/answer evaluation. Promote a stage only when an evaluation set or product constraint demonstrates its value.

Supabase already documents hybrid search using Postgres full-text search and pgvector, which is enough for the first baseline. The critical additions are provenance, evaluation, and failure behavior—not a second database.

## NotebookLM / Gemini Notebook

As of this repository plan, Google exposes notebook and source-management APIs through Gemini Notebook Enterprise, with enterprise setup and preview features. Treat it as an optional integration or benchmarking reference, not Vikram’s memory core. A portable retrieval pipeline preserves product control and avoids coupling personal projects to enterprise licensing.

## Agent count recommendation

Start with four custom roles, not five persistent development silos:

1. `researcher` — read-only evidence gathering.
2. `frontend_engineer` — Electron and React implementation.
3. `backend_ai_engineer` — merge API development, backend, retrieval, and migrations because these contracts overlap heavily at MVP scale.
4. `reviewer` — read-only integration, security, privacy, and test review.

Use the built-in general worker for repository setup and occasional DevOps work. Create a dedicated deployment agent only after CI, signing, release channels, and hosted environments form a substantial independent workstream.

## Reference documentation

- Codex repository guidance: https://learn.chatgpt.com/docs/agent-configuration/agents-md
- Codex custom agents: https://learn.chatgpt.com/docs/agent-configuration/subagents
- Codex ExecPlans: https://developers.openai.com/cookbook/articles/codex_exec_plans
- Electron security: https://www.electronjs.org/docs/latest/tutorial/security
- Supabase hybrid search: https://supabase.com/docs/guides/ai/hybrid-search
- React Flow: https://reactflow.dev/
- tldraw AI integration: https://tldraw.dev/docs/ai
- Sigma.js: https://www.sigmajs.org/
- LangGraph overview: https://docs.langchain.com/oss/python/langgraph/overview
- Gemini Notebook Enterprise API: https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-notebooks
