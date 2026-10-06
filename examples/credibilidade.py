"""Offline, fictitious examples: python examples/credibilidade.py."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from news_analysis.criteria.credibility_config import CredibilityConfig
from news_analysis.criteria.source_credibility import SourceCredibility


class DemoNetwork:
    """Explicit fixtures, never evidence about real publishers."""
    def fetch(self, url: str) -> tuple[str, str]:
        body = '<meta name="author" content="Autora fictícia"><time datetime="2026-01-01"/><a href="/contato">Contato</a>'
        return body, url

    def creation_date(self, domain: str) -> datetime:
        return datetime.now(timezone.utc) - timedelta(days=3000)


if __name__ == '__main__':
    with TemporaryDirectory() as directory:
        recognized, blocked = Path(directory) / 'recognized.json', Path(directory) / 'blocked.json'
        recognized.write_text('["jornal.example.com"]')
        blocked.write_text('["boato.example.org"]')
        scorer = SourceCredibility(CredibilityConfig(recognized_path=recognized, blocklist_path=blocked), DemoNetwork())
        for url, expected in [('https://jornal.example.com/noticia', 80), ('https://portal.example.net/noticia', 45), ('https://boato.example.org/noticia', 0)]:
            result = scorer.calculate(url)
            assert result['score_fonte'] == expected
            print(json.dumps(result, ensure_ascii=False, indent=2))
