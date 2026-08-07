CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL CHECK (length(name) BETWEEN 1 AND 120),
    created_at TEXT NOT NULL
);

CREATE TABLE sources (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('pdf', 'markdown')),
    status TEXT NOT NULL CHECK (status IN ('ready', 'failed')),
    created_at TEXT NOT NULL
);
CREATE INDEX idx_sources_project ON sources(project_id, created_at);

CREATE TABLE source_versions (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    sha256 TEXT NOT NULL,
    storage_key TEXT NOT NULL,
    parser_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(source_id, sha256)
);

CREATE TABLE evidence_units (
    id TEXT PRIMARY KEY,
    source_version_id TEXT NOT NULL REFERENCES source_versions(id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    content TEXT NOT NULL,
    locator_kind TEXT NOT NULL CHECK (locator_kind IN ('pdf_page', 'markdown_section')),
    locator_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(source_version_id, ordinal)
);
CREATE INDEX idx_evidence_source_version ON evidence_units(source_version_id, ordinal);

CREATE TABLE answers (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    grounding TEXT NOT NULL CHECK (grounding IN ('grounded', 'insufficient_evidence')),
    provider_id TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX idx_answers_project ON answers(project_id, created_at);

CREATE TABLE answer_citations (
    id TEXT PRIMARY KEY,
    answer_id TEXT NOT NULL REFERENCES answers(id) ON DELETE CASCADE,
    evidence_id TEXT NOT NULL REFERENCES evidence_units(id),
    ordinal INTEGER NOT NULL,
    excerpt TEXT NOT NULL,
    claim_id TEXT NOT NULL,
    UNIQUE(answer_id, ordinal)
);

CREATE TABLE learning_observations (
    id TEXT PRIMARY KEY,
    answer_id TEXT NOT NULL UNIQUE REFERENCES answers(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('understood', 'unclear', 'review_later')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    source_answer_id TEXT REFERENCES answers(id) ON DELETE SET NULL,
    title TEXT NOT NULL CHECK (length(title) BETWEEN 1 AND 240),
    status TEXT NOT NULL CHECK (status IN ('todo', 'in_progress', 'completed')),
    created_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE INDEX idx_tasks_project ON tasks(project_id, status, created_at);

CREATE TABLE focus_sessions (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('active', 'paused', 'completed')),
    duration_seconds INTEGER NOT NULL CHECK (duration_seconds BETWEEN 60 AND 14400),
    elapsed_active_seconds INTEGER NOT NULL DEFAULT 0 CHECK (elapsed_active_seconds >= 0),
    current_segment_started_at TEXT,
    revision INTEGER NOT NULL DEFAULT 0 CHECK (revision >= 0),
    created_at TEXT NOT NULL,
    completed_at TEXT
);
CREATE INDEX idx_focus_task ON focus_sessions(task_id, created_at);

CREATE TABLE focus_events (
    id TEXT PRIMARY KEY,
    focus_session_id TEXT NOT NULL REFERENCES focus_sessions(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL CHECK (event_type IN ('start', 'pause', 'resume', 'complete')),
    revision INTEGER NOT NULL,
    occurred_at TEXT NOT NULL,
    UNIQUE(focus_session_id, revision)
);
