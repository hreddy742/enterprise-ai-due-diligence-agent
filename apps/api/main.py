from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request

from apps.api.routes import router
from src.core.logging import configure_logging


configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Enterprise AI Due Diligence Agent", version="1.0.0")
app.include_router(router)


@app.middleware("http")
async def request_logging(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info("%s %s -> %s (%sms)", request.method, request.url.path, response.status_code, elapsed_ms)
    return response
