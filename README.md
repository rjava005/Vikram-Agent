# Vikram: An Engineering-Focused AI Assistant

Vikram is a desktop AI workspace designed to help engineers learn, plan, and build more effectively. It brings project knowledge, technical sources, tasks, and focus tools into one place so users can move from an unfamiliar concept to an evidence-backed engineering decision and a concrete next action.

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
| Data platform | Supabase/Postgres, Storage, Realtime, Row Level Security | Projects, sources, tasks, collaboration, and authorization |
| Retrieval | Postgres full-text search, pgvector, rank fusion | Hybrid evidence retrieval with provenance and citations |
| AI models | Provider-neutral gateway; Nebius-hosted Qwen is an initial candidate | Reasoning, explanation, structured outputs, and tool selection |
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