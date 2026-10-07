from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from news_analysis.asset_paths import FLAN_DIR, FLAN_MANIFEST, WRITING_ONNX


@dataclass(frozen=True)
class Settings:
    factcheck_api_key: str | None = None
    db_path: str = ".data/news_analysis.sqlite3"
    model_cache: str | None = None
    writing_onnx_path: str | None = str(WRITING_ONNX)
    fetch_timeout_seconds: float = 10.0
    max_download_bytes: int = 5 * 1024 * 1024
    max_redirects: int = 5
    rate_limit_per_minute: int = 10
    min_extracted_characters: int = 1000
    recognized_domains_path: str | None = None
    misinformation_domains_path: str | None = None
    atlas_enabled: bool = False
    atlas_auth_mode: str = 'dummy'
    atlas_email: str | None = field(default=None, repr=False)
    atlas_password: str | None = field(default=None, repr=False)
    explanation_sml_enabled: bool = True
    explanation_sml_model: str = str(FLAN_DIR)
    explanation_sml_revision: str | None = "0fc9ddf78a1e988dac52e2dac162b0ede4fd74ab"
    explanation_sml_manifest: str | None = str(FLAN_MANIFEST)
    explanation_max_new_tokens: int = 160
    explanation_max_input_tokens: int = 256
    explanation_timeout_seconds: float = 8.0

    def credibility_config(self):
        """Resolve local source databases without bundling unverified ratings."""
        from news_analysis.criteria.credibility_config import AtlasConfig, CredibilityConfig
        return CredibilityConfig(
            recognized_path=Path(self.recognized_domains_path) if self.recognized_domains_path else None,
            blocklist_path=Path(self.misinformation_domains_path) if self.misinformation_domains_path else None,
            atlas=AtlasConfig(enabled=self.atlas_enabled, auth_mode=self.atlas_auth_mode,
                              email=self.atlas_email, password=self.atlas_password),
        )

    @classmethod
    def from_env(cls) -> "Settings":
        values = _combined_environment()
        return cls(
            factcheck_api_key=values.get("FACTCHECK_API_KEY") or None,
            db_path=values.get("NEWS_ANALYSIS_DB_PATH", cls.db_path),
            model_cache=values.get("NEWS_ANALYSIS_MODEL_CACHE") or None,
            writing_onnx_path=values.get("NEWS_ANALYSIS_WRITING_ONNX_PATH") or cls.writing_onnx_path,
            recognized_domains_path=values.get("NEWS_ANALYSIS_RECOGNIZED_DOMAINS") or None,
            misinformation_domains_path=values.get("NEWS_ANALYSIS_MISINFORMATION_DOMAINS") or None,
            atlas_enabled=_read_bool(values.get('NEWS_ANALYSIS_ATLAS_ENABLED', 'false')),
            atlas_auth_mode=values.get('NEWS_ANALYSIS_ATLAS_AUTH_MODE', 'dummy'),
            atlas_email=values.get('NEWS_ANALYSIS_ATLAS_EMAIL') or None,
            atlas_password=values.get('NEWS_ANALYSIS_ATLAS_PASSWORD') or None,
            explanation_sml_enabled=_read_bool(values.get('NEWS_ANALYSIS_SML_ENABLED', 'true')),
            explanation_sml_model=values.get('NEWS_ANALYSIS_SML_MODEL') or cls.explanation_sml_model,
            explanation_sml_revision=values.get('NEWS_ANALYSIS_SML_REVISION') or cls.explanation_sml_revision,
            explanation_sml_manifest=values.get('NEWS_ANALYSIS_SML_MANIFEST') or cls.explanation_sml_manifest,
            explanation_max_new_tokens=int(values.get('NEWS_ANALYSIS_SML_MAX_NEW_TOKENS', '160')),
            explanation_max_input_tokens=int(values.get('NEWS_ANALYSIS_SML_MAX_INPUT_TOKENS', '256')),
            explanation_timeout_seconds=float(values.get('NEWS_ANALYSIS_SML_TIMEOUT_SECONDS', '8')),
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


def _read_bool(value: str) -> bool:
    if value.lower() in {'true', '1', 'yes'}:
        return True
    if value.lower() in {'false', '0', 'no'}:
        return False
    raise ValueError('invalid_boolean_configuration')


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
