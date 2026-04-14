from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.arbitrator import arbitrate, arbitrate_with_trace
from app.config import get_settings
from app.rate_limit import InMemoryRateLimiter
from app.schemas import ArbitrationRequest, ArbitrationResponse, ArbitrationTraceResponse
from app.security import is_api_key_valid
from app.storage import Storage

app = FastAPI(title="LLM Output Arbitration System", version="0.1.0")
settings = get_settings()
storage = Storage(settings.database_url)
rate_limiter = InMemoryRateLimiter(
    requests=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window_seconds,
)

allow_all_origins = "*" in settings.cors_allow_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    if not is_api_key_valid(x_api_key, settings.api_access_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key.",
        )


def _require_rate_limit(request: Request, response: Response) -> None:
    client_ip = request.client.host if request.client else "unknown"
    result = rate_limiter.consume(client_ip)
    response.headers["X-RateLimit-Limit"] = str(result.limit)
    response.headers["X-RateLimit-Remaining"] = str(result.remaining)
    response.headers["X-RateLimit-Window-Seconds"] = str(result.window_seconds)

    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please retry later.",
            headers={
                "Retry-After": str(result.retry_after_seconds),
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": str(result.remaining),
                "X-RateLimit-Window-Seconds": str(result.window_seconds),
            },
        )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/arbitrate",
    response_model=ArbitrationResponse,
    dependencies=[Depends(_require_api_key), Depends(_require_rate_limit)],
)
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


@app.post(
    "/arbitrate/trace",
    response_model=ArbitrationTraceResponse,
    dependencies=[Depends(_require_api_key), Depends(_require_rate_limit)],
)
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
