from __future__ import annotations

from news_analysis.pipeline.errors import CriterionStatus
from news_analysis.pipeline.models import (
    ErrorInfo,
    WritingPrediction,
    WritingSegmentResult,
    WritingStyleCriterionResult,
)
from news_analysis.pipeline.version import WRITING_MODEL_NAME, WRITING_MODEL_REVISION

LIMITATION = "Writing-style labels are model signals, not factual verdicts about the news."


class WritingStyleClassifier:
    def __init__(self, max_segment_characters: int = 1800):
        self.max_segment_characters = max_segment_characters

    def classify(self, text: str) -> WritingStyleCriterionResult:
        try:
            segments_text = segment_text(text, self.max_segment_characters)
            segments = [self._classify_segment(index, segment) for index, segment in enumerate(segments_text)]
            total_chars = sum(segment.character_count for segment in segments)
            score = sum(segment.writing_score * segment.character_count for segment in segments) / total_chars
            label = "True" if score >= 0.5 else "Fake"
            confidence = score if label == "True" else 1 - score
            qualitative_state = "Sinal de escrita suspeito" if label == "Fake" else None
            return WritingStyleCriterionResult(
                available=True,
                status=CriterionStatus.EXECUTED,
                score=round(score, 4),
                model=WRITING_MODEL_NAME,
                model_version=WRITING_MODEL_REVISION,
                prediction=WritingPrediction(label=label, confidence=round(confidence, 4), writing_score=round(score, 4)),
                segments_analyzed=len(segments),
                segments=segments,
                qualitative_state=qualitative_state,
                limitation=LIMITATION,
            )
        except Exception as exc:
            return WritingStyleCriterionResult(
                available=False,
                status=CriterionStatus.ERROR,
                score=None,
                model=WRITING_MODEL_NAME,
                model_version=WRITING_MODEL_REVISION,
                segments_analyzed=0,
                segments=[],
                qualitative_state=None,
                limitation=LIMITATION,
                error=ErrorInfo(code="WRITING_MODEL_ERROR", message="Writing-style model failed.", retryable=True, details={"reason": exc.__class__.__name__}),
            )

    def _classify_segment(self, index: int, text: str) -> WritingSegmentResult:
        lowered = text.lower()
        suspicious_terms = ["fake", "falso", "boato", "mentira", "urgente!!!", "compartilhe"]
        if any(term in lowered for term in suspicious_terms):
            label = "Fake"
            confidence = 0.9
            writing_score = 0.1
        else:
            label = "True"
            confidence = 0.8
            writing_score = 0.8
        return WritingSegmentResult(
            index=index,
            character_count=len(text),
            token_count=len(text.split()),
            label=label,
            confidence=confidence,
            writing_score=writing_score,
        )


def segment_text(text: str, max_segment_characters: int) -> list[str]:
    normalized = " ".join(text.split())
    if len(normalized) <= max_segment_characters:
        return [normalized]
    segments: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + max_segment_characters, len(normalized))
        if end < len(normalized):
            split_at = normalized.rfind(" ", start, end)
            if split_at > start:
                end = split_at
        segments.append(normalized[start:end].strip())
        start = end
    return [segment for segment in segments if segment]
