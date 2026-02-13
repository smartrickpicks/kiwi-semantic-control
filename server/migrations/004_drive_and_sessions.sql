-- V25-DRV: Drive integration + Session continuity + Import versioning
-- Gate 4 Layer 0: Foundation tables

-- 1. drive_connections — one per workspace, stores OAuth tokens for Drive API
CREATE TABLE IF NOT EXISTS drive_connections (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    connected_by TEXT NOT NULL REFERENCES users(id),
    drive_email TEXT,
    access_token TEXT,
    refresh_token TEXT,
    token_expiry TIMESTAMPTZ,
    scopes TEXT[] DEFAULT ARRAY['https://www.googleapis.com/auth/drive.readonly','https://www.googleapis.com/auth/drive.file'],
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'revoked')),
    connected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT uq_drive_connections_workspace UNIQUE (workspace_id)
);
CREATE INDEX IF NOT EXISTS idx_drive_connections_workspace ON drive_connections(workspace_id);

-- 2. drive_import_provenance — tracks every file import with versioning
CREATE TABLE IF NOT EXISTS drive_import_provenance (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    source_file_id TEXT NOT NULL,
    source_file_name TEXT NOT NULL,
    source_mime_type TEXT,
    source_size_bytes BIGINT,
    drive_id TEXT,
    drive_modified_time TIMESTAMPTZ,
    drive_md5 TEXT,
    version_number INTEGER NOT NULL DEFAULT 1,
    supersedes_id TEXT REFERENCES drive_import_provenance(id),
    imported_by TEXT NOT NULL REFERENCES users(id),
    imported_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    batch_id TEXT REFERENCES batches(id),
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT uq_import_version UNIQUE (workspace_id, source_file_id, version_number)
);
CREATE INDEX IF NOT EXISTS idx_import_prov_workspace ON drive_import_provenance(workspace_id);
CREATE INDEX IF NOT EXISTS idx_import_prov_file ON drive_import_provenance(workspace_id, source_file_id);
CREATE INDEX IF NOT EXISTS idx_import_prov_file_ver ON drive_import_provenance(workspace_id, source_file_id, version_number DESC);

-- 3. workbook_sessions — session continuity with dedupe
CREATE TABLE IF NOT EXISTS workbook_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id),
    workspace_id TEXT NOT NULL REFERENCES workspaces(id),
    environment TEXT NOT NULL DEFAULT 'sandbox' CHECK (environment IN ('sandbox', 'production')),
    source_type TEXT NOT NULL CHECK (source_type IN ('local', 'drive')),
    source_ref TEXT NOT NULL,
    session_data JSONB DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'archived', 'deleted')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT uq_session_dedupe UNIQUE (user_id, workspace_id, environment, source_type, source_ref)
);
CREATE INDEX IF NOT EXISTS idx_sessions_user_ws ON workbook_sessions(user_id, workspace_id);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON workbook_sessions(user_id, workspace_id, environment, status)
    WHERE status = 'active';
