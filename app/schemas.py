from __future__ import annotations

from enum import Enum
from typing import List

from pydantic import BaseModel, Field


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class VerdictLabel(str, Enum):
    passed = "pass"
    review = "review"
    fail = "fail"


class ArbitrationRequest(BaseModel):
    prompt: str = Field(min_length=1)
    candidate_response: str = Field(min_length=1)


class CritiqueIssue(BaseModel):
    quote: str
    description: str
    severity: Severity


class CritiqueReport(BaseModel):
    critic_name: str
    dimension: str
    score: float = Field(ge=0.0, le=1.0)
    issues: List[CritiqueIssue] = Field(default_factory=list)
    rationale: str


class ArbitrationVerdict(BaseModel):
    label: VerdictLabel
    confidence: float = Field(ge=0.0, le=1.0)
    overall_score: float = Field(ge=0.0, le=1.0)
    summary: str
    critiques: List[CritiqueReport]


class ArbitrationResponse(BaseModel):
    request_id: str
    verdict: ArbitrationVerdict


class CriticTrace(BaseModel):
    critic_name: str
    dimension: str
    model: str
    source: str
    latency_ms: float = Field(ge=0.0)
    error: str | None = None


class ArbitrationTraceResponse(BaseModel):
    request_id: str
    verdict: ArbitrationVerdict
    traces: List[CriticTrace]
