from __future__ import annotations

import sqlite3


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
