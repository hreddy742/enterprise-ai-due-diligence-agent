from __future__ import annotations

from src.core.agents import AgentBundle, HeuristicClient
from src.core.graph import DueDiligenceGraph
from src.memory.memory_manager import MemoryManager
from src.rag.vectorstore import FaissVectorStore
from src.tools.fetch import FetchTool
from src.tools.search import DuckDuckGoSearchTool


class FakeSearch(DuckDuckGoSearchTool):
    def __init__(self) -> None:
        super().__init__(enabled=True)

    def search(self, query: str, max_results: int = 5) -> list[dict]:
        return [
            {
                "url": f"https://example.com/{abs(hash(query)) % 1000}",
                "title": "Example Source",
                "snippet": "Example snippet",
            }
        ]


class FakeFetch(FetchTool):
    def __init__(self) -> None:
        pass

    def fetch(self, url: str) -> str:
        return "Stripe is a financial infrastructure company serving businesses."



def test_graph_runs(tmp_path):
    vectorstore = FaissVectorStore(tmp_path / "faiss")
    memory = MemoryManager(vectorstore)
    graph = DueDiligenceGraph(
        agents=AgentBundle(llm=HeuristicClient()),
        memory_manager=memory,
        search_tool=FakeSearch(),
        fetch_tool=FakeFetch(),
    )

    out = graph.run(company="Stripe", focus=["pricing", "competitors"], depth="quick", use_memory=True)
    report = out.get("report")
    assert report is not None
    assert report.company == "Stripe"
    assert len(report.sections) == 8
