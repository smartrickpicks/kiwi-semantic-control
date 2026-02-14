-- V251: Suggested Fields + Alias Builder
-- Creates glossary_terms, glossary_aliases, suggestion_runs, suggestions

-- 1. glossary_terms — canonical field definitions
CREATE TABLE IF NOT EXISTS glossary_terms (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    field_key TEXT NOT NULL,
    display_name TEXT,
    description TEXT,
    data_type TEXT DEFAULT 'string',
    category TEXT,
    is_required BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_glossary_terms_workspace ON glossary_terms(workspace_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_glossary_terms_field_key
    ON glossary_terms(workspace_id, field_key) WHERE deleted_at IS NULL;

-- 2. glossary_aliases — alternate names for canonical terms
CREATE TABLE IF NOT EXISTS glossary_aliases (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    term_id TEXT NOT NULL REFERENCES glossary_terms(id),
    alias TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'manual' CHECK (source IN ('manual', 'suggestion', 'import')),
    created_by TEXT REFERENCES users(id),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at TIMESTAMPTZ,
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_glossary_aliases_workspace ON glossary_aliases(workspace_id);
CREATE INDEX IF NOT EXISTS idx_glossary_aliases_term ON glossary_aliases(term_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_glossary_aliases_normalized
    ON glossary_aliases(workspace_id, normalized_alias) WHERE deleted_at IS NULL;

-- 3. suggestion_runs — tracks each execution of the suggestion generator
CREATE TABLE IF NOT EXISTS suggestion_runs (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    document_id TEXT NOT NULL REFERENCES documents(id),
    status TEXT NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
    total_suggestions INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    created_by TEXT REFERENCES users(id),
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_suggestion_runs_workspace ON suggestion_runs(workspace_id);
CREATE INDEX IF NOT EXISTS idx_suggestion_runs_document ON suggestion_runs(document_id);

-- 4. suggestions — individual field mapping suggestions
CREATE TABLE IF NOT EXISTS suggestions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    run_id TEXT NOT NULL REFERENCES suggestion_runs(id),
    document_id TEXT NOT NULL REFERENCES documents(id),
    source_field TEXT NOT NULL,
    suggested_term_id TEXT REFERENCES glossary_terms(id),
    match_score REAL DEFAULT 0.0,
    match_method TEXT DEFAULT 'none' CHECK (match_method IN ('exact', 'fuzzy', 'keyword', 'none')),
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'accepted', 'rejected', 'dismissed')),
    resolved_by TEXT REFERENCES users(id),
    resolved_at TIMESTAMPTZ,
    candidates JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    version INTEGER NOT NULL DEFAULT 1,
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_suggestions_workspace ON suggestions(workspace_id);
CREATE INDEX IF NOT EXISTS idx_suggestions_run ON suggestions(run_id);
CREATE INDEX IF NOT EXISTS idx_suggestions_document ON suggestions(document_id);
CREATE INDEX IF NOT EXISTS idx_suggestions_status ON suggestions(workspace_id, status);
