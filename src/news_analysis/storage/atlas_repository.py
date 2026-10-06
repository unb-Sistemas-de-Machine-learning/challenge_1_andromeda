"""Persistent Atlas index with atomic publication and a cross-process lease."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing, contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from news_analysis.storage.schema import initialize_atlas_schema


class SyncBusy(RuntimeError):
    """Another process owns the synchronization lease."""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AtlasRepository:
    """Keep published versions for audit and read the active version consistently."""
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            initialize_atlas_schema(connection)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=5)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def sync_lease(self, seconds: float, *, now: datetime | None = None) -> Iterator[str]:
        """Acquire once; an expired owner cannot publish or release a newer lease."""
        timestamp = (now or utcnow()).timestamp()
        owner = str(uuid4())
        with closing(self._connect()) as connection:
            connection.execute('BEGIN IMMEDIATE')
            state = connection.execute('SELECT * FROM atlas_sync_state WHERE id=1').fetchone()
            if state['lease_owner'] and state['lease_expires_at'] > timestamp:
                raise SyncBusy('atlas_sync_busy')
            connection.execute('UPDATE atlas_sync_state SET lease_owner=?, lease_expires_at=?, last_attempt_at=? WHERE id=1',
                               (owner, timestamp + seconds, timestamp))
            connection.commit()
        try:
            yield owner
        except Exception as exc:
            with closing(self._connect()) as connection:
                connection.execute('UPDATE atlas_sync_state SET last_error_code=? WHERE id=1 AND lease_owner=?',
                                   (getattr(exc, 'code', type(exc).__name__), owner))
                connection.commit()
            raise
        finally:
            with closing(self._connect()) as connection:
                connection.execute('UPDATE atlas_sync_state SET lease_owner=NULL, lease_expires_at=NULL WHERE id=1 AND lease_owner=?', (owner,))
                connection.commit()

    def publish(self, collection: dict[str, Any], owner: str, *, now: datetime | None = None,
                max_record_drop: float = 0.5) -> str:
        """Validate a candidate and move the active pointer in one transaction."""
        if not collection['links'] or collection['received_count'] < 1:
            raise ValueError('atlas_empty_candidate')
        instant = now or utcnow()
        snapshot_id = str(uuid4())
        links = sorted(collection['links'], key=lambda link: (link['domain'], link['atlas_id'], link['official_url']))
        content = json.dumps(links, ensure_ascii=True, sort_keys=True, separators=(',', ':'))
        metadata = {key: value for key, value in collection.items() if key != 'links'}
        metadata.update(id=snapshot_id, created_at=instant.isoformat(), schema_version=1,
                        content_hash=hashlib.sha256(content.encode()).hexdigest())
        with closing(self._connect()) as connection:
            connection.execute('BEGIN IMMEDIATE')
            state = connection.execute('SELECT * FROM atlas_sync_state WHERE id=1').fetchone()
            if state['lease_owner'] != owner or state['lease_expires_at'] <= instant.timestamp():
                raise SyncBusy('atlas_lease_lost')
            if state['active_snapshot_id']:
                old = connection.execute('SELECT metadata_json FROM atlas_snapshots WHERE id=?', (state['active_snapshot_id'],)).fetchone()
                if old and collection['received_count'] < json.loads(old[0])['received_count'] * (1 - max_record_drop):
                    raise ValueError('atlas_unexpected_record_drop')
            connection.execute('INSERT INTO atlas_snapshots(id, created_at, state, metadata_json) VALUES(?,?,?,?)',
                               (snapshot_id, instant.timestamp(), 'active', json.dumps(metadata, sort_keys=True)))
            connection.executemany('INSERT INTO atlas_domain_links(snapshot_id, domain, atlas_id, official_url, evidence_json) VALUES(?,?,?,?,?)',
                [(snapshot_id, link['domain'], link['atlas_id'], link['official_url'], json.dumps(link, sort_keys=True)) for link in links])
            connection.execute("UPDATE atlas_snapshots SET state='superseded' WHERE id=?", (state['active_snapshot_id'],))
            connection.execute('UPDATE atlas_sync_state SET active_snapshot_id=?, last_success_at=?, last_error_code=NULL WHERE id=1',
                               (snapshot_id, instant.timestamp()))
            connection.commit()
        return snapshot_id

    def snapshot(self, snapshot_id: str) -> dict[str, Any] | None:
        with closing(self._connect()) as connection:
            row = connection.execute('SELECT metadata_json FROM atlas_snapshots WHERE id=?', (snapshot_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def lookup(self, domain: str) -> dict[str, Any]:
        """Snapshot and evidence are read under the same SQLite read transaction."""
        with closing(self._connect()) as connection:
            connection.execute('BEGIN')
            state = dict(connection.execute('SELECT * FROM atlas_sync_state WHERE id=1').fetchone())
            row = connection.execute('SELECT metadata_json FROM atlas_snapshots WHERE id=?', (state['active_snapshot_id'],)).fetchone()
            links = connection.execute('SELECT evidence_json FROM atlas_domain_links WHERE snapshot_id=? AND domain=?',
                                       (state['active_snapshot_id'], domain)).fetchall()
        return dict(snapshot=json.loads(row[0]) if row else None, links=[json.loads(link[0]) for link in links], state=state)

    def status(self) -> dict[str, Any]:
        result = self.lookup('')
        state = result['state']
        # Expose operational state, never the internal lease token.
        return {key: value for key, value in state.items() if key not in {'id', 'lease_owner', 'lease_expires_at'}} | {'snapshot': result['snapshot']}
