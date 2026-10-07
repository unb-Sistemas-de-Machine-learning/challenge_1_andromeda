from dataclasses import replace

from news_analysis.explanation.service import build_explanation
from tests.unit.test_explanation import make_analysis


class FailingEngine:
    def prepare(self):
        raise AssertionError("The public summary must not load the SML model")

    def generate(self, context):
        raise AssertionError("The public summary must not publish an SML draft")


def test_summary_is_available_even_when_sml_is_disabled(temp_settings):
    result = build_explanation(make_analysis(), temp_settings, FailingEngine())
    assert result.status == "SUCCESS"
    assert result.engine is None
    assert result.validation == "FALLBACK"
    assert result.text.startswith("Confiabilidade baixíssima.")
    assert "SML" not in result.text


def test_enabled_sml_does_not_replace_audited_summary(temp_settings):
    result = build_explanation(make_analysis(), replace(temp_settings, explanation_sml_enabled=True), FailingEngine())
    assert result.status == "SUCCESS"
    assert result.text == build_explanation(make_analysis(), temp_settings).text


def test_writing_only_summary_explains_missing_fact_checks(temp_settings):
    analysis = make_analysis("UNAVAILABLE", coverage=40)
    analysis.final.score = 86.1
    result = build_explanation(analysis, temp_settings)
    assert result.text.startswith("Confiabilidade alta.")
    assert "Não há checagem factual disponível" in result.text
    assert "A avaliação considera apenas o estilo de escrita" in result.text
    assert "não confirma os fatos" in result.text
    assert "86" not in result.text


def test_unavailable_recognition_is_not_presented_as_negative(temp_settings):
    analysis = make_analysis()
    analysis.criteria.credibility["criterios"] = [
        {"nome": "veiculo_reconhecido", "status": "indisponivel"},
        {"nome": "tld_institucional", "status": "neutro"},
    ]
    result = build_explanation(analysis, temp_settings)
    assert "o veículo desta notícia não pôde ser consultado na base de veículos" in result.text
    assert "Pontos negativos encontrados" not in result.text
