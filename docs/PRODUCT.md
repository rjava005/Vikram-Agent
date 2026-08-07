# Vikram product definition

## Product promise

Vikram turns scattered engineering sources, projects, tasks, and personal working patterns into one understandable workspace. It should help the user decide, learn, and act with evidence while keeping external actions visible and reversible.

## Primary users

The first user is an electrical and systems engineer who moves between papers, firmware and software repositories, schematics, PCB layouts, CAD exports, BOMs, lab notes, job listings, and time-sensitive project tasks. Early collaboration is limited to a few invited teammates.

## Product principles

- Teach before assuming. Explanations should reveal missing prerequisite concepts without becoming a generic textbook.
- Ground before generating. Engineering answers show where evidence came from and distinguish source facts from inference.
- Suggest before acting. External side effects remain behind a clear review and approval step.
- Track evidence, not personality labels. Learning-state estimates are editable and tied to observed interactions.
- Prefer one useful end-to-end loop over many disconnected demos.
- Make active state visible: recording, retrieval, agent work, synchronization, approvals, and background jobs.

## Priority roadmap

### Phase 1 — Foundation and engineering learning MVP

- Desktop project workspace and secure capability broker.
- Project creation, tasks, daily plan, and focus sessions.
- Push-to-talk text and voice interaction.
- Import PDF and Markdown sources.
- Grounded question answering with citations and explicit uncertainty.
- Editable learning feedback: understood, unclear, and review later.
- A structured engineering-plan view with simple nodes and dependencies.
- Deterministic fake providers so the entire app works without paid API keys.

### Phase 2 — Useful engineering breadth and job scout

- Repository ingestion with symbol-aware chunks and exact file citations.
- PCB bundles: schematic/layout PDFs or images, BOM, netlist, and DRC reports.
- CAD bundles: STEP metadata, BOM, drawings, and rendered views.
- Electronic components, hardware, and software-library catalogs with canonical identity and cross-project usage.
- Scheduled job discovery, deduplication, fit scoring, gap analysis, and application-draft queue.
- Real-time collaboration for invited project members with row-level authorization.
- Retrieval and answer evaluation dashboards.

### Phase 3 — Advanced workspace

- Region-aware overlays on code, papers, schematics, PCB renders, and CAD renders.
- Native-format adapters where licensing and file-format support are reliable.
- Project constellation using expandable graph levels and status/type encoding.
- Durable cloud workflows that continue when the desktop app is closed.
- Carefully scoped OS and communication tools exposed through explicit capabilities.

## MVP acceptance loop

A user can create a project, import one engineering source, ask a question, inspect citations, mark their understanding, create a task from the answer, and complete a focus session. The loop works with fake providers and has automated coverage for the process boundaries.

## Explicit non-goals for the first milestone

- Automatic job applications or messages.
- Always-on voice capture.
- A general-purpose computer-control agent.
- Recreating Notion, a full CAD editor, or a full IDE.
- Perfect long-term personalization before feedback and evaluation data exist.
- The full constellation visualization.

## Job scout policy

Job discovery may run on a schedule and may search approved sources, normalize listings, deduplicate them, compare them with the user’s evidence-backed skills, and prepare tailored drafts. It must not submit a form, send an email or message, accept terms, or represent the user externally without a final explicit approval tied to the exact action.

## Learning profile policy

Store learning observations as small claims with a topic, confidence, supporting interaction, timestamp, and user-editable status. Prefer statements such as “asked for a prerequisite explanation of op-amp phase margin on 2026-08-06” over “does not understand control theory.” Decay or revalidate old estimates, and let the user correct them.
