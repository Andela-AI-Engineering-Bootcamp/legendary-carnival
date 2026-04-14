from __future__ import annotations

import uuid
from statistics import mean

from app.critics import (
    completeness_critic,
    factual_accuracy_critic,
    logical_consistency_critic,
)
from app.schemas import ArbitrationResponse, ArbitrationVerdict, VerdictLabel


def _label_for_score(score: float) -> VerdictLabel:
    if score >= 0.8:
        return VerdictLabel.passed
    if score >= 0.55:
        return VerdictLabel.review
    return VerdictLabel.fail


def arbitrate(prompt: str, candidate_response: str) -> ArbitrationResponse:
    critiques = [
        factual_accuracy_critic(prompt, candidate_response),
        logical_consistency_critic(prompt, candidate_response),
        completeness_critic(prompt, candidate_response),
    ]

    overall_score = mean([c.score for c in critiques]) if critiques else 0.0
    label = _label_for_score(overall_score)
    confidence = min(1.0, max(0.0, 0.6 + (overall_score - 0.5)))

    issue_count = sum(len(c.issues) for c in critiques)
    summary = (
        f"{label.value.upper()} with {issue_count} flagged issue(s). "
        f"Average critic score: {overall_score:.2f}."
    )

    verdict = ArbitrationVerdict(
        label=label,
        confidence=confidence,
        overall_score=overall_score,
        summary=summary,
        critiques=critiques,
    )
    return ArbitrationResponse(request_id=str(uuid.uuid4()), verdict=verdict)
