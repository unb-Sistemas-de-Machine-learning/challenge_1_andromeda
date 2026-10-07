from news_analysis.explanation.context import _confidence_band, build_explanation_context
from news_analysis.explanation.prompt import build_fallback_text, build_prompt
from news_analysis.explanation.validation import validate_explanation
from news_analysis.pipeline.aggregation import aggregate_final_score
from news_analysis.pipeline.models import (
    Analysis,
    CriteriaSet,
    FactCheckCriterionResult,
    PipelineVersion,
    WritingStyleCriterionResult,
)


def make_analysis(evidence_status="REFUTED", coverage=100):
    fact = FactCheckCriterionResult(
        available=evidence_status != "UNAVAILABLE",
        status="EXECUTED" if evidence_status != "UNAVAILABLE" else "UNAVAILABLE",
        score=0.2 if evidence_status != "UNAVAILABLE" else None,
        target_claim="A afirmação selecionada",
        evidence_status=evidence_status,
        reviews_count=2,
        applicable_reviews_count=1,
        publishers_count=1,
        query="A afirmação selecionada",
        reviews=[],
    )
    writing = WritingStyleCriterionResult(
        available=True,
        status="EXECUTED",
        score=0.7,
        model_version="test",
        segments_analyzed=1,
        segments=[],
        qualitative_state="poucas_boas_praticas",
        limitation="sinal de estilo",
    )
    final = aggregate_final_score(fact.score, writing.score)
    final.coverage = coverage
    return Analysis(
        id="analysis-test",
        status="SUCCESS",
        input={"url": "https://example.com"},
        criteria=CriteriaSet(verifiable_facts=fact, writing_style=writing, credibility={
            "score_fonte": 80,
            "confianca_fonte": "alta",
            "veto_dominio_suspeito": False,
            "flags": [],
            "erros": [],
        }),
        final=final,
        pipeline_version=PipelineVersion(
            id="test", rules_version="test", fact_check_mapping_version="test",
            writing_model_name="test", dependency_versions={},
        ),
        limitations=["limitação de teste"],
    )


def test_context_is_compact_and_keeps_explicit_fact_state():
    context = build_explanation_context(make_analysis())
    assert context.fact_check.evidence_status == "REFUTED"
    assert context.fact_check.target_claim == "A afirmação selecionada"
    assert context.source.veto_applied is False
    assert len(context.fact_check.target_claim) <= 240


def test_validator_rejects_new_numbers_and_unavailable_verdict():
    context = build_explanation_context(make_analysis("UNAVAILABLE", coverage=40))
    assert validate_explanation("A nota foi 999% e a afirmação foi confirmada.", context)[0] is False
    assert validate_explanation("A análise tem cobertura parcial e não encontrou evidência factual utilizável para a afirmação selecionada.", context)[0] is True


def test_confidence_band_boundaries():
    assert [_confidence_band(score) for score in (40, 40.01, 70, 70.01, 85, 86)] == [
        "baixíssima", "baixa", "baixa", "média", "média", "alta",
    ]


def test_source_explanation_uses_human_terms_and_neutral_tld():
    analysis = make_analysis()
    analysis.criteria.credibility["criterios"] = [
        {"nome": "veiculo_reconhecido", "status": "indisponivel", "detalhe": "Base ausente"},
        {"nome": "tld_institucional", "status": "neutro", "detalhe": "TLD não institucional"},
    ]
    context = build_explanation_context(analysis)
    summary = build_fallback_text(context)
    assert "o veículo desta notícia não pôde ser consultado na base de veículos" in summary
    assert "Pontos negativos encontrados" not in summary
    assert "tld" not in summary.lower()
    assert "nota 40" not in build_prompt(context)

    analysis.criteria.credibility["dominio"] = "portal.gov.br"
    analysis.criteria.credibility["criterios"][1]["status"] = "ok"
    context = build_explanation_context(analysis)
    assert "o site verificado é um site oficial do governo" in build_fallback_text(context)

    analysis.criteria.credibility["criterios"][0]["status"] = "negativo"
    context = build_explanation_context(analysis)
    assert "Pontos negativos encontrados: o veículo desta notícia não foi encontrado nas bases de veículos consultadas." in build_fallback_text(context)


def test_validator_rejects_cut_off_and_numeric_score():
    context = build_explanation_context(make_analysis())
    assert validate_explanation("Confiabilidade baixa. Há evidências contrárias ao fato analisado. Fonte: complet", context)[1] == "incomplete"
    assert validate_explanation("A confiabilidade é baixa, com nota 40. Há evidências contrárias ao fato analisado.", context)[1] == "numeric_score"
