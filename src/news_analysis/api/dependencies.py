from __future__ import annotations

from functools import lru_cache

from news_analysis.config import Settings
from news_analysis.pipeline.analyzer import NewsAnalyzer
from news_analysis.storage.audit_repository import AuditRepository


@lru_cache
def get_settings() -> Settings:
    settings = Settings.from_env()
    settings.ensure_storage_parent()
    return settings


@lru_cache
def get_repository() -> AuditRepository:
    return AuditRepository(get_settings().db_path)


def get_analyzer() -> NewsAnalyzer:
    return NewsAnalyzer(get_settings(), get_repository())
