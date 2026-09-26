from __future__ import annotations

from enum import Enum


class AnalysisStatus(str, Enum):
    SUCCESS = "SUCCESS"
    INVALID_URL = "INVALID_URL"
    BLOCKED_INTERNAL_URL = "BLOCKED_INTERNAL_URL"
    NEWS_FETCH_FAILED = "NEWS_FETCH_FAILED"
    ARTICLE_EXTRACTION_FAILED = "ARTICLE_EXTRACTION_FAILED"
    FACT_CHECK_API_ERROR = "FACT_CHECK_API_ERROR"
    WRITING_MODEL_ERROR = "WRITING_MODEL_ERROR"
    CRITERION_UNAVAILABLE = "CRITERION_UNAVAILABLE"
    RATE_LIMITED = "RATE_LIMITED"


class CriterionStatus(str, Enum):
    EXECUTED = "EXECUTED"
    UNAVAILABLE = "UNAVAILABLE"
    ERROR = "ERROR"
    NOT_IMPLEMENTED = "NOT_IMPLEMENTED"


HTTP_STATUS_BY_ANALYSIS_STATUS = {
    AnalysisStatus.INVALID_URL: 400,
    AnalysisStatus.BLOCKED_INTERNAL_URL: 403,
    AnalysisStatus.RATE_LIMITED: 429,
    AnalysisStatus.NEWS_FETCH_FAILED: 502,
    AnalysisStatus.ARTICLE_EXTRACTION_FAILED: 502,
    AnalysisStatus.FACT_CHECK_API_ERROR: 502,
    AnalysisStatus.WRITING_MODEL_ERROR: 502,
}


class AnalysisError(Exception):
    status: AnalysisStatus
    retryable: bool

    def __init__(self, status: AnalysisStatus, message: str, retryable: bool = False, details: dict | None = None):
        super().__init__(message)
        self.status = status
        self.message = message
        self.retryable = retryable
        self.details = details or {}
