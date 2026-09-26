import pytest

from news_analysis.article.extractor import ArticleExtractor
from news_analysis.pipeline.errors import AnalysisError, AnalysisStatus


def test_article_extractor_requires_minimum_main_text():
    extractor = ArticleExtractor(min_characters=1000)
    with pytest.raises(AnalysisError) as exc:
        extractor.extract("<html><title>T</title><body>curto</body></html>", "https://example.com")
    assert exc.value.status == AnalysisStatus.ARTICLE_EXTRACTION_FAILED


def test_article_extractor_returns_metadata_and_hash(long_article_html):
    result = ArticleExtractor(min_characters=1000).extract(long_article_html, "https://example.com/news")
    assert result.article.extracted_character_count >= 1000
    assert result.article.content_hash
    assert result.article.title == "Vacina reduz casos graves"
