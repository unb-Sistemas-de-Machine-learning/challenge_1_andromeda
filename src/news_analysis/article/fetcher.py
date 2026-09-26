from __future__ import annotations

import httpx

from news_analysis.config import Settings
from news_analysis.pipeline.errors import AnalysisError, AnalysisStatus


class ArticleFetcher:
    def __init__(self, settings: Settings, client: httpx.Client | None = None):
        self.settings = settings
        self.client = client

    def fetch(self, url: str) -> tuple[str, str]:
        close_client = self.client is None
        client = self.client or httpx.Client(
            timeout=self.settings.fetch_timeout_seconds,
            follow_redirects=True,
            max_redirects=self.settings.max_redirects,
            headers={"User-Agent": "challenge-1-andromeda/0.1"},
        )
        try:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                if len(response.history) > self.settings.max_redirects:
                    raise AnalysisError(
                        AnalysisStatus.NEWS_FETCH_FAILED,
                        "Redirect limit exceeded while fetching article.",
                        retryable=False,
                    )
                chunks: list[bytes] = []
                downloaded = 0
                for chunk in response.iter_bytes():
                    downloaded += len(chunk)
                    if downloaded > self.settings.max_download_bytes:
                        raise AnalysisError(
                            AnalysisStatus.NEWS_FETCH_FAILED,
                            "Article download exceeded the 5 MB safety limit.",
                            retryable=False,
                            details={"max_download_bytes": self.settings.max_download_bytes},
                        )
                    chunks.append(chunk)
                return b"".join(chunks).decode(response.encoding or "utf-8", errors="replace"), str(response.url)
        except AnalysisError:
            raise
        except httpx.TimeoutException as exc:
            raise AnalysisError(
                AnalysisStatus.NEWS_FETCH_FAILED,
                "Article fetch exceeded the 10-second timeout.",
                retryable=True,
            ) from exc
        except httpx.TooManyRedirects as exc:
            raise AnalysisError(
                AnalysisStatus.NEWS_FETCH_FAILED,
                "Redirect limit exceeded while fetching article.",
                retryable=False,
            ) from exc
        except httpx.HTTPError as exc:
            raise AnalysisError(
                AnalysisStatus.NEWS_FETCH_FAILED,
                "Article could not be fetched.",
                retryable=True,
                details={"reason": exc.__class__.__name__},
            ) from exc
        finally:
            if close_client:
                client.close()
