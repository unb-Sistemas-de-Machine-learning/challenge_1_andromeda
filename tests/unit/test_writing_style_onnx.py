"""The optional optimized runtime preserves the public writing criterion."""
from types import SimpleNamespace

import numpy as np

from news_analysis.criteria import writing_style_onnx
from news_analysis.pipeline.version import WRITING_MODEL_REVISION
from tests.conftest import FakeWritingTokenizer


def test_optimized_backend_preserves_segments_and_score(monkeypatch):
    class Session:
        def get_inputs(self):
            return [SimpleNamespace(name=name) for name in ('input_ids', 'attention_mask', 'token_type_ids')]

        def run(self, outputs, inputs):
            assert inputs['input_ids'].dtype == np.int64
            assert inputs['token_type_ids'].shape == inputs['input_ids'].shape
            return [np.log(np.array([[0.2, 0.8]], dtype=np.float32))]

    monkeypatch.setattr(writing_style_onnx, '_manifest', lambda path: {'sha256': 'a' * 64})
    monkeypatch.setattr(writing_style_onnx, '_load_onnx_model', lambda path: (FakeWritingTokenizer(), Session()))
    result = writing_style_onnx.OnnxWritingStyleClassifier('model.int8.onnx').classify('a' * 600)
    assert result.available
    assert result.score == 0.8
    assert result.segments_analyzed == 2
    assert sum(item.character_count for item in result.segments) == 600
    assert result.model_version == f'{WRITING_MODEL_REVISION}-onnx-int8-aaaaaaaaaaaa'


def test_missing_optimized_artifact_does_not_crash_analysis(tmp_path):
    result = writing_style_onnx.OnnxWritingStyleClassifier(str(tmp_path / 'missing.onnx')).classify('Texto')
    assert not result.available
    assert result.score is None
    assert result.error.code == 'WRITING_MODEL_ERROR'
