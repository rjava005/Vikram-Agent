CREATE TABLE project_ai_policies (
    project_id TEXT PRIMARY KEY REFERENCES projects(id) ON DELETE CASCADE,
    mode TEXT NOT NULL DEFAULT 'local' CHECK (mode IN ('local', 'nebius')),
    zdr_attested INTEGER NOT NULL DEFAULT 0 CHECK (zdr_attested IN (0, 1)),
    revision INTEGER NOT NULL DEFAULT 0 CHECK (revision >= 0),
    updated_at TEXT NOT NULL,
    CHECK ((mode = 'local' AND zdr_attested = 0) OR (mode = 'nebius' AND zdr_attested = 1))
);

INSERT INTO project_ai_policies(project_id, mode, zdr_attested, revision, updated_at)
SELECT id, 'local', 0, 0, created_at FROM projects;

CREATE TABLE evidence_embeddings (
    project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    evidence_id TEXT NOT NULL REFERENCES evidence_units(id) ON DELETE CASCADE,
    provider_id TEXT NOT NULL,
    model_id TEXT NOT NULL,
    content_sha256 TEXT NOT NULL,
    dimensions INTEGER NOT NULL CHECK (dimensions > 0),
    vector_blob BLOB NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (project_id, evidence_id, provider_id, model_id, content_sha256)
);
CREATE INDEX idx_evidence_embeddings_project_model
    ON evidence_embeddings(project_id, provider_id, model_id);

CREATE TABLE answer_runs (
    answer_id TEXT PRIMARY KEY REFERENCES answers(id) ON DELETE CASCADE,
    provider_mode TEXT NOT NULL CHECK (provider_mode IN ('fake', 'nebius')),
    model_id TEXT NOT NULL,
    embedding_model_id TEXT NOT NULL,
    retrieval_strategy TEXT NOT NULL,
    verifier_model_id TEXT,
    verifier_prompt_version TEXT,
    candidate_count INTEGER NOT NULL CHECK (candidate_count >= 0),
    selected_evidence_count INTEGER NOT NULL CHECK (selected_evidence_count >= 0),
    generation_latency_ms INTEGER CHECK (generation_latency_ms >= 0),
    verification_latency_ms INTEGER CHECK (verification_latency_ms >= 0),
    input_tokens INTEGER CHECK (input_tokens >= 0),
    output_tokens INTEGER CHECK (output_tokens >= 0),
    created_at TEXT NOT NULL
);

CREATE TABLE retrieval_candidates (
    answer_id TEXT NOT NULL REFERENCES answers(id) ON DELETE CASCADE,
    evidence_id TEXT NOT NULL REFERENCES evidence_units(id),
    lexical_rank INTEGER CHECK (lexical_rank > 0),
    semantic_rank INTEGER CHECK (semantic_rank > 0),
    fused_score REAL NOT NULL CHECK (fused_score >= 0),
    selected INTEGER NOT NULL CHECK (selected IN (0, 1)),
    PRIMARY KEY (answer_id, evidence_id)
);

CREATE TABLE claim_verifications (
    answer_id TEXT NOT NULL REFERENCES answers(id) ON DELETE CASCADE,
    claim_id TEXT NOT NULL,
    evidence_ids_json TEXT NOT NULL,
    verdict TEXT NOT NULL CHECK (verdict IN ('supported', 'unsupported')),
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (answer_id, claim_id)
);
