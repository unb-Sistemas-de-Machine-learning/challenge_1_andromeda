"""Optional optimized CPU backend for the pinned writing-style classifier."""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path

from news_analysis.asset_paths import WRITING_ONNX
from news_analysis.bundled_models import ensure_model
from news_analysis.criteria.writing_style import WritingStyleClassifier
from news_analysis.pipeline.models import WritingSegmentResult
from news_analysis.pipeline.version import WRITING_MODEL_NAME, WRITING_MODEL_REVISION


def _manifest(path: Path) -> dict:
    manifest = json.loads((path.parent / 'manifest.json').read_text(encoding='utf-8'))
    if (manifest.get('model') != WRITING_MODEL_NAME or
            manifest.get('revision') != WRITING_MODEL_REVISION or
            manifest.get('format') != 'onnx-int8-dynamic-matmul-gather' or
            manifest.get('max_length') != 512 or
            not isinstance(manifest.get('sha256'), str)):
        raise ValueError('Optimized writing model manifest does not match the pinned classifier')
    return manifest


@lru_cache(maxsize=2)
def _load_onnx_model(path: str):
    import onnxruntime as ort
    from transformers import AutoTokenizer

    model_path = Path(path).resolve()
    manifest = _manifest(model_path)
    with model_path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if digest != manifest['sha256']:
        raise ValueError('Optimized writing model checksum mismatch')
    tokenizer = AutoTokenizer.from_pretrained(model_path.parent, use_fast=True, local_files_only=True)
    options = ort.SessionOptions()
    options.intra_op_num_threads = 4
    session = ort.InferenceSession(str(model_path), sess_options=options,
                                   providers=['CPUExecutionProvider'])
    return tokenizer, session


class OnnxWritingStyleClassifier(WritingStyleClassifier):
    """Keeps the public scoring schema and segmentation of the PyTorch backend."""

    def __init__(self, model_path: str):
        super().__init__()
        self.model_path = str(Path(model_path).resolve())
        if Path(self.model_path) == WRITING_ONNX:
            ensure_model('writing_bertimbau')
        self.model_version = f'{WRITING_MODEL_REVISION}-onnx-int8-unavailable'
        try:
            self.model_version = f'{WRITING_MODEL_REVISION}-onnx-int8-{_manifest(Path(self.model_path))["sha256"][:12]}'
        except (OSError, ValueError, KeyError, json.JSONDecodeError):
            # classify() reports a criterion error without preventing the rest
            # of the analysis from running when an optional artifact is absent.
            pass

    def _classify_segments(self, text: str) -> list[WritingSegmentResult]:
        import numpy as np

        tokenizer, session = _load_onnx_model(self.model_path)
        encoded = tokenizer(' '.join(text.split()), truncation=True, max_length=512, stride=0,
                            return_overflowing_tokens=True, return_offsets_mapping=True)
        segments = []
        previous_end = 0
        for index, offsets in enumerate(encoded['offset_mapping']):
            content_offsets = [(start, end) for start, end in offsets if end > start]
            if not content_offsets:
                raise ValueError('Tokenizer produced an empty segment.')
            end = content_offsets[-1][1]
            inputs = {item.name: np.asarray(
                [encoded[item.name][index]] if item.name in encoded else
                [[0] * len(encoded['input_ids'][index])], dtype=np.int64)
                for item in session.get_inputs()}
            logits = session.run(None, inputs)[0][0]
            probabilities = np.exp(logits - np.max(logits))
            writing_score = float(probabilities[1] / probabilities.sum())
            label = 'True' if writing_score >= 0.5 else 'Fake'
            segments.append(WritingSegmentResult(
                index=index, character_count=end - previous_end,
                token_count=len(encoded['input_ids'][index]), label=label,
                confidence=writing_score if label == 'True' else 1 - writing_score,
                writing_score=writing_score,
            ))
            previous_end = end
        return segments
