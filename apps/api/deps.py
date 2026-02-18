from __future__ import annotations

from functools import lru_cache

from src.core.agents import AgentBundle, build_llm_client
from src.core.config import Settings, get_settings
from src.core.graph import DueDiligenceGraph
from src.memory.memory_manager import MemoryManager
from src.rag.vectorstore import FaissVectorStore
from src.tools.fetch import FetchTool
from src.tools.search import DuckDuckGoSearchTool


@lru_cache(maxsize=1)
def get_app_settings() -> Settings:
    return get_settings()


@lru_cache(maxsize=1)
def get_graph_runner() -> DueDiligenceGraph:
    settings = get_app_settings()
    llm = build_llm_client(settings)
    agents = AgentBundle(llm=llm)
    vectorstore = FaissVectorStore(settings.faiss_dir)
    memory = MemoryManager(vectorstore)
    search_tool = DuckDuckGoSearchTool(enabled=settings.enable_web_search)
    fetch_tool = FetchTool(
        cache_dir=settings.cache_dir,
        timeout_seconds=settings.fetch_timeout_seconds,
        min_chars=settings.min_clean_chars,
        max_chars=settings.max_fetch_chars,
    )
    return DueDiligenceGraph(
        agents=agents,
        memory_manager=memory,
        search_tool=search_tool,
        fetch_tool=fetch_tool,
    )
