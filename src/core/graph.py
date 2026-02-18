from __future__ import annotations

import logging
import json
from typing import Any

from langgraph.graph import END, StateGraph

from src.core.agents import AgentBundle
from src.core.state import MemDoc, ResearchState, Source
from src.memory.memory_manager import MemoryManager
from src.tools.fetch import FetchTool
from src.tools.search import DuckDuckGoSearchTool
from src.tools.utils import dedupe_urls


logger = logging.getLogger(__name__)


class DueDiligenceGraph:
    def __init__(
        self,
        agents: AgentBundle,
        memory_manager: MemoryManager,
        search_tool: DuckDuckGoSearchTool,
        fetch_tool: FetchTool,
    ) -> None:
        self.agents = agents
        self.memory_manager = memory_manager
        self.search_tool = search_tool
        self.fetch_tool = fetch_tool
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(ResearchState)
        workflow.add_node("planner", self.planner_node)
        workflow.add_node("search", self.search_node)
        workflow.add_node("retry_plan", self.retry_plan_node)
        workflow.add_node("fetch_clean", self.fetch_clean_node)
        workflow.add_node("memory_retrieve", self.memory_retrieve_node)
        workflow.add_node("analyst", self.analyst_node)
        workflow.add_node("writer", self.writer_node)
        workflow.add_node("memory_update", self.memory_update_node)

        workflow.set_entry_point("planner")
        workflow.add_edge("planner", "search")
        workflow.add_conditional_edges(
            "search",
            self.search_router,
            {"retry": "retry_plan", "continue": "fetch_clean"},
        )
        workflow.add_edge("retry_plan", "search")
        workflow.add_edge("fetch_clean", "memory_retrieve")
        workflow.add_edge("memory_retrieve", "analyst")
        workflow.add_edge("analyst", "writer")
        workflow.add_edge("writer", "memory_update")
        workflow.add_edge("memory_update", END)
        return workflow.compile()

    def planner_node(self, state: ResearchState) -> dict[str, Any]:
        queries = self.agents.planner(state["company"], state.get("focus", []), state.get("depth", "standard"))
        return {"query_plan": queries, "retry_count": 0}

    def search_node(self, state: ResearchState) -> dict[str, Any]:
        depth = state.get("depth", "standard")
        per_query = {"quick": 2, "standard": 3, "deep": 4}.get(depth, 3)

        found: list[Source] = []
        for query in state.get("query_plan", []):
            rows = self.search_tool.search(query, max_results=per_query)
            for row in rows:
                url = str(row.get("url", "")).strip()
                if not url:
                    continue
                found.append(Source(url=url, title=row.get("title", ""), snippet=row.get("snippet", ""), text=""))

        deduped_urls = dedupe_urls([s.url for s in found])
        deduped_sources: list[Source] = []
        first_by_url = {s.url: s for s in found}
        for url in deduped_urls:
            deduped_sources.append(first_by_url[url])

        return {"sources": deduped_sources}

    def search_router(self, state: ResearchState) -> str:
        min_sources = {"quick": 3, "standard": 5, "deep": 8}.get(state.get("depth", "standard"), 5)
        retry_count = int(state.get("retry_count", 0))
        source_count = len(state.get("sources", []))
        if source_count < min_sources and retry_count < 1:
            return "retry"
        return "continue"

    def retry_plan_node(self, state: ResearchState) -> dict[str, Any]:
        expanded = self.agents.expand_queries(state["company"], state.get("focus", []), state.get("query_plan", []))
        return {"query_plan": expanded, "retry_count": int(state.get("retry_count", 0)) + 1}

    def fetch_clean_node(self, state: ResearchState) -> dict[str, Any]:
        depth = state.get("depth", "standard")
        max_pages = {"quick": 5, "standard": 10, "deep": 15}.get(depth, 10)
        updated: list[Source] = []
        for source in state.get("sources", [])[:max_pages]:
            text = self.fetch_tool.fetch(source.url)
            if not text:
                continue
            updated.append(Source(url=source.url, title=source.title, snippet=source.snippet, text=text))
        return {"sources": updated}

    def memory_retrieve_node(self, state: ResearchState) -> dict[str, Any]:
        if not state.get("use_memory", True):
            return {"retrieved_memory": []}
        query = " ".join([state["company"]] + state.get("focus", []))
        rows = self.memory_manager.retrieve(query=query, company=state["company"], k=8)
        docs = [MemDoc(text=r["text"], score=r["score"], metadata=r["metadata"]) for r in rows]
        return {"retrieved_memory": docs}

    def analyst_node(self, state: ResearchState) -> dict[str, Any]:
        analysis = self.agents.analyst(
            company=state["company"],
            focus=state.get("focus", []),
            sources=state.get("sources", []),
            memory_docs=[d.model_dump() if hasattr(d, "model_dump") else d for d in state.get("retrieved_memory", [])],
        )
        return {"notes": json.dumps(analysis, ensure_ascii=True)}

    def writer_node(self, state: ResearchState) -> dict[str, Any]:
        try:
            analysis = json.loads(state.get("notes", "{}"))
            if not isinstance(analysis, dict):
                analysis = {}
        except Exception:
            analysis = {}
        report = self.agents.writer(
            company=state["company"],
            analysis=analysis,
            sources=state.get("sources", []),
            memory_used=bool(state.get("use_memory", True) and state.get("retrieved_memory")),
        )
        return {"report": report}

    def memory_update_node(self, state: ResearchState) -> dict[str, Any]:
        report = state["report"]
        sources = [s.model_dump() if hasattr(s, "model_dump") else s for s in state.get("sources", [])]
        added_docs = self.memory_manager.add_source_documents(state["company"], sources)
        bullets = [section.content[:220] for section in report.sections[:5]]
        added_summary = self.memory_manager.add_summary(state["company"], report.executive_summary, bullets)
        updates = {"added_docs": added_docs + added_summary, "added_sources": len(sources)}
        report.memory_updates = updates
        return {"report": report, "memory_updates": updates}

    def run(self, company: str, focus: list[str], depth: str, use_memory: bool) -> ResearchState:
        initial: ResearchState = {
            "company": company,
            "focus": focus,
            "depth": depth,
            "use_memory": use_memory,
            "query_plan": [],
            "sources": [],
            "retrieved_memory": [],
            "notes": "",
            "retry_count": 0,
            "memory_updates": {"added_docs": 0, "added_sources": 0},
        }
        result = self.graph.invoke(initial)
        logger.info("Graph completed for %s with %s sources", company, len(result.get("sources", [])))
        return result
