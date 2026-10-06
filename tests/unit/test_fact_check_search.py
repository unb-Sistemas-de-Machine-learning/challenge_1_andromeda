import httpx
import pytest

from news_analysis.criteria.fact_check import FactCheckClient, build_fact_check_queries, evaluate_fact_checks, is_applicable_fact_check
from news_analysis.criteria.fact_check_search import run_fact_check_search, select_claim_candidates


DF = 'DF retoma vacinação contra Covid-19 para adultos após chegada de doses'


def response(claim, rating='Verdadeiro', site='a.example'):
    return {'claims': [{'text': claim, 'claimReview': [
        {'publisher': {'site': site}, 'textualRating': rating, 'url': f'https://{site}/review'}]}]}


class Client:
    def __init__(self, *responses):
        self.responses = iter(responses)
        self.queries = []

    def search(self, query):
        self.queries.append(query)
        value = next(self.responses, {'claims': []})
        if isinstance(value, Exception):
            raise value
        return value


def test_df_query_is_short_and_does_not_duplicate_headline_or_body():
    queries = build_fact_check_queries(DF, DF + '. O Distrito Federal recebeu novas doses.')
    assert queries[0] == DF
    assert len(queries) <= 2
    assert all('recebeu' not in query for query in queries)
    assert queries[1].startswith('df ')
    assert len(queries[1].split()) <= 10


def test_candidates_preserve_original_sentences_and_explicit_claim_priority():
    text = DF + '. O Distrito Federal recebeu novas doses de vacina. As UBSs retomaram os atendimentos. Outra frase não deve ser selecionada.'
    candidates = select_claim_candidates(DF + ' | Jornal', text)
    assert candidates == [(DF, 'article_title'), ('O Distrito Federal recebeu novas doses de vacina.', 'article_sentence'),
                          ('As UBSs retomaram os atendimentos.', 'article_sentence')]
    assert select_claim_candidates(DF, text, 'Vacina não causa autismo') == [('Vacina não causa autismo', 'user')]
    assert select_claim_candidates('Vacina funciona?', 'Uma vacina reduz casos graves.') == [
        ('Uma vacina reduz casos graves.', 'article_sentence')]


def test_search_combines_divergent_evidence_instead_of_stopping_at_first_result():
    target = 'Vacina reduz os casos graves'
    client = Client(response(target), response(target, 'Falso', 'b.example'))
    result = run_fact_check_search(client, None, '', target)
    assert len(client.queries) == 2
    assert result.evidence_status == 'MIXED'
    assert result.score == .5
    assert result.publishers_count == 2
    assert result.conflicting_verdicts
    assert len(result.search_attempts) == 2


def test_duplicate_across_queries_is_retained_but_not_counted_twice():
    target = 'Vacina reduz os casos graves'
    client = Client(response(target), response(target))
    result = run_fact_check_search(client, None, '', target)
    assert result.score == 1
    assert result.reviews_count == 2
    assert result.scored_reviews_count == 1
    assert result.reviews[1].exclusion_reason == 'duplicate_review'


def test_later_failure_does_not_erase_successful_evidence_or_leak_exception_text():
    target = 'Vacina reduz os casos graves'
    result = run_fact_check_search(Client(response(target), httpx.ReadTimeout('secret API key')), None, '', target)
    assert result.available and result.score == 1
    assert result.evidence_status == 'SUPPORTED'
    assert result.status == 'EXECUTED'
    assert result.search_incomplete
    assert result.search_attempts[-1]['status'] == 'error'
    assert 'secret API key' not in result.model_dump_json()


def test_all_failed_searches_are_error_without_a_score():
    result = run_fact_check_search(Client(httpx.ConnectError('offline'), httpx.ConnectError('offline')), None, '',
                                  'Vacina reduz os casos graves')
    assert result.status == 'ERROR'
    assert result.evidence_status == 'UNAVAILABLE'
    assert result.score is None and not result.available


def test_malformed_later_response_cannot_destroy_valid_evidence():
    target = 'Vacina reduz os casos graves'
    result = run_fact_check_search(Client(response(target), {'claims': [42]}), None, '', target)
    assert result.available and result.score == 1
    assert result.search_incomplete
    assert result.search_attempts[-1]['status'] == 'error'


def test_missing_key_stops_before_secondary_claims():
    client = Client({'claims': [], 'unavailable_reason': 'missing_api_key'})
    result = run_fact_check_search(client, DF, 'O Distrito Federal recebeu novas doses de vacina.')
    assert len(client.queries) == 1
    assert result.error.details['reason'] == 'missing_api_key'
    assert result.additional_claims == []


def test_additional_claims_do_not_replace_unavailable_primary_or_enter_its_score():
    primary = 'Vacina reduz casos graves'
    additional = 'Hospitais recebem novos equipamentos.'
    result = run_fact_check_search(Client({'claims': []}, response(additional)), primary, additional)
    assert result.target_claim == primary
    assert result.score is None
    assert result.evidence_status == 'UNAVAILABLE'
    assert result.additional_claims[0].evidence_status == 'SUPPORTED'
    assert result.additional_claims[0].score == 1
    assert 'intended_weight' not in result.additional_claims[0].model_dump()


@pytest.mark.parametrize('rating,state', [('Verdadeiro', 'SUPPORTED'), ('Falso', 'REFUTED'),
                                         ('Meia verdade', 'MIXED'), ('rótulo desconhecido', 'MATCHED_UNSCORED')])
def test_evidence_summary_uses_only_usable_ratings(rating, state):
    result = evaluate_fact_checks(response(DF, rating), DF, '', DF)
    assert result.evidence_status == state


def test_matching_preserves_locality_numbers_negation_and_direction():
    assert is_applicable_fact_check(DF, DF.replace('DF', 'Distrito Federal'), None)
    assert is_applicable_fact_check(DF, DF.lower(), None)
    assert is_applicable_fact_check(DF, DF.replace('DF', 'O Distrito Federal').replace('retoma', 'retomou'), None)
    assert not is_applicable_fact_check(DF, DF.replace('DF', 'SP'), None)
    assert not is_applicable_fact_check(DF, DF.replace('retoma', 'suspende'), None)
    assert not is_applicable_fact_check(DF, DF.replace('retoma', 'não retoma'), None)
    assert not is_applicable_fact_check(DF + ' em 2026', DF + ' em 2020', None)


def test_failed_second_page_preserves_first_page_and_reports_incomplete_search(temp_settings):
    calls = []
    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(200, json={**response(DF), 'nextPageToken': 'next'})
        return httpx.Response(503)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        result = FactCheckClient(temp_settings, client).search(DF)
    assert len(result['claims']) == 1
    assert result['search_incomplete']
    assert result['search_errors'][0]['http_status'] == 503


def test_request_budget_is_at_most_six_queries_for_three_candidates():
    client = Client()
    run_fact_check_search(client, DF, 'O Distrito Federal recebeu novas doses. As UBSs retomaram os atendimentos.')
    assert len(client.queries) <= 6


def test_authorization_failure_stops_requests_and_sanitizes_secrets():
    request = httpx.Request('GET', 'https://example.com?key=secret')
    error = httpx.HTTPStatusError('secret', request=request, response=httpx.Response(403, request=request))
    client = Client(error)
    result = run_fact_check_search(client, DF, 'O Distrito Federal recebeu novas doses.')
    assert len(client.queries) == 1
    assert result.status == 'ERROR'
    assert 'secret' not in result.model_dump_json()
