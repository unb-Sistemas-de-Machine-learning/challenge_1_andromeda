from news_analysis.criteria.source_credibility import evaluate_source_credibility
from news_analysis.pipeline.models import Article


def test_source_credibility_scores_observable_metadata():
    article = Article(
        original_url="https://news.example/article",
        final_url="https://news.example/article",
        canonical_url="https://news.example/article",
        publisher="News Example",
        title="Noticia",
        author="Reporter",
        published_at="2026-01-01",
        content_hash="abc",
        extracted_character_count=1000,
    )
    result = evaluate_source_credibility(article)
    assert result.available is True
    assert result.status == "EXECUTED"
    assert result.score == 1
    assert result.intended_weight == 0.2
    assert all(signal.passed for signal in result.signals)
