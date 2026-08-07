# Desktop UI direction

## Reading the concept image

The concept establishes the right emotional center: Vikram should feel calm, visual, and immediately ready to listen. The main opportunity is to replace large decorative containers with a stronger information hierarchy and clearer active state.

Keep the blue-violet identity, rounded geometry, central workspace, today panel, and assistant dock. Reduce the outer glow, use a neutral near-black surface behind the blue accents, and reserve saturated color for current focus, recording, selection, and status. The clock should support the focus workflow rather than occupy its own large visual object.

## MVP workspace layout

| Region | MVP content | Later expansion |
| --- | --- | --- |
| Top bar | Current project, sync/offline state, privacy indicators, notifications, profile | Collaboration presence and workspace switcher |
| Left rail | Projects, sources, components, jobs, settings, “new project” | Saved views and constellation filters |
| Center workspace | Selected project overview, source viewer, cited assistant overlay, structured engineering plan | Freeform AI drawing board and constellation explorer |
| Right rail | Today’s tasks, focus timer, upcoming break, explanation review queue | Adaptive day plan and teammate activity |
| Assistant dock | Text input, push-to-talk, attachment, current mode, stop control | Voice conversation and scoped tool approvals |

The center should always answer “what am I working on?” before it answers “what exists in every project?” For that reason, the full constellation is deferred. The MVP center first shows one selected project and its current engineering plan.

## Assistant overlay

The assistant is an inspectable layer, not a modal chatbot that obscures the artifact.

- Selecting a citation highlights the corresponding page, code symbol, schematic region, or artifact record.
- Explanations can be pinned beside the selected artifact and converted into a task, note, or prerequisite card.
- The user can choose concise, teaching, or derivation depth without changing the underlying evidence.
- Every tool action shows its scope. A file read, microphone capture, job draft, and external submission must look visibly different.
- Recording and model work have independent stop controls.

## Two different visual tools

Do not force brainstorming, engineering planning, and large graph exploration into one canvas library.

- Use React Flow for structured subsystem plans, requirements, dependencies, status, and drill-down nodes. These graphs have domain meaning and should serialize to stable project entities.
- Add tldraw for the later friendly drawing board where the user and AI sketch, annotate images, and turn loose shapes into structured project nodes. Verify production licensing before release.
- Add Sigma.js with Graphology for the later constellation when the graph contains many nodes and needs fast zoom and filtering more than arbitrary node editing.

## Constellation interaction model

The constellation uses progressive disclosure:

1. Portfolio level: one node per project, encoded by status and project type with color plus shape or icon.
2. Project level: major subsystems such as robot arm, embedded control, perception, and frontend.
3. Subsystem level: requirements, components, software modules, documents, tests, and open decisions.
4. Artifact level: source citations, files, BOM parts, and task history.

Zoom level controls detail; it must not render every artifact at once. Search, filters, breadcrumbs, a minimap, and “return to active work” are required before visual effects.

## Accessibility and calmness

- Never use color alone for not started, in progress, blocked, and complete.
- Maintain readable contrast over gradients and glows.
- Provide reduced-motion behavior for graph movement, listening animation, and focus transitions.
- Keep the active focus task and remaining time legible at a glance.
- Use notifications sparingly; breaks should be clear and respectful, not punitive.
- Let the user snooze, skip, or explain a changed plan so personalization learns from explicit feedback.
