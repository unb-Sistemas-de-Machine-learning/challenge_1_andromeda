"""Synthetic regressions from the reported wording, not a live API fixture."""
import pytest

from news_analysis.criteria.claim_matching import match_claims
from news_analysis.criteria.fact_check import build_fact_check_queries, evaluate_fact_checks
from news_analysis.criteria.rating_normalization import normalize_rating

TARGET = 'Lula diz que ser lixeiro não dá orgulho: “Coisa pobre”'
PARAPHRASE = 'Lula diz que gari é profissão pobre e que não dá orgulho'


@pytest.mark.parametrize('checked', [
    PARAPHRASE,
    'Lula afirmou que trabalhar como gari é uma profissão pobre e que não proporciona orgulho',
    'Lula disse que ser gari não traz orgulho: coisa pobre',
])
def test_reported_paraphrases_are_strong_matches(checked):
    match = match_claims(TARGET, checked)
    assert match.applicable
    assert match.classification == 'SAME_CLAIM'
    assert match.similarity >= .8


@pytest.mark.parametrize('checked', [
    'Foto mostra garis com cartazes contra Lula',
    'Lula diz que gari é profissão rica e que dá orgulho',
    'Bolsonaro diz que gari é profissão pobre e que não dá orgulho',
    'Lula não disse que ser lixeiro dá orgulho: coisa pobre',
    'Lula diz que lixeiro é uma coisa pobre',
    'É falso que Lula diz que ser lixeiro não dá orgulho: coisa pobre',
    'Lula diz que ser lixeiro não dá orgulho: coisa pobre em 2020',
    'Lixeiro é uma coisa pobre',
])
def test_related_topics_incomplete_quotes_and_changed_propositions_do_not_score(checked):
    assert not match_claims(TARGET, checked).applicable


def test_queries_use_controlled_synonyms_without_modifying_original_target():
    queries = build_fact_check_queries(TARGET, '')
    assert queries[0] == TARGET
    assert 'gari' in queries[1]
    assert 'nao' in queries[1]


def raw_review(claim, rating, site, **extra):
    return {'text': claim, 'claimReview': [dict(publisher={'site': site}, url=f'https://{site}/1',
                                             textualRating=rating, **extra)]}


def test_same_related_and_context_verdicts_are_auditable_and_scored_separately():
    raw = {'claims': [raw_review(PARAPHRASE, 'Fora de contexto', 'a.example'),
                      raw_review(TARGET, 'Enganoso', 'b.example'),
                      raw_review('Foto mostra garis com cartazes contra Lula', 'Falso', 'c.example')]}
    result = evaluate_fact_checks(raw, TARGET, '', TARGET)
    assert result.available
    assert result.score == .25
    assert result.applicable_reviews_count == result.scored_reviews_count == 2
    assert result.related_reviews_count == 1
    assert result.reviews[0].rating_interpretation == 'CONTEXT'
    assert result.reviews[0].textual_rating == 'Fora de contexto'
    assert result.reviews[0].normalized_target and result.reviews[0].normalized_claim
    assert result.reviews[0].matcher_version
    assert result.reviews[2].exclusion_reason == 'claim_related'
    assert not result.reviews[2].included_in_score


def test_rating_or_review_headline_cannot_turn_an_unrelated_claim_into_a_match():
    raw = {'claims': [raw_review('Foto mostra garis com cartazes contra Lula', 'Falso', 'a.example', title=TARGET)]}
    result = evaluate_fact_checks(raw, TARGET, '', TARGET)
    assert result.score is None
    assert result.related_reviews_count == 1
    assert result.error.details['reason'] == 'related_reviews_only'


def test_missing_claim_text_is_not_replaced_with_headline_or_non_api_fields():
    raw = {'claims': [raw_review(None, None, 'a.example', title=TARGET, text=TARGET,
                               reviewRating={'alternateName': 'Falso', 'numericRating': 0})]}
    result = evaluate_fact_checks(raw, TARGET, '', TARGET)
    assert result.score is None
    assert result.reviews[0].match_reason == 'missing_claim_text'
    assert result.reviews[0].normalized_value is None


def test_matched_unmapped_rating_does_not_look_like_absence_of_matching_reviews():
    result = evaluate_fact_checks({'claims': [raw_review(PARAPHRASE, 'Escala desconhecida', 'a.example')]}, TARGET, '', TARGET)
    assert result.applicable_reviews_count == 1
    assert result.evidence_status == 'MATCHED_UNSCORED'
    assert result.score is None and not result.available


@pytest.mark.parametrize('label', ['Fora de contexto', 'DESCONTEXTUALIZADO', 'Out of context'])
def test_exact_context_labels_have_documented_local_mapping(label):
    assert normalize_rating(label) == .25
    assert normalize_rating('Não está ' + label) is None
