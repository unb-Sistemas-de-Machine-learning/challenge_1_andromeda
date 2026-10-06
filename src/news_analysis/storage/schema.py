from __future__ import annotations

import sqlite3


def initialize_atlas_schema(connection: sqlite3.Connection) -> None:
    """Add Atlas tables without changing existing analysis records."""
    connection.executescript('''
        CREATE TABLE IF NOT EXISTS atlas_snapshots (
            id TEXT PRIMARY KEY, created_at REAL NOT NULL,
            state TEXT NOT NULL, metadata_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS atlas_domain_links (
            snapshot_id TEXT NOT NULL, domain TEXT NOT NULL, atlas_id INTEGER NOT NULL,
            official_url TEXT NOT NULL, evidence_json TEXT NOT NULL,
            PRIMARY KEY(snapshot_id, domain, atlas_id, official_url)
        );
        CREATE INDEX IF NOT EXISTS idx_atlas_domain ON atlas_domain_links(snapshot_id, domain);
        CREATE TABLE IF NOT EXISTS atlas_sync_state (
            id INTEGER PRIMARY KEY CHECK(id=1), active_snapshot_id TEXT,
            last_attempt_at REAL, last_success_at REAL, last_error_code TEXT,
            lease_owner TEXT, lease_expires_at REAL
        );
        INSERT OR IGNORE INTO atlas_sync_state(id) VALUES(1);
    ''')
    connection.commit()


def initialize_schema(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS analyses (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL,
            input_url TEXT NOT NULL,
            final_url TEXT,
            created_at TEXT NOT NULL,
            completed_at TEXT,
            content_hash TEXT,
            pipeline_version TEXT NOT NULL,
            payload_json TEXT NOT NULL
        )
        """
    )
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analyses_status ON analyses(status)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_analyses_created_at ON analyses(created_at)")
    connection.commit()
