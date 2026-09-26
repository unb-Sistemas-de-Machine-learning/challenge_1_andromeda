from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    factcheck_api_key: str | None = None
    db_path: str = ".data/news_analysis.sqlite3"
    model_cache: str | None = None
    fetch_timeout_seconds: float = 10.0
    max_download_bytes: int = 5 * 1024 * 1024
    max_redirects: int = 5
    rate_limit_per_minute: int = 10
    min_extracted_characters: int = 1000

    @classmethod
    def from_env(cls) -> "Settings":
        values = _combined_environment()
        return cls(
            factcheck_api_key=values.get("FACTCHECK_API_KEY") or None,
            db_path=values.get("NEWS_ANALYSIS_DB_PATH", cls.db_path),
            model_cache=values.get("NEWS_ANALYSIS_MODEL_CACHE") or None,
            fetch_timeout_seconds=float(values.get("NEWS_ANALYSIS_FETCH_TIMEOUT_SECONDS", "10")),
            max_download_bytes=int(values.get("NEWS_ANALYSIS_MAX_DOWNLOAD_BYTES", str(cls.max_download_bytes))),
            max_redirects=int(values.get("NEWS_ANALYSIS_MAX_REDIRECTS", "5")),
            rate_limit_per_minute=int(values.get("NEWS_ANALYSIS_RATE_LIMIT_PER_MINUTE", "10")),
        )

    def ensure_storage_parent(self) -> None:
        parent = Path(self.db_path).expanduser().resolve().parent
        parent.mkdir(parents=True, exist_ok=True)


def _combined_environment() -> dict[str, str]:
    values = _read_dotenv(Path.cwd() / ".env")
    values.update(os.environ)
    return values


def _read_dotenv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values
