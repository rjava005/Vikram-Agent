# Vikram  repository starter

This bundle is the planning and agent-configuration layer for Vikram, a permission-aware desktop assistant for engineering work, personal focus, and job discovery.

It deliberately does not contain application code yet. Its purpose is to make the first Codex implementation pass narrow, reviewable, and consistent.

## Use this bundle

1. Copy the contents into the root of the Vikram Git repository.
2. Review `docs/PRODUCT.md`, especially the MVP boundary.
3. Adjust any undecided technology choices in `docs/STACK_DECISIONS.md`.
4. Start Codex from the repository root and paste `CODEX_PROMPT.md`.
5. Review the ExecPlan Codex creates in `plans/active/` before allowing broad implementation work.

## What each control file does

| File | Purpose |
| --- | --- |
| `AGENTS.md` | Durable repository-wide engineering and safety rules that Codex loads automatically. |
| `PLANS.md` | Required format for long-running implementation plans. |
| `CODEX_PROMPT.md` | Copy-ready prompt for the first implementation milestone. |
| `.codex/config.toml` | Project-scoped Codex configuration and subagent concurrency limit. |
| `.codex/agents/*.toml` | Narrow custom subagent roles. These replace the proposed `*.agents` files. |
| `apps/desktop/AGENTS.md` | More specific rules for Electron and React work. |
| `services/api/AGENTS.md` | More specific rules for FastAPI, retrieval, and background workflows. |

## Recommended first build

Build one vertical slice before expanding the product:

1. Create or open a project.
2. Import a PDF or Markdown engineering source.
3. Ask a question and receive an answer with source citations.
4. Mark the explanation as understood, unclear, or needs review.
5. Convert the result into a task.
6. Run a visible focus timer against that task.

This slice exercises the UI, API, source ingestion, retrieval contract, learning profile, task system, and focus workflow without prematurely building autonomous applications, arbitrary OS control, or the constellation view.

