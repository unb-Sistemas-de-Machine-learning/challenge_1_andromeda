from datetime import datetime, timedelta, timezone

from news_analysis.criteria.credibility_config import CredibilityConfig
from news_analysis.criteria.source_credibility import SourceCredibility
from news_analysis.pipeline.analyzer import NewsAnalyzer
from tests.conftest import FakeFactCheckClient, FakeFetcher


def test_source_veto_persisted_without_overwriting_fact_check(tmp_path, temp_settings, repository, long_article_html, sample_fact_check_response):
    path = tmp_path / 'empty.json'
    path.write_text('[]')

    class Network:
        def creation_date(self, domain):
            return datetime.now(timezone.utc) - timedelta(days=10)

    source = SourceCredibility(CredibilityConfig(recognized_path=path, blocklist_path=path), Network())
    analyzer = NewsAnalyzer(temp_settings, repository,
                            fetcher=FakeFetcher(long_article_html, 'https://example.com/article'),
                            fact_check_client=FakeFactCheckClient(sample_fact_check_response),
                            source_credibility=source)
    analysis = analyzer.analyze('https://93.184.216.34/article')
    assert analysis.criteria.credibility['score_fonte'] == 5
    assert analysis.final.score == 35
    assert 'min(35' in analysis.final.formula
    stored = repository.get(analysis.id)
    assert stored['criteria']['credibility'] == analysis.criteria.credibility
    assert stored['criteria']['verifiable_facts']['available']
