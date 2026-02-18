from __future__ import annotations

from datetime import datetime, timezone

from src.memory.schemas import MemoryRecord
from src.rag.chunking import chunk_text
from src.rag.vectorstore import FaissVectorStore


class MemoryManager:
    def __init__(self, vectorstore: FaissVectorStore) -> None:
        self.vectorstore = vectorstore

    def retrieve(self, query: str, company: str, k: int = 6) -> list[dict]:
        results = self.vectorstore.similarity_search(query=query, k=k, company=company)
        return [
            {"text": r.text, "score": r.score, "metadata": r.metadata}
            for r in results
        ]

    def add_source_documents(self, company: str, sources: list[dict]) -> int:
        texts: list[str] = []
        metas: list[dict] = []
        now = datetime.now(timezone.utc).isoformat()
        for source in sources:
            for chunk in chunk_text(source.get("text", "")):
                record = MemoryRecord(
                    text=chunk,
                    company=company,
                    url=source.get("url"),
                    title=source.get("title"),
                    retrieved_at=now,
                    source_type="web",
                )
                texts.append(record.text)
                metas.append(record.model_dump(exclude={"text"}))
        return self.vectorstore.add_documents(texts, metas)

    def add_summary(self, company: str, summary: str, bullets: list[str]) -> int:
        now = datetime.now(timezone.utc).isoformat()
        texts = [summary] + bullets
        metas = [
            MemoryRecord(
                text=t,
                company=company,
                url=None,
                title="Analyst summary",
                retrieved_at=now,
                source_type="summary",
            ).model_dump(exclude={"text"})
            for t in texts
            if t and t.strip()
        ]
        real_texts = [t for t in texts if t and t.strip()]
        return self.vectorstore.add_documents(real_texts, metas)
