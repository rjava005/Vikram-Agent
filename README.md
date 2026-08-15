# Vikram: An Engineering-Focused AI Assistant

Vikram is a desktop AI workspace designed to help engineers learn, plan, and build more effectively. It brings project knowledge, technical sources, tasks, and focus tools into one place so users can move from an unfamiliar concept to an evidence-backed engineering decision and a concrete next action.

## Reviewable MVP

The default vertical slice is local-only and needs no model, voice, database, or cloud credentials. An optional Nebius mode can be enabled for individual projects after an explicit privacy disclosure and Zero Data Retention (ZDR) attestation. It provides:

- a sandboxed Electron + React + TypeScript + Tailwind desktop;
- a FastAPI service with a versioned `/api/v1` contract;
- SQLite migrations and content-addressed local source blobs;
- deterministic fake model, embedding, retrieval, speech-to-text, and text-to-speech providers;
- opt-in Nebius embeddings and two-pass generated-answer verification behind the same API boundary;
- explicit PDF/Markdown selection through the Electron main process;
- page- or section-grounded answers, editable learning feedback, tasks, and focus sessions.

This is a single-user review build. The API binds only to loopback and every `/api/v1` request requires a 256-bit capability generated in memory by the dev launcher. CORS is not treated as authentication, and the token is never logged or stored. The renderer never receives a model credential or provider URL. Do not expose the API port to a network or use this milestone for shared/private multi-user data. Supabase authentication, RLS, packaged sidecar supervision, and signed distribution belong to a later security plan.

## Prerequisites

The following versions were used for the verified setup on Windows 11:

- Node.js `24.13.0` (the workspace accepts Node 24.x);
- Python `3.14.6` (the API accepts Python 3.12 through 3.14);
- Git `2.48.1.windows.1`;
- PowerShell 5.1 or later.

`pnpm` is pinned to `11.15.1` through Corepack. Python packages are locked by `services/api/uv.lock`. JavaScript packages are locked by `pnpm-lock.yaml`.

## Setup

From the repository root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install uv

$env:UV_CACHE_DIR = Join-Path (Get-Location) '.uv-cache'
uv sync --project services\api --extra dev

$env:COREPACK_HOME = Join-Path (Get-Location) '.corepack'
corepack pnpm install --store-dir .pnpm-store
```

The pnpm install allowlist permits lifecycle scripts only for Electron and esbuild. Do not replace it with a global “allow all builds” setting.

## Launch the API and desktop

Keep the root `.venv` activated, retain the two cache environment variables from setup, and run:

```powershell
corepack pnpm dev
```

This generates a fresh local API capability, starts FastAPI at `http://127.0.0.1:8742`, and launches Electron through `electron-vite`. Runtime data is created under `.vikram/` and remains local and ignored by Git. Stop both processes with `Ctrl+C`.

### Optional Nebius remote AI

