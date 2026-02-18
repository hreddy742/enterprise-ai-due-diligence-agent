from __future__ import annotations

import logging
from pathlib import Path

from bs4 import BeautifulSoup
import requests

from src.tools.utils import cache_path, compact_whitespace


logger = logging.getLogger(__name__)


class FetchTool:
    def __init__(self, cache_dir: Path, timeout_seconds: int = 12, min_chars: int = 400, max_chars: int = 20000) -> None:
        self.cache_dir = cache_dir
        self.timeout_seconds = timeout_seconds
        self.min_chars = min_chars
        self.max_chars = max_chars
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _clean_html(self, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()
        text = soup.get_text(" ")
        text = compact_whitespace(text)
        return text[: self.max_chars]

    def fetch(self, url: str) -> str:
        path = cache_path(self.cache_dir, url)
        if path.exists():
            return path.read_text(encoding="utf-8")

        try:
            response = requests.get(
                url,
                timeout=self.timeout_seconds,
                headers={"User-Agent": "Mozilla/5.0 (DueDiligenceAgent/1.0)"},
            )
            if response.status_code >= 400:
                return ""
            cleaned = self._clean_html(response.text)
            if len(cleaned) < self.min_chars:
                return ""
            path.write_text(cleaned, encoding="utf-8")
            return cleaned
        except Exception as exc:
            logger.warning("Fetch failure for %s: %s", url, exc)
            return ""
