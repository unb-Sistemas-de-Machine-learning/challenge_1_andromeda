from news_analysis.explanation.context import build_explanation_context
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
