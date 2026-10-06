from news_analysis.explanation.service import build_explanation
from tests.unit.test_explanation import make_analysis


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
