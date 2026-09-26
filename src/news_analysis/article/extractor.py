from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from html import unescape

from news_analysis.pipeline.errors import AnalysisError, AnalysisStatus
from news_analysis.pipeline.models import Article


@dataclass
class ExtractedArticle:
    article: Article
    main_text: str


class ArticleExtractor:
    def __init__(self, min_characters: int = 1000):
        self.min_characters = min_characters

    def extract(self, html: str, original_url: str, final_url: str | None = None) -> ExtractedArticle:
        title, text, metadata = _extract_with_trafilatura(html, original_url)
        if not text:
            title = title or _extract_title(html)
            text = _fallback_text(html)
        character_count = len(text)
        if character_count < self.min_characters:
            raise AnalysisError(
                AnalysisStatus.ARTICLE_EXTRACTION_FAILED,
                "Fewer than 1,000 characters of main article text were extracted.",
                retryable=False,
                details={"extracted_character_count": character_count, "minimum": self.min_characters},
            )
        content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        article = Article(
            original_url=original_url,
            final_url=final_url or original_url,
            canonical_url=metadata.get("canonical_url"),
            publisher=metadata.get("publisher"),
            title=title,
            subtitle=metadata.get("subtitle"),
            author=metadata.get("author"),
            published_at=metadata.get("published_at"),
            content_hash=content_hash,
            extracted_character_count=character_count,
        )
        return ExtractedArticle(article=article, main_text=text)


def _extract_with_trafilatura(html: str, url: str) -> tuple[str | None, str | None, dict[str, str | None]]:
    try:
        import trafilatura
        from trafilatura.metadata import extract_metadata
    except Exception:
        return None, None, {}

    text = trafilatura.extract(html, url=url, include_comments=False, include_tables=False)
    metadata: dict[str, str | None] = {}
    try:
        extracted = extract_metadata(html)
        if extracted:
            metadata = {
                "publisher": extracted.sitename,
                "title": extracted.title,
                "subtitle": extracted.description,
                "author": extracted.author,
                "published_at": extracted.date,
                "canonical_url": extracted.url,
            }
    except Exception:
        metadata = {}
    return metadata.get("title"), text, metadata


def _extract_title(html: str) -> str | None:
    match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return unescape(_strip_tags(match.group(1))).strip() or None


def _fallback_text(html: str) -> str:
    body = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    body = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</h[1-6]>", "\n", body)
    return unescape(_strip_tags(body)).strip()


def _strip_tags(value: str) -> str:
    return re.sub(r"<[^>]+>", " ", value).replace("\xa0", " ")
