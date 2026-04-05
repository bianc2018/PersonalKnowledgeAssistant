-- Main schema for AI Knowledge Assistant
-- Run this script on fresh database initialization

-- Knowledge items
CREATE TABLE IF NOT EXISTS knowledge_items (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('text', 'file', 'url', 'research_report')),
    current_version_id TEXT,
    is_deleted INTEGER NOT NULL DEFAULT 0 CHECK (is_deleted IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (current_version_id) REFERENCES knowledge_versions(id) DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX IF NOT EXISTS idx_knowledge_items_deleted ON knowledge_items(is_deleted);
CREATE INDEX IF NOT EXISTS idx_knowledge_items_updated ON knowledge_items(updated_at);

-- Knowledge versions
CREATE TABLE IF NOT EXISTS knowledge_versions (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL,
    content_text TEXT NOT NULL,
    content_delta REAL NOT NULL DEFAULT 0.0 CHECK (content_delta >= 0.0 AND content_delta <= 1.0),
    created_by TEXT NOT NULL CHECK (created_by IN ('user_edit', 'auto_extraction', 'import', 'research_report')),
    created_at TEXT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES knowledge_items(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_knowledge_versions_item ON knowledge_versions(item_id);

-- Attachments (encrypted raw media files)
CREATE TABLE IF NOT EXISTS attachments (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    extraction_status TEXT NOT NULL CHECK (extraction_status IN ('success', 'failed', 'pending', 'not_applicable')),
    extraction_error TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (item_id) REFERENCES knowledge_items(id) ON DELETE CASCADE
);

-- Tags
CREATE TABLE IF NOT EXISTS tags (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    color TEXT,
    created_at TEXT NOT NULL
);

-- Tag links (many-to-many)
CREATE TABLE IF NOT EXISTS tag_links (
    item_id TEXT NOT NULL,
    tag_id TEXT NOT NULL,
    PRIMARY KEY (item_id, tag_id),
    FOREIGN KEY (item_id) REFERENCES knowledge_items(id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

-- Confidence evaluations (per version)
CREATE TABLE IF NOT EXISTS confidence_evaluations (
    id TEXT PRIMARY KEY,
    version_id TEXT UNIQUE NOT NULL,
    score_level TEXT NOT NULL CHECK (score_level IN ('high', 'medium', 'low')),
    score_value REAL CHECK (score_value >= 0.0 AND score_value <= 1.0),
    method TEXT NOT NULL CHECK (method IN ('web_verification', 'commonsense_reasoning', 'hybrid')),
    rationale TEXT NOT NULL,
    evaluated_at TEXT NOT NULL,
    FOREIGN KEY (version_id) REFERENCES knowledge_versions(id) ON DELETE CASCADE
);

-- Conversations
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Messages
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);

-- Message citations
CREATE TABLE IF NOT EXISTS message_citations (
    id TEXT PRIMARY KEY,
    message_id TEXT NOT NULL,
    item_id TEXT NOT NULL,
    version_id TEXT,
    chunk_text TEXT,
    citation_index INTEGER NOT NULL,
    FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id) REFERENCES knowledge_items(id) ON DELETE CASCADE,
    FOREIGN KEY (version_id) REFERENCES knowledge_versions(id) ON DELETE SET NULL
);

-- User profile (single-user app, fixed id=1)
CREATE TABLE IF NOT EXISTS user_profiles (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    interests TEXT,
    knowledge_levels TEXT,
    last_updated TEXT NOT NULL
);

-- Research tasks
CREATE TABLE IF NOT EXISTS research_tasks (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    scope_description TEXT,
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'awaiting_input', 'completed', 'failed', 'degraded', 'pending_recheck')),
    progress_percent INTEGER NOT NULL DEFAULT 0 CHECK (progress_percent >= 0 AND progress_percent <= 100),
    search_source_used TEXT CHECK (search_source_used IN ('llm_builtin', 'search_api', 'http_crawler', 'local_llm')),
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    error_message TEXT,
    saved_item_id TEXT,
    FOREIGN KEY (saved_item_id) REFERENCES knowledge_items(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_research_tasks_status ON research_tasks(status);

-- Research sections
CREATE TABLE IF NOT EXISTS research_sections (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    section_type TEXT NOT NULL CHECK (section_type IN ('background', 'key_points', 'trends', 'conclusion', 'summary')),
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    order_index INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (task_id) REFERENCES research_tasks(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_research_sections_task ON research_sections(task_id);

-- Research citations
CREATE TABLE IF NOT EXISTS research_citations (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    source_title TEXT,
    source_url TEXT,
    source_summary TEXT,
    FOREIGN KEY (task_id) REFERENCES research_tasks(id) ON DELETE CASCADE
);

-- System config (single row, fixed id=1)
CREATE TABLE IF NOT EXISTS system_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    initialized INTEGER NOT NULL DEFAULT 0 CHECK (initialized IN (0, 1)),
    password_hash TEXT,
    salt BLOB,
    llm_config TEXT NOT NULL DEFAULT '{}',
    embedding_config TEXT NOT NULL DEFAULT '{}',
    search_config TEXT DEFAULT '{}',
    privacy_settings TEXT NOT NULL DEFAULT '{"allow_full_content": false, "allow_web_search": true, "allow_log_upload": false}',
    retry_settings TEXT NOT NULL DEFAULT '{"retry_times": 3, "timeout_seconds": 30}',
    storage_settings TEXT NOT NULL DEFAULT '{"archive_threshold_gb": 10.0, "research_concurrency_limit": 2, "version_retention_policy": null}',
    log_settings TEXT NOT NULL DEFAULT '{"level": "INFO", "retention_days": 30}',
    updated_at TEXT NOT NULL
);

-- Embedding chunks metadata (vectors stored in sqlite-vec virtual table)
CREATE TABLE IF NOT EXISTS embedding_chunks (
    id TEXT PRIMARY KEY,
    version_id TEXT NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    FOREIGN KEY (version_id) REFERENCES knowledge_versions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_embedding_chunks_version ON embedding_chunks(version_id);
