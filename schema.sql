PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE capsules (
    id          TEXT PRIMARY KEY,
    foundation  TEXT NOT NULL,
    state_json  TEXT NOT NULL DEFAULT '{}',
    is_meta     INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_capsules_foundation ON capsules(foundation);
CREATE INDEX idx_capsules_is_meta    ON capsules(is_meta) WHERE is_meta = 1;

CREATE TABLE links (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    source     TEXT NOT NULL REFERENCES capsules(id) ON DELETE CASCADE,
    type       TEXT NOT NULL,
    target     TEXT NOT NULL REFERENCES capsules(id) ON DELETE CASCADE,
    metadata   TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(source, type, target)
);
CREATE INDEX idx_links_source ON links(source, type);
CREATE INDEX idx_links_target ON links(target, type);
CREATE INDEX idx_links_type   ON links(type);

CREATE TABLE events (
    seq         INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type  TEXT NOT NULL,
    capsule_id  TEXT,
    payload     TEXT NOT NULL DEFAULT '{}',
    occurred_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_events_capsule ON events(capsule_id, occurred_at);
CREATE INDEX idx_events_type    ON events(event_type, occurred_at);

CREATE TABLE trust_scores (
    capsule_id  TEXT NOT NULL REFERENCES capsules(id) ON DELETE CASCADE,
    model_id    TEXT NOT NULL REFERENCES capsules(id),
    score       REAL NOT NULL,
    computed_at TEXT NOT NULL,
    PRIMARY KEY (capsule_id, model_id)
);

CREATE TABLE schema_version (version INTEGER NOT NULL);
INSERT INTO schema_version VALUES (1);

CREATE VIEW capsules_view AS
SELECT id, foundation, json(state_json) AS state, is_meta, created_at, updated_at
FROM capsules;
