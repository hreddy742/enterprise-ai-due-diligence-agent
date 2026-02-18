from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    service_name: str = "enterprise-ai-due-diligence-agent"
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    request_timeout_seconds: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))
    fetch_timeout_seconds: int = int(os.getenv("FETCH_TIMEOUT_SECONDS", "12"))
    max_fetch_chars: int = int(os.getenv("MAX_FETCH_CHARS", "20000"))
    min_clean_chars: int = int(os.getenv("MIN_CLEAN_CHARS", "400"))
    enable_web_search: bool = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"
    data_dir: Path = Path(os.getenv("DATA_DIR", "data"))
    faiss_dir: Path = Path(os.getenv("FAISS_DIR", "data/faiss_index"))
    cache_dir: Path = Path(os.getenv("CACHE_DIR", "data/cache"))



def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.faiss_dir.mkdir(parents=True, exist_ok=True)
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
    return settings
