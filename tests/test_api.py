from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.deps import get_graph_runner
from apps.api.main import app
from src.core.state import Citation, Report, ReportSection


class FakeGraph:
    def run(self, company: str, focus: list[str], depth: str, use_memory: bool):
        report = Report(
            company=company,
            generated_at="2026-01-01T00:00:00Z",
            executive_summary="Test summary",
            sections=[
                ReportSection(
                    title="Company Overview",
                    content="Overview",
                    citations=[Citation(url="https://example.com", title="Example", snippet="Snippet")],
                ),
                ReportSection(title="Business Model", content="Model", citations=[]),
                ReportSection(title="Revenue Streams", content="Revenue", citations=[]),
                ReportSection(title="Market", content="Market", citations=[]),
                ReportSection(title="Competitors", content="Competitors", citations=[]),
                ReportSection(title="SWOT", content="SWOT", citations=[]),
                ReportSection(title="Risks", content="Risks", citations=[]),
                ReportSection(title="Opportunities", content="Opportunities", citations=[]),
            ],
            memory_used=use_memory,
            memory_updates={"added_docs": 1, "added_sources": 1},
        )
        return {"report": report}


app.dependency_overrides[get_graph_runner] = lambda: FakeGraph()
client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True



def test_research():
    payload = {"company": "Stripe", "focus": ["pricing", "competitors"], "depth": "standard", "use_memory": True}
    resp = client.post("/research", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["company"] == "Stripe"
    assert len(body["sections"]) == 8
    assert "executive_summary" in body
