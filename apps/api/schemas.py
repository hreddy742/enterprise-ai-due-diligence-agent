from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CitationOut(BaseModel):
    url: str
    title: str = ""
    snippet: str = ""


class SectionOut(BaseModel):
    title: Literal[
        "Company Overview",
        "Business Model",
        "Revenue Streams",
        "Market",
        "Competitors",
        "SWOT",
        "Risks",
        "Opportunities",
    ]
    content: str
    citations: list[CitationOut] = Field(default_factory=list)


class ResearchRequest(BaseModel):
    company: str = Field(min_length=1)
    focus: list[str] = Field(default_factory=list)
    depth: Literal["quick", "standard", "deep"] = "standard"
    use_memory: bool = True


class MemoryUpdates(BaseModel):
    added_docs: int
    added_sources: int


class ResearchResponse(BaseModel):
    company: str
    generated_at: str
    executive_summary: str
    sections: list[SectionOut]
    memory_used: bool
    memory_updates: MemoryUpdates


class HealthResponse(BaseModel):
    ok: bool
    service: str
