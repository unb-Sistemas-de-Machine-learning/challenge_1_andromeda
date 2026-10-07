"""Explicit Atlas synchronization CLI: python -m news_analysis.atlas_sync."""
from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from threading import Lock
from typing import Any
from zoneinfo import ZoneInfo

from news_analysis.config import Settings
from news_analysis.criteria.atlas_client import AtlasClient, AtlasError
from news_analysis.criteria.credibility_config import AtlasConfig
from news_analysis.storage.atlas_repository import AtlasRepository, SyncBusy

logger = logging.getLogger(__name__)
ATLAS_DAY_ZONE = ZoneInfo('America/Sao_Paulo')
_refresh_lock = Lock()


def sync_atlas(repository: AtlasRepository, config: AtlasConfig, *, client: AtlasClient | None = None,
               dry_run: bool = False) -> dict[str, Any]:
    """Publish only after a full, bounded collection. Failures keep the previous index."""
    if not config.enabled:
        raise AtlasError('atlas_disabled')
    owned_client = client is None
    client = client or AtlasClient(config)
    try:
        with repository.sync_lease(config.sync_budget + 10) as owner:
            collection = client.collect()
            snapshot_id = None if dry_run else repository.publish(collection, owner, max_record_drop=config.max_record_drop)
            return {key: value for key, value in collection.items() if key != 'links'} | dict(
                status='validated' if dry_run else 'published', snapshot_id=snapshot_id,
                fetched_at=datetime.now(timezone.utc).isoformat(), dry_run=dry_run)
    finally:
        if owned_client:
            client.close()


def atlas_status(repository: AtlasRepository, config: AtlasConfig) -> dict[str, Any]:
    """Read safe local operational metadata, without calling the remote API."""
    if not config.enabled:
        return dict(enabled=False, status='disabled', last_success_at=None)
    view = repository.status()
    snapshot = view['snapshot']
    age = None
    state = 'missing'
    if snapshot:
        instant = datetime.now(timezone.utc)
        created = datetime.fromisoformat(snapshot['created_at'])
        age = max(0, (instant - created).total_seconds())
        same_day = created.astimezone(ATLAS_DAY_ZONE).date() == instant.astimezone(ATLAS_DAY_ZONE).date()
        state = 'expired' if age > config.max_age else 'fresh' if same_day else 'stale'
    success = view['last_success_at']
    return dict(enabled=True, status=state, active_snapshot_id=view['active_snapshot_id'],
                age_seconds=round(age) if age is not None else None,
                last_success_at=datetime.fromtimestamp(success, timezone.utc).isoformat() if success else None,
                last_attempt_at=view['last_attempt_at'], last_error_code=view['last_error_code'], snapshot=snapshot)


def refresh_atlas_for_analysis(repository: AtlasRepository, config: AtlasConfig, *,
                               now: datetime | None = None, client: AtlasClient | None = None) -> str:
    """Refresh once per São Paulo calendar day before a new analysis uses the index.

    A failed refresh leaves the previously published snapshot in place. The
    analysis can continue, with the repository recording the sync error.
    """
    if not config.enabled:
        return 'disabled'
    instant = now or datetime.now(timezone.utc)
    with _refresh_lock:
        try:
            state = repository.status()
            success = state['last_success_at']
            if state['active_snapshot_id'] and success is not None:
                updated_day = datetime.fromtimestamp(success, timezone.utc).astimezone(ATLAS_DAY_ZONE).date()
                if updated_day == instant.astimezone(ATLAS_DAY_ZONE).date():
                    return 'current'
            sync_atlas(repository, config, client=client)
            return 'published'
        except SyncBusy:
            return 'busy'
        except Exception as exc:
            code = exc.code if isinstance(exc, AtlasError) else type(exc).__name__
            logger.warning('Atlas refresh before analysis failed: %s', code)
            return 'unavailable'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Sincronizar e consultar o índice local do Atlas da Notícia')
    commands = parser.add_subparsers(dest='command', required=True)
    sync = commands.add_parser('sync')
    sync.add_argument('--dry-run', action='store_true')
    commands.add_parser('status')
    args = parser.parse_args(argv)
    try:
        settings = Settings.from_env()
        config = settings.credibility_config().atlas
        repository = AtlasRepository(settings.db_path)
    except (ValueError, OSError):
        print(json.dumps(dict(status='error', error_code='invalid_configuration')))
        return 2
    try:
        result = atlas_status(repository, config) if args.command == 'status' else sync_atlas(repository, config, dry_run=args.dry_run)
        print(json.dumps(result, ensure_ascii=True))
        return 0
    except SyncBusy:
        print(json.dumps(dict(status='error', error_code='atlas_sync_busy')))
        return 3
    except Exception as exc:
        code = exc.code if isinstance(exc, AtlasError) else 'sync_validation_or_storage_error'
        logger.warning('Atlas sync failed: %s', code)
        print(json.dumps(dict(status='error', error_code=code)))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
