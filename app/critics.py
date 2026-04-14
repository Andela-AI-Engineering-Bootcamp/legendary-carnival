from __future__ import annotations

from app.schemas import CritiqueIssue, CritiqueReport, Severity


def factual_accuracy_critic(prompt: str, response: str) -> CritiqueReport:
    issues: list[CritiqueIssue] = []
    lower = response.lower()

    if "always" in lower or "never" in lower:
        issues.append(
            CritiqueIssue(
                quote="always/never",
                description="Absolute claim may be unreliable without supporting evidence.",
                severity=Severity.medium,
            )
        )

    if "according to" not in lower and "source" not in lower:
        issues.append(
            CritiqueIssue(
                quote=response[:80],
                description="No source signal or grounding marker found in response.",
                severity=Severity.low,
            )
        )

    score = max(0.0, 1.0 - (0.2 * len(issues)))
    return CritiqueReport(
        critic_name="Factual Accuracy Critic",
        dimension="factual_accuracy",
        score=score,
        issues=issues,
        rationale="Checks for unsupported absolutes and grounding cues.",
    )


def logical_consistency_critic(prompt: str, response: str) -> CritiqueReport:
    issues: list[CritiqueIssue] = []
    lower = response.lower()

    contradiction_pairs = [
        ("always", "except"),
        ("must", "optional"),
        ("cannot", "can"),
    ]
    for a, b in contradiction_pairs:
        if a in lower and b in lower:
            issues.append(
                CritiqueIssue(
                    quote=f"{a} ... {b}",
                    description="Potential internal contradiction detected.",
                    severity=Severity.high,
                )
            )

    if "because" in lower and "therefore" not in lower and len(response.split(".")) >= 3:
        issues.append(
            CritiqueIssue(
                quote=response[:100],
                description="Reasoning is present but conclusion signal is weak.",
                severity=Severity.low,
            )
        )

    score = max(0.0, 1.0 - (0.25 * len(issues)))
    return CritiqueReport(
        critic_name="Logical Consistency Critic",
        dimension="logical_consistency",
        score=score,
        issues=issues,
        rationale="Checks contradiction patterns and reasoning flow coherence.",
    )


def completeness_critic(prompt: str, response: str) -> CritiqueReport:
    issues: list[CritiqueIssue] = []

    prompt_words = {w.strip(".,?!:;").lower() for w in prompt.split() if len(w) > 4}
    response_words = {w.strip(".,?!:;").lower() for w in response.split()}

    if prompt_words:
        overlap_ratio = len(prompt_words & response_words) / len(prompt_words)
    else:
        overlap_ratio = 1.0

    if overlap_ratio < 0.25:
        issues.append(
            CritiqueIssue(
                quote=response[:90],
                description="Low topic overlap with prompt suggests missing coverage.",
                severity=Severity.high,
            )
        )

    if len(response.split()) < 20:
        issues.append(
            CritiqueIssue(
                quote=response,
                description="Response is brief and may skip important parts.",
                severity=Severity.medium,
            )
        )

    score = max(0.0, 1.0 - (0.3 * len(issues)))
    return CritiqueReport(
        critic_name="Completeness Critic",
        dimension="completeness",
        score=score,
        issues=issues,
        rationale="Checks topical coverage and minimum answer depth.",
    )
