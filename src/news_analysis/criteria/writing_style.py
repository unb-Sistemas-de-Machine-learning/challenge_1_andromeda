from __future__ import annotations

from functools import lru_cache
from threading import Lock

from news_analysis.pipeline.errors import CriterionStatus
from news_analysis.pipeline.models import (
    ErrorInfo,
    WritingPrediction,
    WritingSegmentResult,
    WritingStyleCriterionResult,
)
from news_analysis.pipeline.version import WRITING_MODEL_NAME, WRITING_MODEL_REVISION

LIMITATION = "Writing-style labels are model signals, not factual verdicts about the news."
_INFERENCE_LOCK = Lock()


@lru_cache(maxsize=4)
def _load_model(cache_dir: str | None):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    options = {"revision": WRITING_MODEL_REVISION, "cache_dir": cache_dir}
    tokenizer = AutoTokenizer.from_pretrained(WRITING_MODEL_NAME, use_fast=True, **options)
    model = AutoModelForSequenceClassification.from_pretrained(WRITING_MODEL_NAME, **options)
    model.to("cpu")
    model.eval()
    return tokenizer, model


class WritingStyleClassifier:
    def __init__(self, cache_dir: str | None = None):
        self.cache_dir = cache_dir

    def classify(self, text: str) -> WritingStyleCriterionResult:
        try:
            if not text.strip():
                raise ValueError("Article text is empty.")
            # Serialize loading and inference so concurrent requests reuse one CPU model.
            with _INFERENCE_LOCK:
                segments = self._classify_segments(text)
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

    def _classify_segments(self, text: str) -> list[WritingSegmentResult]:
        import torch

        tokenizer, model = _load_model(self.cache_dir)
        if model.config.num_labels != 2:
            raise ValueError("Expected a binary classifier.")
        normalized = " ".join(text.split())
        encoded = tokenizer(
            normalized,
            truncation=True,
            max_length=min(512, model.config.max_position_embeddings),
            stride=0,
            return_overflowing_tokens=True,
            return_offsets_mapping=True,
        )
        segments = []
        previous_end = 0
        with torch.inference_mode():
            for index, offsets in enumerate(encoded["offset_mapping"]):
                content_offsets = [(start, end) for start, end in offsets if end > start]
                if not content_offsets:
                    raise ValueError("Tokenizer produced an empty segment.")
                end = content_offsets[-1][1]
                inputs = {
                    name: torch.tensor([encoded[name][index]], dtype=torch.long)
                    for name in tokenizer.model_input_names if name in encoded
                }
                probabilities = model(**inputs).logits.softmax(dim=-1)[0]
                # The author's mapping is LABEL_0 = Fake and LABEL_1 = True.
                writing_score = float(probabilities[1].item())
                label = "True" if writing_score >= 0.5 else "Fake"
                confidence = writing_score if label == "True" else float(probabilities[0].item())
                segments.append(WritingSegmentResult(
                    index=index,
                    character_count=end - previous_end,
                    token_count=len(encoded["input_ids"][index]),
                    label=label,
                    confidence=confidence,
                    writing_score=writing_score,
                ))
                previous_end = end
        return segments
