from __future__ import annotations

import time
from typing import Any

from app.config import Settings
from app.openrouter import OpenRouterClient
from app.schemas import CriticTrace, CritiqueIssue, CritiqueReport, Severity


def _normalized_words(text: str, min_length: int = 5) -> set[str]:
    words = set()
    for raw_word in text.split():
        normalized = raw_word.strip(".,?!:;").lower()
        if len(normalized) >= min_length:
            words.add(normalized)
    return words


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

    prompt_words = _normalized_words(prompt)
    response_words = _normalized_words(response)

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


def _safe_issue(item: dict[str, Any]) -> CritiqueIssue:
    severity_raw = str(item.get("severity", "low")).lower()
    if severity_raw not in {"low", "medium", "high"}:
        severity_raw = "low"
    return CritiqueIssue(
        quote=str(item.get("quote", ""))[:300],
        description=str(item.get("description", "No description provided."))[:500],
        severity=Severity(severity_raw),
    )


def _parse_llm_report(
    llm_payload: dict[str, Any],
    critic_name: str,
    dimension: str,
    fallback_rationale: str,
) -> CritiqueReport:
    raw_score = llm_payload.get("score", 0.5)
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        score = 0.5
    score = min(1.0, max(0.0, score))

    raw_issues = llm_payload.get("issues", [])
    if not isinstance(raw_issues, list):
        raw_issues = []

    issues = [_safe_issue(item) for item in raw_issues if isinstance(item, dict)]
    rationale = str(llm_payload.get("rationale", fallback_rationale))

    return CritiqueReport(
        critic_name=critic_name,
        dimension=dimension,
        score=score,
        issues=issues,
        rationale=rationale,
    )


def run_critics(
    prompt: str,
    candidate_response: str,
    settings: Settings,
) -> list[CritiqueReport]:
    reports, _ = run_critics_with_trace(
        prompt=prompt,
        candidate_response=candidate_response,
        settings=settings,
    )
    return reports


def run_critics_with_trace(
    prompt: str,
    candidate_response: str,
    settings: Settings,
) -> tuple[list[CritiqueReport], list[CriticTrace]]:
    if not settings.openrouter_api_key:
        reports = [
            factual_accuracy_critic(prompt, candidate_response),
            logical_consistency_critic(prompt, candidate_response),
            completeness_critic(prompt, candidate_response),
        ]
        traces = [
            CriticTrace(
                critic_name=report.critic_name,
                dimension=report.dimension,
                model="heuristic",
                source="fallback_no_key",
                latency_ms=0.0,
                error=None,
            )
            for report in reports
        ]
        return reports, traces

    client = OpenRouterClient(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        app_name=settings.openrouter_app_name,
        site_url=settings.openrouter_site_url,
    )

    critics_config = [
        (
            "Factual Accuracy Critic",
            "factual_accuracy",
            settings.factual_model,
            factual_accuracy_critic,
            "Assesses claim correctness and factual grounding.",
        ),
        (
            "Logical Consistency Critic",
            "logical_consistency",
            settings.logical_model,
            logical_consistency_critic,
            "Assesses whether reasoning is coherent and non-contradictory.",
        ),
        (
            "Completeness Critic",
            "completeness",
            settings.completeness_model,
            completeness_critic,
            "Assesses whether the response fully addresses the prompt.",
        ),
    ]

    reports: list[CritiqueReport] = []
    traces: list[CriticTrace] = []
    for critic_name, dimension, model, fallback_fn, fallback_rationale in critics_config:
        started = time.perf_counter()
        source = "openrouter"
        error: str | None = None
        try:
            payload = client.critique(
                model=model,
                dimension=dimension,
                prompt=prompt,
                candidate_response=candidate_response,
            )
            report = _parse_llm_report(
                payload,
                critic_name=critic_name,
                dimension=dimension,
                fallback_rationale=fallback_rationale,
            )
        except Exception as exc:
            report = fallback_fn(prompt, candidate_response)
            source = "fallback_error"
            error = str(exc)[:300]
        reports.append(report)
        latency_ms = (time.perf_counter() - started) * 1000
        traces.append(
            CriticTrace(
                critic_name=critic_name,
                dimension=dimension,
                model=model,
                source=source,
                latency_ms=round(latency_ms, 2),
                error=error,
            )
        )

    return reports, traces
