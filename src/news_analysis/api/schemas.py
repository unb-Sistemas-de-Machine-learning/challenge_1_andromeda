from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from news_analysis.pipeline.models import Analysis, ErrorInfo


class AnalysisRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str
    user_id: str | None = None


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    error: ErrorInfo


AnalysisResponse = Analysis
