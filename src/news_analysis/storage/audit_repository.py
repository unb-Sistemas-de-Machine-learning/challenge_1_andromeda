from __future__ import annotations

import json
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Any

from news_analysis.pipeline.models import Analysis, model_to_dict
from news_analysis.storage.schema import initialize_schema


class AuditRepository:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            initialize_schema(connection)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def save(self, analysis: Analysis) -> None:
        payload = _strip_forbidden_text(model_to_dict(analysis))
        article = payload.get("article") or {}
        with closing(self._connect()) as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO analyses (
                    id, status, input_url, final_url, created_at, completed_at,
                    content_hash, pipeline_version, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["id"],
                    payload["status"],
                    payload["input"]["url"],
                    article.get("final_url"),
                    payload.get("created_at"),
                    payload.get("completed_at"),
                    article.get("content_hash"),
                    payload["pipeline_version"]["id"],
                    json.dumps(payload, ensure_ascii=True, sort_keys=True),
                ),
            )
            connection.commit()

    def get(self, analysis_id: str) -> dict[str, Any] | None:
        with closing(self._connect()) as connection:
            row = connection.execute(
                "SELECT payload_json FROM analyses WHERE id = ?",
                (analysis_id,),
            ).fetchone()
        if row is None:
            return None
        payload = json.loads(row[0])
        # Project legacy records into the current output shape, preserving their
        # original score and pipeline version instead of silently rescoring them.
        criteria = payload.get("criteria", {})
        # Removed placeholder is omitted when projecting old records; stored
        # historical payloads and scores are preserved without recalculation.
        criteria.pop("factual_claims", None)
        legacy = criteria.get("source_credibility")
        # v1/v2 used this name for fact reviews; v4 reused it for independent
        # metadata signals. Never overwrite existing facts or their weights.
        if ("verifiable_facts" not in criteria and isinstance(legacy, dict)
                and "reviews_count" in legacy and "signals" not in legacy):
            criterion = criteria.pop("source_credibility")
            criterion["scope"] = "Historical analysis: original rating mapping and aggregation; not recalculated."
            criterion["target_claim"] = (payload.get("article") or {}).get("title")
            criteria["verifiable_facts"] = criterion
            for key in ("intended_weights", "effective_weights"):
                weights = payload.get("final", {}).get(key, {})
                if "source_credibility" in weights and "verifiable_facts" not in weights:
                    weights["verifiable_facts"] = weights.pop("source_credibility")
        return payload


def _strip_forbidden_text(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_forbidden_text(item)
            for key, item in value.items()
            if key not in {"text", "main_text", "extracted_text", "html"}
        }
    if isinstance(value, list):
        return [_strip_forbidden_text(item) for item in value]
    return value
