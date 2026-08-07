# Vikram execution plans

An execution plan, or ExecPlan, is a living implementation document for work that is too broad or uncertain to hold safely in a chat checklist. It must let a contributor resume the work using only the current repository and the plan.

## When an ExecPlan is required

Create an ExecPlan when work does any of the following:

- crosses the desktop, API, worker, or database boundary;
- changes authentication, permissions, privacy, or an external-action approval gate;
- introduces or replaces a model, voice, storage, retrieval, scheduling, or OS provider;
- adds a schema migration or durable background workflow;
- contains a feasibility question that needs a prototype;
- is expected to span more than one focused implementation session.

Store active plans in `plans/active/<short-name>.md`. Move them to `plans/completed/` after acceptance passes. One plan owns one coherent user-visible outcome.

## Rules for authoring and execution

- Make the plan self-contained. State the purpose, repository context, assumptions, exact paths, interfaces, commands, and observable results.
- Write for a capable contributor who is new to Vikram. Define repository-specific terms in plain language.
- Describe user-visible behavior before implementation details.
- Resolve ordinary reversible ambiguity in the plan and record the reason. Escalate only decisions that materially change scope, safety, cost, or user data.
- Keep the plan current. Update progress, decisions, discoveries, and validation while working, not in a final cleanup pass.
- Prefer proof-of-concept milestones when a library, file format, model capability, or performance assumption is uncertain.
- Acceptance must describe behavior a person can observe or a command whose output can be checked.
- Do not use an ExecPlan as a substitute for tests, source documentation, or a stable API contract.

## Required plan structure

Every ExecPlan uses the following sections.

### Purpose and user outcome

Explain what the user can do after the change and why it matters.

### Scope and non-goals

Define what this plan owns and name adjacent behavior it intentionally leaves unchanged.

### Progress

Use timestamped checkboxes. Split partially completed work so finished and remaining tasks are unambiguous.

### Context and repository map

Name the relevant files, modules, processes, data stores, and existing behavior. Explain how they connect.

### Interfaces and data contracts

Describe new or changed API, IPC, database, event, provider, and UI-state contracts. Include authorization and failure behavior.

### Milestones

For each milestone, state the implementation, exact verification, expected observation, and safe stopping point. Each milestone should leave the repository coherent.

### Validation and acceptance

List commands and manual scenarios. Include unhappy paths, permissions, privacy, and provenance checks where relevant.

### Rollback and recovery

Explain how to retry safely, reverse migrations or feature exposure, and recover from partial background work.

### Decisions

Record the decision, alternatives considered, reason, date, and owner.

### Discoveries

Record unexpected behavior, evidence, performance results, library constraints, or invalidated assumptions.

### Outcome and follow-ups

At completion, summarize what shipped, what was proven, remaining limitations, and separate follow-up plans.

## Minimal skeleton

```md
# <Outcome-oriented title>

## Purpose and user outcome

## Scope and non-goals

## Progress

- [ ] YYYY-MM-DD HH:MMZ — First observable milestone.

## Context and repository map

## Interfaces and data contracts

## Milestones

## Validation and acceptance

## Rollback and recovery

## Decisions

## Discoveries

## Outcome and follow-ups
```
