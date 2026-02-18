from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json

import faiss
import numpy as np

from src.rag.embeddings import get_embedding_model


@dataclass
class SearchResult:
    text: str
    score: float
    metadata: dict


class FaissVectorStore:
    def __init__(self, index_dir: Path, embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2") -> None:
        self.index_dir = index_dir
        self.index_path = self.index_dir / "index.faiss"
        self.meta_path = self.index_dir / "metadata.jsonl"
        self.model = get_embedding_model(embedding_model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata: list[dict] = []
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._load()

    def _load(self) -> None:
        if self.index_path.exists() and self.meta_path.exists():
            self.index = faiss.read_index(str(self.index_path))
            self.metadata = []
            for line in self.meta_path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    self.metadata.append(json.loads(line))

    def save(self) -> None:
        faiss.write_index(self.index, str(self.index_path))
        with self.meta_path.open("w", encoding="utf-8") as f:
            for record in self.metadata:
                f.write(json.dumps(record, ensure_ascii=True) + "\n")

    def add_documents(self, texts: list[str], metadatas: list[dict]) -> int:
        clean_pairs = [(t.strip(), m) for t, m in zip(texts, metadatas) if t and t.strip()]
        if not clean_pairs:
            return 0
        emb = self.model.encode([p[0] for p in clean_pairs], normalize_embeddings=True)
        vectors = np.array(emb, dtype=np.float32)
        self.index.add(vectors)
        for text, meta in clean_pairs:
            entry = {"text": text, **meta}
            self.metadata.append(entry)
        self.save()
        return len(clean_pairs)

    def similarity_search(self, query: str, k: int = 5, company: str | None = None) -> list[SearchResult]:
        if self.index.ntotal == 0 or not query.strip():
            return []
        q_emb = self.model.encode([query], normalize_embeddings=True)
        q_vec = np.array(q_emb, dtype=np.float32)
        distances, indices = self.index.search(q_vec, max(k * 3, k))
        out: list[SearchResult] = []
        for score, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue
            meta = self.metadata[idx]
            if company and str(meta.get("company", "")).lower() != company.lower():
                continue
            out.append(SearchResult(text=meta.get("text", ""), score=float(score), metadata=meta))
            if len(out) >= k:
                break
        return out
