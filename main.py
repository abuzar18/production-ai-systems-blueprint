from __future__ import annotations

import json
import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from domain import SourceDocument
from pipeline import run_workflow


logger = logging.getLogger("production_ai_blueprint")
logging.basicConfig(level=logging.INFO, format="%(message)s")


class DocumentInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    source_id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=20_000)


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=5, max_length=1_000)
    documents: list[DocumentInput] = Field(min_length=1, max_length=50)


class CitationOutput(BaseModel):
    source_id: str
    title: str
    score: float


class AnalyzeResponse(BaseModel):
    request_id: str
    status: str
    answer: str
    citations: list[CitationOutput]
    trace: list[str]


@asynccontextmanager
async def lifespan(_: FastAPI):
    logger.info(json.dumps({"event": "service_started"}))
    yield
    logger.info(json.dumps({"event": "service_stopped"}))


app = FastAPI(
    title="Production AI Systems Blueprint",
    version="1.0.0",
    description="A verifiable, evidence-backed AI workflow reference implementation.",
    lifespan=lifespan,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict[str, str]:
    return {"status": "ready"}


@app.post("/v1/analyze", response_model=AnalyzeResponse)
def analyze(
    payload: AnalyzeRequest,
    response: Response,
    x_request_id: str | None = Header(default=None),
) -> AnalyzeResponse:
    request_id = x_request_id or str(uuid.uuid4())
    response.headers["X-Request-ID"] = request_id
    started = time.perf_counter()

    documents = [
        SourceDocument(
            source_id=document.source_id,
            title=document.title,
            text=document.text,
        )
        for document in payload.documents
    ]

    try:
        result = run_workflow(payload.question, documents, request_id=request_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    duration_ms = round((time.perf_counter() - started) * 1_000, 2)
    logger.info(
        json.dumps(
            {
                "event": "workflow_completed",
                "request_id": request_id,
                "status": result.status.value,
                "duration_ms": duration_ms,
                "citation_count": len(result.citations),
            }
        )
    )

    return AnalyzeResponse(
        request_id=result.request_id,
        status=result.status.value,
        answer=result.answer,
        citations=[
            CitationOutput(
                source_id=citation.source_id,
                title=citation.title,
                score=citation.score,
            )
            for citation in result.citations
        ],
        trace=result.trace,
    )

