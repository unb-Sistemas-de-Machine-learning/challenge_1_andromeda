from news_analysis.article.extractor import ArticleExtractor
from news_analysis.pipeline.analyzer import NewsAnalyzer
from tests.conftest import FakeFactCheckClient, FakeFetcher


def test_repository_saves_and_retrieves_without_full_text(temp_settings, repository, long_article_html, sample_fact_check_response, long_article_text):
    analyzer = NewsAnalyzer(
        temp_settings,
        repository,
        fetcher=FakeFetcher(long_article_html),
        fact_check_client=FakeFactCheckClient(sample_fact_check_response),
        extractor=ArticleExtractor(min_characters=1000),
    )
    analysis = analyzer.analyze("https://93.184.216.34/article")
    stored = repository.get(analysis.id)
    serialized = str(stored)
    assert stored["pipeline_version"]["id"]
    assert stored["article"]["content_hash"]
    assert long_article_text not in serialized
    assert "main_text" not in serialized


def test_legacy_records_are_readable_without_rescoring(temp_settings, repository, long_article_html, sample_fact_check_response):
    import json
    from news_analysis.pipeline.models import Analysis
    analyzer = NewsAnalyzer(temp_settings, repository, fetcher=FakeFetcher(long_article_html), fact_check_client=FakeFactCheckClient(sample_fact_check_response))
    result = analyzer.analyze("https://93.184.216.34/article")
    payload = repository.get(result.id)
    payload["criteria"].pop("source_credibility")
    payload["criteria"]["source_credibility"] = payload["criteria"].pop("verifiable_facts")
    payload["pipeline_version"]["rules_version"] = "legacy-rules"
    for key in ("intended_weights", "effective_weights"):
        weights = payload["final"][key]
        weights["source_credibility"] = weights.pop("verifiable_facts")
    from contextlib import closing
    with closing(repository._connect()) as connection:
        connection.execute("UPDATE analyses SET payload_json=? WHERE id=?", (json.dumps(payload), result.id))
        connection.commit()
    restored = repository.get(result.id)
    assert restored["final"]["score"] == payload["final"]["score"]
    assert restored["pipeline_version"]["rules_version"] == "legacy-rules"
    assert "not recalculated" in restored["criteria"]["verifiable_facts"]["scope"]
    Analysis.model_validate(restored)
