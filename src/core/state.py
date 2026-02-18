from __future__ import annotations

from typing import TypedDict

from pydantic import BaseModel, Field


class Citation(BaseModel):
    url: str
    title: str = ""
    snippet: str = ""


class Source(BaseModel):
    url: str
    title: str = ""
    snippet: str = ""
    text: str = ""


class MemDoc(BaseModel):
    text: str
    score: float
    metadata: dict = Field(default_factory=dict)


class ReportSection(BaseModel):
    title: str
    content: str
    citations: list[Citation] = Field(default_factory=list)


class Report(BaseModel):
    company: str
    generated_at: str
    executive_summary: str
    sections: list[ReportSection]
    memory_used: bool
    memory_updates: dict[str, int] = Field(default_factory=lambda: {"added_docs": 0, "added_sources": 0})


class ResearchState(TypedDict, total=False):
    company: str
    focus: list[str]
    depth: str
    use_memory: bool
    query_plan: list[str]
    sources: list[Source]
    retrieved_memory: list[MemDoc]
    notes: str
    report: Report
    retry_count: int
    memory_updates: dict[str, int]
