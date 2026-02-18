from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from apps.api.deps import get_app_settings, get_graph_runner
from apps.api.schemas import HealthResponse, ResearchRequest, ResearchResponse
from src.core.config import Settings
from src.core.graph import DueDiligenceGraph


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
def health(settings: Settings = Depends(get_app_settings)) -> HealthResponse:
    return HealthResponse(ok=True, service=settings.service_name)


@router.post("/research", response_model=ResearchResponse)
def research(
    payload: ResearchRequest,
    graph: DueDiligenceGraph = Depends(get_graph_runner),
) -> ResearchResponse:
    try:
        logger.info("Research request company=%s depth=%s focus=%s", payload.company, payload.depth, payload.focus)
        state = graph.run(
            company=payload.company,
            focus=payload.focus,
            depth=payload.depth,
            use_memory=payload.use_memory,
        )
        report = state.get("report")
        if report is None:
            raise HTTPException(status_code=500, detail="Failed to generate report")
        return ResearchResponse.model_validate(report.model_dump())
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Research pipeline failed")
        raise HTTPException(status_code=500, detail=f"Research pipeline failed: {exc}")
