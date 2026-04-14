from __future__ import annotations

import uuid
from statistics import mean

from app.config import Settings
from app.critics import run_critics, run_critics_with_trace
from app.schemas import (
    ArbitrationResponse,
    ArbitrationTraceResponse,
    ArbitrationVerdict,
    CritiqueReport,
    VerdictLabel,
)


def _label_for_score(score: float) -> VerdictLabel:
    if score >= 0.8:
        return VerdictLabel.passed
    if score >= 0.55:
        return VerdictLabel.review
    return VerdictLabel.fail


def _build_verdict(critiques: list[CritiqueReport]) -> ArbitrationVerdict:
    overall_score = mean([c.score for c in critiques]) if critiques else 0.0
    label = _label_for_score(overall_score)
    confidence = min(1.0, max(0.0, 0.6 + (overall_score - 0.5)))

    issue_count = sum(len(c.issues) for c in critiques)
    summary = (
        f"{label.value.upper()} with {issue_count} flagged issue(s). "
        f"Average critic score: {overall_score:.2f}."
    )

    return ArbitrationVerdict(
        label=label,
        confidence=confidence,
        overall_score=overall_score,
        summary=summary,
        critiques=critiques,
    )


def arbitrate(
    prompt: str,
    candidate_response: str,
    settings: Settings,
) -> ArbitrationResponse:
    critiques = run_critics(
        prompt=prompt,
        candidate_response=candidate_response,
        settings=settings,
    )
    verdict = _build_verdict(critiques)
    return ArbitrationResponse(request_id=str(uuid.uuid4()), verdict=verdict)


def arbitrate_with_trace(
    prompt: str,
    candidate_response: str,
    settings: Settings,
) -> ArbitrationTraceResponse:
    critiques, traces = run_critics_with_trace(
        prompt=prompt,
        candidate_response=candidate_response,
        settings=settings,
    )
    verdict = _build_verdict(critiques)
    return ArbitrationTraceResponse(
        request_id=str(uuid.uuid4()),
        verdict=verdict,
        traces=traces,
    )
