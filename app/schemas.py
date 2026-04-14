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


class ConfidenceLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class ArbitrationRequest(BaseModel):
    prompt: str = Field(min_length=1)
    candidate_response: str = Field(min_length=1)


class BatchArbitrationRequest(BaseModel):
    items: List[ArbitrationRequest] = Field(min_length=1)


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


class DisagreementItem(BaseModel):
    issue_description: str
    raised_by: List[str] = Field(default_factory=list)
    dismissed_by: List[str] = Field(default_factory=list)
    disagreement_type: str


class ConfirmedIssue(BaseModel):
    issue: str
    severity: Severity
    evidence: str
    confirmed_by: List[str] = Field(default_factory=list)


class DismissedFlag(BaseModel):
    issue: str
    raised_by: str
    dismissal_reason: str


class ArbitrationVerdict(BaseModel):
    label: VerdictLabel
    confidence: float = Field(ge=0.0, le=1.0)
    overall_score: float = Field(ge=0.0, le=1.0)
    overall_quality_score_10: float = Field(ge=1.0, le=10.0)
    confidence_level: ConfidenceLevel
    summary: str
    critiques: List[CritiqueReport]
    disagreements: List[DisagreementItem] = Field(default_factory=list)
    confirmed_issues: List[ConfirmedIssue] = Field(default_factory=list)
    dismissed_flags: List[DismissedFlag] = Field(default_factory=list)


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


class BatchArbitrationResponse(BaseModel):
    results: List[ArbitrationResponse]


class BatchSummaryRow(BaseModel):
    request_id: str
    output_excerpt: str
    overall_score: float = Field(ge=0.0, le=1.0)
    overall_quality_score_10: float = Field(ge=1.0, le=10.0)
    issue_count: int = Field(ge=0)
    confidence: float = Field(ge=0.0, le=1.0)


class AnalyticsResponse(BaseModel):
    total_arbitrations: int = Field(ge=0)
    issues_by_critic: dict[str, int] = Field(default_factory=dict)
    overruled_by_critic: dict[str, int] = Field(default_factory=dict)
    failure_types: dict[str, int] = Field(default_factory=dict)
    critic_agreement_rate: float = Field(ge=0.0, le=1.0)
