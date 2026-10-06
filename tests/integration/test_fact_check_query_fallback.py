from news_analysis.article.extractor import ArticleExtractor
from news_analysis.pipeline.analyzer import NewsAnalyzer
from tests.conftest import FakeFetcher


class SequencedFactCheckClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.queries = []

    def search(self, query: str):
        self.queries.append(query)
        if self.responses:
            return self.responses.pop(0)
        return {"claims": []}


def test_fact_check_searches_claim_then_keywords(temp_settings, repository, long_article_html, sample_fact_check_response):
    fact_check_client = SequencedFactCheckClient([{"claims": []}, sample_fact_check_response])
    analyzer = NewsAnalyzer(
        temp_settings,
        repository,
        fetcher=FakeFetcher(long_article_html, final_url="https://93.184.216.34/article"),
        fact_check_client=fact_check_client,
        extractor=ArticleExtractor(min_characters=1000),
    )

    analysis = analyzer.analyze("https://93.184.216.34/article", claim="Vacina reduz os casos graves")

    assert analysis.criteria.verifiable_facts.available is True
    assert len(fact_check_client.queries) == 2
    assert fact_check_client.queries == ["Vacina reduz os casos graves", "vacina reduz casos graves"]
    assert analysis.criteria.verifiable_facts.target_claim == 'Vacina reduz os casos graves'
    assert analysis.criteria.verifiable_facts.additional_claims == []


def test_complementary_evidence_is_audited_without_changing_primary_score(temp_settings, repository, long_article_html, sample_fact_check_response):
    from tests.conftest import FakeFactCheckClient
    analyzer = NewsAnalyzer(temp_settings, repository, fetcher=FakeFetcher(long_article_html),
                            fact_check_client=FakeFactCheckClient(sample_fact_check_response))
    analysis = analyzer.analyze('https://93.184.216.34/article')
    criterion = analysis.criteria.verifiable_facts
    assert criterion.evidence_status == 'SUPPORTED'
    assert criterion.score == 1
    assert criterion.additional_claims
    assert all(item.score is None for item in criterion.additional_claims)
    stored = repository.get(analysis.id)['criteria']['verifiable_facts']
    assert stored['additional_claims'][0]['evidence_status'] == 'UNAVAILABLE'
    assert stored['additional_claims'][0]['reviews'][0]['exclusion_reason'] == 'claim_mismatch'
