import pytest

from news_analysis.criteria import writing_style
from news_analysis.pipeline.version import WRITING_MODEL_REVISION
from tests.conftest import FakeWritingModel, FakeWritingTokenizer


def test_model_output_replaces_keywords(mocked_writing_model):
    result = writing_style.WritingStyleClassifier().classify("fake falso boato mentira urgente!!! compartilhe")
    assert result.available
    assert result.score == 0.8
    assert result.prediction.label == "True"
    assert result.model_version == WRITING_MODEL_REVISION
    assert len(mocked_writing_model.inputs) == 1


def test_fake_prediction_uses_probability_of_true(monkeypatch):
    monkeypatch.setattr(writing_style, "_load_model", lambda cache: (FakeWritingTokenizer(), FakeWritingModel(0.15)))
    result = writing_style.WritingStyleClassifier().classify("Texto sem palavras suspeitas.")
    assert result.score == 0.15
    assert result.prediction.label == "Fake"
    assert result.prediction.confidence == 0.85
    assert result.segments[0].writing_score == pytest.approx(0.15)


def test_long_text_covers_every_token_without_exceeding_limit(mocked_writing_model):
    text = "a" * 1200
    result = writing_style.WritingStyleClassifier().classify(text)
    assert result.available
    assert result.segments_analyzed == 3
    assert sum(segment.character_count for segment in result.segments) == len(text)
    assert sum(segment.token_count - 2 for segment in result.segments) == len(text)
    assert all(segment.token_count <= 512 for segment in result.segments)
    reconstructed = [token for inputs in mocked_writing_model.inputs for token in inputs["input_ids"][0].tolist()[1:-1]]
    assert reconstructed == [ord(char) for char in text]


def test_segment_average_preserves_character_weighting(monkeypatch):
    model = FakeWritingModel()
    def infer(**inputs):
        model.true_probability = 0.2 if len(model.inputs) == 0 else 0.9
        return model(**inputs)
    from types import SimpleNamespace
    wrapper = SimpleNamespace(config=model.config)
    class Model:
        config = wrapper.config
        __call__ = staticmethod(infer)
    monkeypatch.setattr(writing_style, "_load_model", lambda cache: (FakeWritingTokenizer(), Model()))
    result = writing_style.WritingStyleClassifier().classify("a" * 600)
    assert result.score == pytest.approx((510 * 0.2 + 90 * 0.9) / 600)


def test_model_failure_is_unavailable_without_rule_fallback(monkeypatch):
    def fail(cache):
        raise OSError("Cannot load weights")
    monkeypatch.setattr(writing_style, "_load_model", fail)
    result = writing_style.WritingStyleClassifier().classify("Texto normal")
    assert not result.available
    assert result.status == "ERROR"
    assert result.score is None
    assert result.segments == []
    assert result.error.code == "WRITING_MODEL_ERROR"


def test_empty_text_does_not_invoke_model(mocked_writing_model):
    result = writing_style.WritingStyleClassifier().classify(" \n ")
    assert not result.available
    assert not mocked_writing_model.inputs


def test_custom_cache_is_forwarded(monkeypatch):
    caches = []
    def load(cache):
        caches.append(cache)
        return FakeWritingTokenizer(), FakeWritingModel()
    monkeypatch.setattr(writing_style, "_load_model", load)
    assert writing_style.WritingStyleClassifier(cache_dir="custom-cache").classify("Texto").available
    assert caches == ["custom-cache"]
