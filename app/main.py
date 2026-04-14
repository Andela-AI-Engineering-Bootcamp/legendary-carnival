from __future__ import annotations

from fastapi import FastAPI

from app.arbitrator import arbitrate, arbitrate_with_trace
from app.config import get_settings
from app.schemas import ArbitrationRequest, ArbitrationResponse, ArbitrationTraceResponse
from app.storage import Storage

app = FastAPI(title="LLM Output Arbitration System", version="0.1.0")
storage = Storage()
settings = get_settings()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/arbitrate", response_model=ArbitrationResponse)
def run_arbitration(request: ArbitrationRequest) -> ArbitrationResponse:
    result = arbitrate(
        prompt=request.prompt,
        candidate_response=request.candidate_response,
        settings=settings,
    )
    storage.save(
        prompt=request.prompt,
        candidate_response=request.candidate_response,
        arbitration_response=result,
    )
    return result


@app.post("/arbitrate/trace", response_model=ArbitrationTraceResponse)
def run_arbitration_with_trace(request: ArbitrationRequest) -> ArbitrationTraceResponse:
    result = arbitrate_with_trace(
        prompt=request.prompt,
        candidate_response=request.candidate_response,
        settings=settings,
    )
    storage.save(
        prompt=request.prompt,
        candidate_response=request.candidate_response,
        arbitration_response=ArbitrationResponse(
            request_id=result.request_id,
            verdict=result.verdict,
        ),
    )
    return result
