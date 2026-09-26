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


def test_fact_check_falls_back_from_combined_query_to_title(temp_settings, repository, long_article_html, sample_fact_check_response):
    fact_check_client = SequencedFactCheckClient([{"claims": []}, sample_fact_check_response])
    analyzer = NewsAnalyzer(
        temp_settings,
        repository,
        fetcher=FakeFetcher(long_article_html, final_url="https://93.184.216.34/article"),
        fact_check_client=fact_check_client,
        extractor=ArticleExtractor(min_characters=1000),
    )

    analysis = analyzer.analyze("https://93.184.216.34/article")

    assert analysis.criteria.source_credibility.available is True
    assert len(fact_check_client.queries) == 2
    assert fact_check_client.queries[1] == "Vacina reduz casos graves"
