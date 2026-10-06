from news_analysis.explanation.service import build_explanation
from tests.unit.test_explanation import make_analysis
from dataclasses import replace
from types import SimpleNamespace

from news_analysis.explanation import service


class FakeEngine:
    model_id = "fake/sml"
    model_revision = "test"

    def __init__(self, text):
        self.text = text

    def generate(self, context):
        return self.text


def test_sml_is_not_loaded_when_disabled(temp_settings):
    analysis = make_analysis()
    result = build_explanation(analysis, temp_settings, engine=FakeEngine("unused"))
    assert result.engine == "sml"
    assert result.status == "UNAVAILABLE"
    assert result.error_code == "sml_disabled"


def test_valid_sml_output_uses_same_contract(temp_settings):
    temp_settings = temp_settings.__class__(**{**temp_settings.__dict__, "explanation_sml_enabled": True})
    result = build_explanation(analysis=make_analysis(), settings=temp_settings, engine=FakeEngine(
        "A checagem encontrou avaliações contrárias para a afirmação. A cobertura foi parcial."
    ))
    assert result.engine == "sml"
    assert result.model_id == "fake/sml"
    assert result.validation == "VALID"


def test_invalid_sml_output_falls_back(temp_settings):
    temp_settings = temp_settings.__class__(**{**temp_settings.__dict__, "explanation_sml_enabled": True})
    result = build_explanation(make_analysis(), temp_settings, FakeEngine("A nota foi 999%. https://bad.example"))
    assert result.engine == "sml"
    assert result.status == "ERROR"
    assert result.validation == "REJECTED"
    assert result.text is None


def test_cold_loading_is_not_charged_to_the_generation_budget(temp_settings, monkeypatch):
    elapsed = [0.0]

    class ColdEngine(FakeEngine):
        def prepare(self):
            elapsed[0] += 30.0

        def generate(self, context):
            elapsed[0] += 1.5
            return self.text

    monkeypatch.setattr(service, "time", SimpleNamespace(perf_counter=lambda: elapsed[0]))
    result = build_explanation(
        make_analysis(), replace(temp_settings, explanation_sml_enabled=True),
        ColdEngine("A checagem encontrou avaliações contrárias para a afirmação. A cobertura foi parcial."),
    )
    assert result.status == "SUCCESS"
    assert result.generated_ms == 1500


def test_engine_timeout_is_explicit_and_does_not_return_partial_text(temp_settings):
    class SlowEngine(FakeEngine):
        def generate(self, context):
            raise TimeoutError("sml_timeout")

    result = build_explanation(
        make_analysis(), replace(temp_settings, explanation_sml_enabled=True), SlowEngine("partial"),
    )
    assert result.status == "ERROR"
    assert result.error_code == "sml_timeout"
    assert result.text is None
    assert result.generated_ms is not None


def test_slow_injected_engine_keeps_post_generation_timeout(temp_settings, monkeypatch):
    clock = iter([0.0, 0.0, 9.0])
    monkeypatch.setattr(service, "time", SimpleNamespace(perf_counter=lambda: next(clock)))
    result = build_explanation(
        make_analysis(), replace(temp_settings, explanation_sml_enabled=True), FakeEngine("unused"),
    )
    assert result.error_code == "sml_timeout"
    assert result.generated_ms == 9000
    assert result.text is None


def test_service_passes_configured_timeout_to_default_engine(temp_settings, monkeypatch):
    def factory(**kwargs):
        assert kwargs["timeout_seconds"] == 1.25
        return FakeEngine("A checagem encontrou avaliações contrárias para a afirmação. A cobertura foi parcial.")

    monkeypatch.setattr(service, "FlanT5SmallEngine", factory)
    result = build_explanation(
        make_analysis(), replace(temp_settings, explanation_sml_enabled=True, explanation_timeout_seconds=1.25),
    )
    assert result.status == "SUCCESS"
