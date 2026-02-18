from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import logging
from typing import Any

from openai import OpenAI
import requests

from src.core.config import Settings
from src.core.state import Citation, Report, ReportSection, Source


logger = logging.getLogger(__name__)

SECTION_TITLES = [
    "Company Overview",
    "Business Model",
    "Revenue Streams",
    "Market",
    "Competitors",
    "SWOT",
    "Risks",
    "Opportunities",
]


class LLMClient:
    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        raise NotImplementedError


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return resp.choices[0].message.content or ""


class OllamaClient(LLMClient):
    def __init__(self, base_url: str, model: str, timeout_seconds: int = 60) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "options": {"temperature": temperature},
        }
        resp = requests.post(
            f"{self.base_url}/api/chat",
            json=payload,
            timeout=self.timeout_seconds,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("message", {}).get("content", "")


class HeuristicClient(LLMClient):
    def complete(self, system_prompt: str, user_prompt: str, temperature: float = 0.2) -> str:
        return "{}"



def build_llm_client(settings: Settings) -> LLMClient:
    if settings.openai_api_key:
        try:
            return OpenAIClient(settings.openai_api_key, settings.openai_model)
        except Exception as exc:
            logger.warning("Failed to initialize OpenAI client: %s", exc)
    try:
        return OllamaClient(settings.ollama_base_url, settings.ollama_model)
    except Exception as exc:
        logger.warning("Failed to initialize Ollama client: %s", exc)
    return HeuristicClient()



def safe_json_load(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except Exception:
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except Exception:
                return {}
        return {}


@dataclass
class AgentBundle:
    llm: LLMClient

    def planner(self, company: str, focus: list[str], depth: str) -> list[str]:
        target_count = {"quick": 4, "standard": 8, "deep": 12}.get(depth, 8)
        sys_prompt = (
            "You are a due diligence planning agent. Return only valid JSON with key 'queries' containing a list of search queries."
        )
        user_prompt = (
            f"Company: {company}\n"
            f"Focus: {focus}\n"
            f"Depth: {depth}\n"
            f"Need exactly {target_count} focused queries across business model, pricing, financials, competitors, market, risks."
        )
        queries: list[str] = []
        try:
            data = safe_json_load(self.llm.complete(sys_prompt, user_prompt))
            queries = [str(q).strip() for q in data.get("queries", []) if str(q).strip()]
        except Exception as exc:
            logger.warning("Planner model call failed: %s", exc)

        if not queries:
            base = [
                f"{company} company overview",
                f"{company} business model",
                f"{company} pricing",
                f"{company} competitors",
                f"{company} market share",
                f"{company} risks",
                f"{company} SWOT analysis",
                f"{company} latest news",
                f"{company} customer segments",
                f"{company} revenue streams",
                f"{company} regulatory risks",
                f"{company} growth opportunities",
            ]
            focus_queries = [f"{company} {f}" for f in focus]
            queries = focus_queries + base

        deduped: list[str] = []
        seen: set[str] = set()
        for q in queries:
            qn = q.lower()
            if qn in seen:
                continue
            seen.add(qn)
            deduped.append(q)
        return deduped[:target_count]

    def expand_queries(self, company: str, focus: list[str], existing: list[str]) -> list[str]:
        extra = [
            f"{company} annual report",
            f"{company} investor relations",
            f"{company} pricing page",
            f"{company} competitive landscape",
            f"{company} litigation regulatory filing",
        ] + [f"{company} {f} analysis" for f in focus]
        merged = existing + [q for q in extra if q.lower() not in {e.lower() for e in existing}]
        return merged

    def analyst(
        self,
        company: str,
        focus: list[str],
        sources: list[Source],
        memory_docs: list[dict],
    ) -> dict[str, Any]:
        source_rows = [
            {
                "url": s.url,
                "title": s.title,
                "snippet": s.snippet,
                "excerpt": s.text[:500],
            }
            for s in sources[:25]
        ]
        sys_prompt = (
            "You are an enterprise due diligence analyst. Use only provided evidence. "
            "If evidence is weak, include '[Not fully confirmed]'. Return strict JSON only."
        )
        user_prompt = json.dumps(
            {
                "company": company,
                "focus": focus,
                "required_sections": SECTION_TITLES,
                "sources": source_rows,
                "memory": memory_docs[:8],
                "format": {
                    "executive_summary": "string",
                    "sections": [
                        {
                            "title": "one of required_sections",
                            "content": "markdown text",
                            "citation_urls": ["url1", "url2"],
                        }
                    ],
                },
            },
            ensure_ascii=True,
        )

        parsed: dict[str, Any] = {}
        try:
            parsed = safe_json_load(self.llm.complete(sys_prompt, user_prompt))
        except Exception as exc:
            logger.warning("Analyst model call failed: %s", exc)

        if parsed.get("sections"):
            return parsed

        fallback_sections = []
        default_urls = [s.url for s in sources[:3] if s.url]
        for title in SECTION_TITLES:
            fallback_sections.append(
                {
                    "title": title,
                    "content": f"[Not fully confirmed] Limited evidence available for {title.lower()} for {company}.",
                    "citation_urls": default_urls,
                }
            )
        return {
            "executive_summary": f"[Not fully confirmed] Automated due diligence draft for {company} generated from limited available evidence.",
            "sections": fallback_sections,
        }

    def writer(
        self,
        company: str,
        analysis: dict[str, Any],
        sources: list[Source],
        memory_used: bool,
    ) -> Report:
        source_map = {s.url: s for s in sources if s.url}
        built_sections: list[ReportSection] = []

        raw_sections = analysis.get("sections", [])
        by_title = {str(s.get("title", "")).strip(): s for s in raw_sections if isinstance(s, dict)}
        for title in SECTION_TITLES:
            row = by_title.get(title, {})
            content = str(row.get("content", "")).strip() or f"[Not fully confirmed] No strong evidence found for {title.lower()}."
            citation_urls = [str(u) for u in row.get("citation_urls", []) if str(u)]
            citations: list[Citation] = []
            for url in citation_urls:
                src = source_map.get(url)
                if not src:
                    continue
                citations.append(Citation(url=src.url, title=src.title, snippet=src.snippet[:320]))
            built_sections.append(ReportSection(title=title, content=content, citations=citations))

        summary = str(analysis.get("executive_summary", "")).strip()
        if not summary:
            summary = f"[Not fully confirmed] Due diligence summary for {company} generated with incomplete context."

        return Report(
            company=company,
            generated_at=datetime.now(timezone.utc).isoformat(),
            executive_summary=summary,
            sections=built_sections,
            memory_used=memory_used,
            memory_updates={"added_docs": 0, "added_sources": 0},
        )
