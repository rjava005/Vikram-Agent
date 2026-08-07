# Desktop application instructions

These instructions apply under `apps/desktop` and refine the repository root `AGENTS.md`.

## Process boundaries

- Keep `main`, `preload`, and `renderer` imports one-directional and explicit.
- The renderer runs with `nodeIntegration: false`, `contextIsolation: true`, and renderer sandboxing enabled.
- Expose one purpose-specific preload method per approved capability. Never expose raw `ipcRenderer`, shell execution, unrestricted paths, or provider credentials.
- Validate the sender and runtime payload of every privileged IPC request.
- Restrict navigation, window creation, external protocols, and permission requests with allowlists.
- Use a restrictive Content Security Policy and local packaged UI assets.

## UI behavior

- Use React components and TypeScript strict mode.
- Use TanStack Query for server state and small Zustand stores for transient UI state.
- Keep all microphone states visible: idle, requesting permission, recording, processing, playing, denied, and error.
- Keyboard navigation, focus visibility, reduced motion, screen-reader names, and sufficient contrast are acceptance requirements.
- Do not use color as the only encoding for project status or type.
- Provide deterministic empty, loading, offline, and failure states before polishing animation.

## Visual surfaces

- Use React Flow for editable structured engineering plans and dependency graphs.
- Introduce tldraw only for the freeform brainstorming board in its own milestone.
- Introduce Sigma.js only for the later high-node-count constellation view.
- Keep graph nodes tied to stable domain identifiers; layout coordinates are presentation data, not project truth.

## Verification

Run the package’s formatter, lint, type, component, and smoke checks. For security-sensitive preload changes, add a test proving the renderer cannot access capabilities outside the declared bridge.
