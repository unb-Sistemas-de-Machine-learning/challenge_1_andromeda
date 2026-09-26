from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse

from news_analysis.api.dependencies import get_analyzer, get_repository, get_settings
from news_analysis.api.schemas import AnalysisRequest, AnalysisResponse
from news_analysis.config import Settings
from news_analysis.pipeline.analyzer import NewsAnalyzer
from news_analysis.pipeline.errors import AnalysisStatus, HTTP_STATUS_BY_ANALYSIS_STATUS
from news_analysis.pipeline.models import ErrorInfo, model_to_dict
from news_analysis.storage.audit_repository import AuditRepository

app = FastAPI(title="News Analysis API", version="0.1.0")


class InMemoryRateLimiter:
    def __init__(self):
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, limit: int, now: float | None = None) -> bool:
        now = now if now is not None else time.time()
        window = now - 60
        hits = self._hits[key]
        while hits and hits[0] <= window:
            hits.popleft()
        if len(hits) >= limit:
            return False
        hits.append(now)
        return True

    def reset(self) -> None:
        self._hits.clear()


rate_limiter = InMemoryRateLimiter()


@app.post("/analyses", response_model=AnalysisResponse)
def create_analysis(
    request: AnalysisRequest,
    analyzer: NewsAnalyzer = Depends(get_analyzer),
    settings: Settings = Depends(get_settings),
):
    user_key = request.user_id or request.url
    if not rate_limiter.allow(user_key, settings.rate_limit_per_minute):
        error = ErrorInfo(
            code=AnalysisStatus.RATE_LIMITED.value,
            message="Rate limit reached: only 10 analysis requests per user are accepted per minute.",
            retryable=True,
            details={"limit_per_minute": settings.rate_limit_per_minute},
        )
        return JSONResponse(
            status_code=429,
            content={"status": AnalysisStatus.RATE_LIMITED.value, "error": model_to_dict(error)},
        )
    analysis = analyzer.analyze(request.url)
    status_code = HTTP_STATUS_BY_ANALYSIS_STATUS.get(AnalysisStatus(analysis.status), 200)
    if status_code != 200:
        return JSONResponse(
            status_code=status_code,
            content={"status": analysis.status, "error": model_to_dict(analysis.error)},
        )
    return analysis


@app.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(analysis_id: str, repository: AuditRepository = Depends(get_repository)):
    payload = repository.get(analysis_id)
    if payload is None:
        return JSONResponse(
            status_code=404,
            content={
                "status": AnalysisStatus.CRITERION_UNAVAILABLE.value,
                "error": {
                    "code": "NOT_FOUND",
                    "message": "Analysis not found.",
                    "retryable": False,
                },
            },
        )
    return payload
