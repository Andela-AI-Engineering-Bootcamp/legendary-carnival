from __future__ import annotations

from fastapi import FastAPI

from app.arbitrator import arbitrate
from app.schemas import ArbitrationRequest, ArbitrationResponse
from app.storage import Storage

app = FastAPI(title="LLM Output Arbitration System", version="0.1.0")
storage = Storage()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/arbitrate", response_model=ArbitrationResponse)
def run_arbitration(request: ArbitrationRequest) -> ArbitrationResponse:
    result = arbitrate(
        prompt=request.prompt,
        candidate_response=request.candidate_response,
    )
    storage.save(
        prompt=request.prompt,
        candidate_response=request.candidate_response,
        arbitration_response=result,
    )
    return result
