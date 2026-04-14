from __future__ import annotations

import uuid
from statistics import mean

from app.adjudicator import adjudicate
from app.config import Settings
from app.critics import run_critics, run_critics_with_trace
from app.schemas import (
    ArbitrationResponse,
    ArbitrationTraceResponse,
    ArbitrationVerdict,
    ConfidenceLevel,
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
    overall_quality_score_10 = max(1.0, min(10.0, round(overall_score * 10, 2)))

    issue_count = sum(len(c.issues) for c in critiques)
    summary = (
        f"{label.value.upper()} with {issue_count} flagged issue(s). "
        f"Average critic score: {overall_score:.2f}."
    )

    return ArbitrationVerdict(
        label=label,
        confidence=confidence,
        overall_score=overall_score,
        overall_quality_score_10=overall_quality_score_10,
        confidence_level=ConfidenceLevel.medium,
        summary=summary,
        critiques=critiques,
        disagreements=[],
        confirmed_issues=[],
        dismissed_flags=[],
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
    disagreements, confirmed_issues, dismissed_flags, confidence_level = adjudicate(
        prompt=prompt,
        candidate_response=candidate_response,
        critiques=critiques,
        confidence=verdict.confidence,
    )
    verdict.overall_quality_score_10 = overall_quality_score_10 = max(
        1.0, min(10.0, round(verdict.overall_score * 10, 2))
    )
    verdict.confidence_level = confidence_level
    verdict.disagreements = disagreements
    verdict.confirmed_issues = confirmed_issues
    verdict.dismissed_flags = dismissed_flags
    verdict.summary = (
        f"Quality score {overall_quality_score_10}/10 with {len(confirmed_issues)} confirmed "
        f"issue(s) and {len(dismissed_flags)} dismissed flag(s). "
        f"Adjudicator reviewed disagreements across critics."
    )
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
    disagreements, confirmed_issues, dismissed_flags, confidence_level = adjudicate(
        prompt=prompt,
        candidate_response=candidate_response,
        critiques=critiques,
        confidence=verdict.confidence,
    )
    overall_quality_score_10 = max(1.0, min(10.0, round(verdict.overall_score * 10, 2)))
    verdict.overall_quality_score_10 = overall_quality_score_10
    verdict.confidence_level = confidence_level
    verdict.disagreements = disagreements
    verdict.confirmed_issues = confirmed_issues
    verdict.dismissed_flags = dismissed_flags
    verdict.summary = (
        f"Quality score {overall_quality_score_10}/10 with {len(confirmed_issues)} confirmed "
        f"issue(s) and {len(dismissed_flags)} dismissed flag(s). "
        f"Adjudicator reviewed disagreements across critics."
    )
    return ArbitrationTraceResponse(
        request_id=str(uuid.uuid4()),
        verdict=verdict,
        traces=traces,
    )
