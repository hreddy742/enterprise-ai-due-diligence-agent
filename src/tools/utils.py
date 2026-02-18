from __future__ import annotations

from hashlib import md5
from pathlib import Path
import re



def dedupe_urls(urls: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for url in urls:
        normalized = (url or "").strip().rstrip("/")
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        out.append(normalized)
    return out



def cache_key(url: str) -> str:
    return md5(url.encode("utf-8")).hexdigest()



def cache_path(cache_dir: Path, url: str) -> Path:
    return cache_dir / f"{cache_key(url)}.txt"



def compact_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()