First enable organization-level ZDR in the Nebius account as described in the [Nebius legal guide](https://docs.tokenfactory.nebius.com/legal/legal-quick-guide). Vikram cannot inspect that account setting, so each project requires a user attestation before it sends data. On the first remote question, Vikram sends the project's bounded evidence units (up to the 256-unit milestone cap) to Nebius for semantic embedding and caches those vectors locally. Each answer then sends the question and at most four selected source excerpts for generation and verification. Project records, original source files, tasks, feedback, and focus data remain local.

With the virtual environment activated, configure the key only in the current PowerShell process and launch the same app:

```powershell
$env:VIKRAM_PROVIDER_MODE = 'nebius'
$secureNebiusKey = Read-Host -AsSecureString 'Nebius API key'
$env:NEBIUS_API_KEY = [System.Net.NetworkCredential]::new('', $secureNebiusKey).Password
Remove-Variable secureNebiusKey
corepack pnpm dev
```

The app still opens every project in local deterministic mode. Open the project's AI processing control, read the disclosure, attest that ZDR is enabled, and choose **Enable Nebius remote AI**. Revoking remote AI deletes that project's cached Nebius embeddings and preserves its sources, previous answers, tasks, and focus history. A failed remote request is never silently replaced with a fake answer.

## Exercise the complete slice

1. Select **New project** and name the project.
2. Select **Import source** and explicitly choose `examples/control-loop.md` (or a text-based `.pdf` up to 10 MB). Canceling the picker changes nothing.
3. Ask: `What does phase margin measure?`
4. Expand the citation and inspect its source, Markdown heading and line range. PDF citations show a one-based page.
5. Mark the answer **Understood**, **Unclear**, or **Review later**.
6. Select **Turn answer into a task**.
7. In Today, select **Focus**, then **Pause**, **Resume**, and **Complete**.
8. Optionally select the circular push-to-talk control. Recording permission is requested only after that action, every recording state is visible, and Stop immediately releases the microphone. This milestone does not send recorded audio to a real provider.

For remote acceptance, import two non-sensitive sources, enable Nebius for only that project, ask one supported and one unsupported question, inspect the **Remote verified** badge and citations, cancel one in-flight answer, then return the project to local AI. Unsupported or unverified remote claims produce a visible error and are not saved.

Scanned PDFs without extractable text fail with a visible OCR-not-available message. The app never modifies the selected source file.

## Verification

With the setup environment still active, these are the root checks used for the milestone:

```powershell
corepack pnpm format:check
corepack pnpm lint
corepack pnpm typecheck
corepack pnpm test
corepack pnpm smoke
```

`smoke` builds and launches the native Electron application, starts the real local FastAPI service with fake providers, runs the grounded workflow through task/focus completion, checks the structured citation, verifies that Node globals are absent from the renderer, and closes its processes automatically.

Validate the committed private evaluation fixture without a key:

```powershell
corepack pnpm api:eval:validate
```

After configuring `NEBIUS_API_KEY` in the current process and confirming organization-level ZDR, run the live quality gate:

```powershell
corepack pnpm api:eval:live --attest-zdr
```

The runner first checks the account's live model catalog, then evaluates 12 answerable and 4 unanswerable synthetic questions. It writes a redacted report under `.vikram/evals/` and exits nonzero unless recall@4 is at least 90%, at least 10 answerable questions produce verified grounded answers, all negative questions remain unsupported, and every emitted claim has a valid verifier-approved reference. These are private task-specific checks, not a cross-provider benchmark for publication.

## Runtime configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `VIKRAM_DATA_DIR` | `.vikram` | Local SQLite database and content-addressed blobs. |
| `VIKRAM_HOST` | `127.0.0.1` | API bind host; the canonical launcher forces loopback. |
| `VIKRAM_PORT` | `8742` | Shared API/desktop port; the launcher validates it. |
| `VIKRAM_PROVIDER_MODE` | `fake` | `fake` keeps every project deterministic and local; `nebius` makes the opt-in remote capability available. |
| `NEBIUS_API_KEY` | unset | Required only when provider mode is `nebius`; keep it in the process environment and never commit it. |
| `VIKRAM_NEBIUS_GENERATION_MODEL` | `Qwen/Qwen3-30B-A3B-Instruct-2507` | Server-selected generation and verification model; live evaluation must confirm account availability. |
| `VIKRAM_NEBIUS_EMBEDDING_MODEL` | `Qwen/Qwen3-Embedding-8B` | Server-selected semantic embedding model. |
| `VIKRAM_NEBIUS_EMBEDDING_DIMENSIONS` | `4096` | Requested embedding dimensions; changing it invalidates the matching cache and re-embeds evidence. |
| `VIKRAM_NEBIUS_TIMEOUT_SECONDS` | `45` | Total deadline for one provider operation; the desktop allows 60 seconds for the complete answer request. |
| `VIKRAM_NEBIUS_MAX_EVIDENCE_UNITS` | `256` | Temporary per-project remote-indexing limit. |
| `VIKRAM_API_BASE_URL` | `http://127.0.0.1:<VIKRAM_PORT>` | Shared renderer/main API target; only matching loopback HTTP is accepted. |
| `VIKRAM_API_TOKEN` | generated by `pnpm dev` | High-entropy per-launch local capability; required only when starting processes manually. |
| `VIKRAM_MAX_SOURCE_BYTES` | `10485760` | Maximum selected source size. |

No `.env` file is required or bundled. Keys, source excerpts, provider request/response bodies, and live evaluation data are not staged by the documented workflow.

The long-term vision is an assistant that understands a user's projects and working patterns over time without hiding its reasoning or acting beyond the user's approval. Vikram should be equally useful while reading a research paper, exploring a large codebase, reviewing a PCB or CAD design, planning a product, organizing components, or preparing for the next focused work session.

## What Vikram aims to do

- Answer questions about engineering sources with citations and clear prerequisite explanations.
- Learn which concepts a user understands, is still exploring, or wants to review later.
- Turn project goals into visual subsystem maps, requirements, dependencies, and actionable tasks.
- Plan focused work sessions with visible timers and scheduled breaks.
- Build a reusable catalog of electronic parts, hardware, and software libraries across projects.
- Scout and rank relevant jobs, then prepare application materials for user approval.
- Grow into an interactive project constellation and AI-readable brainstorming canvas.

## Initial product loop

The first MVP intentionally proves one complete workflow:

1. Create or open an engineering project.
2. Import a PDF or Markdown source.
3. Ask a technical question and receive a grounded answer with citations.
4. Record whether the explanation was understood, unclear, or should be revisited.
5. Convert the result into a project task.
6. Complete a focused work session for that task.

This loop connects source analysis, retrieval, learning memory, project planning, and personal focus without prematurely building every long-term feature.

## High-level architecture

Vikram uses a desktop-first experience with a separately testable AI and data service. External model, speech, and storage providers are accessed through interfaces so they can be evaluated or replaced without rewriting the product.

| Layer | Initial choices | Responsibility |
| --- | --- | --- |
| Desktop | Electron, React, TypeScript, Tailwind CSS | Secure cross-platform shell and user interface |
| UI data and state | TanStack Query, Zustand, accessible component primitives | Server state, focused local state, and accessible interactions |
| Visual planning | React Flow | Engineering system diagrams, dependencies, and task graphs |
| Application API | FastAPI, Python | Ingestion, retrieval, agent workflows, and typed application contracts |
| Data platform | SQLite + local content-addressed blobs for this MVP; Supabase/Postgres later | Local projects, immutable source evidence, answers, tasks, and focus events |
| Retrieval | Deterministic lexical/hash baseline behind retrieval and embedding ports | Reviewable local evidence retrieval with structured provenance and citations |
| AI models | Deterministic local default; optional Nebius-hosted Qwen behind project consent | Structured grounded generation and independent claim verification |
| Voice | Provider-neutral speech interfaces; ElevenLabs is an initial candidate | Push-to-talk transcription and the Vikram voice experience |
| Observability | OpenTelemetry-compatible tracing | Debuggable cross-process workflows with private-content redaction |

## Architecture principles

- **Ground before generating.** Technical claims should link back to their source, while inference and uncertainty remain visible.
- **Teach before assuming.** Explanations should adapt to the user's demonstrated background and expose missing prerequisites.
- **Suggest before acting.** Job submissions, messages, file changes, and other external side effects require explicit approval.
- **Keep providers replaceable.** Models, voice services, parsers, and storage integrations sit behind stable application interfaces.
- **Measure retrieval quality.** Parsing, search, citations, and answer quality are evaluated instead of assuming that a larger model fixes weak evidence.
- **Protect the desktop boundary.** Electron renderers remain sandboxed, privileged actions use narrow IPC contracts, and OS access is capability-based.
- **Build vertical slices.** Each milestone should create an end-to-end user outcome rather than a collection of disconnected demos.

## Planned roadmap

- **Phase 1 — Engineering learning MVP:** secure desktop shell, projects and tasks, source import, cited Q&A, learning feedback, visual plans, and focus sessions.
- **Phase 2 — Engineering breadth and job scout:** codebase and PCB/CAD artifact ingestion, shared component catalogs, scheduled job discovery, application drafts, and small-team collaboration.
- **Phase 3 — Advanced workspace:** contextual engineering overlays, richer native-format adapters, the project constellation, and carefully scoped background or OS capabilities.

Note: Vikram will not autonomously submit job applications, send messages, or control a user's computer without a visible and specific approval step.
