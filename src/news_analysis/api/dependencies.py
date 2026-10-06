from __future__ import annotations

from functools import lru_cache

from news_analysis.config import Settings
from news_analysis.criteria.recognition import RecognitionProvider
from news_analysis.criteria.source_credibility import SourceCredibility
from news_analysis.pipeline.analyzer import NewsAnalyzer
from news_analysis.storage.audit_repository import AuditRepository
from news_analysis.storage.atlas_repository import AtlasRepository


@lru_cache
def get_settings() -> Settings:
    settings = Settings.from_env()
    settings.ensure_storage_parent()
    return settings


@lru_cache
def get_repository() -> AuditRepository:
    return AuditRepository(get_settings().db_path)


@lru_cache
def get_atlas_repository() -> AtlasRepository:
    return AtlasRepository(get_settings().db_path)


@lru_cache
def get_source_credibility() -> SourceCredibility:
    config = get_settings().credibility_config()
    recognition = RecognitionProvider(config, get_atlas_repository() if config.atlas.enabled else None)
    return SourceCredibility(config, recognition=recognition)


@lru_cache
def get_analyzer() -> NewsAnalyzer:
    return NewsAnalyzer(get_settings(), get_repository(), source_credibility=get_source_credibility())
