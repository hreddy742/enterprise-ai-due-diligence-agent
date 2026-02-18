from __future__ import annotations

import logging

from duckduckgo_search import DDGS


logger = logging.getLogger(__name__)


class DuckDuckGoSearchTool:
    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def search(self, query: str, max_results: int = 5) -> list[dict]:
        if not self.enabled:
            return []
        try:
            with DDGS() as ddgs:
                rows = ddgs.text(query, max_results=max_results)
                output: list[dict] = []
                for row in rows:
                    output.append(
                        {
                            "url": row.get("href", ""),
                            "title": row.get("title", ""),
                            "snippet": row.get("body", ""),
                        }
                    )
                return output
        except Exception as exc:
            logger.warning("Search failure for query '%s': %s", query, exc)
            return []
