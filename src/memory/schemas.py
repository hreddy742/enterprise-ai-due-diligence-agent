from __future__ import annotations

from pydantic import BaseModel, Field


class MemoryRecord(BaseModel):
    text: str
    company: str
    url: str | None = None
    title: str | None = None
    retrieved_at: str
    source_type: str = Field(default="web")
