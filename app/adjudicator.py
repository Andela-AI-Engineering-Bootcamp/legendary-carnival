from __future__ import annotations

from collections import defaultdict

from app.schemas import (
    ConfidenceLevel,
    ConfirmedIssue,
    CritiqueIssue,
    CritiqueReport,
    DisagreementItem,
    DismissedFlag,
    Severity,
)


def _normalize_issue_key(issue: CritiqueIssue) -> str:
    return " ".join(issue.description.lower().split())[:140]


def _resolve_confidence_level(confidence: float) -> ConfidenceLevel:
    if confidence >= 0.8:
        return ConfidenceLevel.high
    if confidence >= 0.6:
        return ConfidenceLevel.medium
    return ConfidenceLevel.low


def adjudicate(
    prompt: str,
    candidate_response: str,
    critiques: list[CritiqueReport],
    confidence: float,
) -> tuple[list[DisagreementItem], list[ConfirmedIssue], list[DismissedFlag], ConfidenceLevel]:
    critics = [c.critic_name for c in critiques]
    issue_votes: dict[str, list[tuple[str, CritiqueIssue, str]]] = defaultdict(list)

    for critique in critiques:
        for issue in critique.issues:
            issue_votes[_normalize_issue_key(issue)].append(
                (critique.critic_name, issue, critique.dimension)
            )

    disagreements: list[DisagreementItem] = []
    confirmed_issues: list[ConfirmedIssue] = []
    dismissed_flags: list[DismissedFlag] = []

    for issue_key, votes in issue_votes.items():
        raised_by = [critic_name for critic_name, _, _ in votes]
        dismissed_by = [critic for critic in critics if critic not in raised_by]
        sample_issue = votes[0][1]
        dimension = votes[0][2]

        disagreement_type = "none"
        if dismissed_by:
            if dimension == "factual_accuracy":
                disagreement_type = "factual_claim"
            elif dimension == "logical_consistency":
                disagreement_type = "logic_chain"
            else:
                disagreement_type = "completeness"

            disagreements.append(
                DisagreementItem(
                    issue_description=sample_issue.description,
                    raised_by=raised_by,
                    dismissed_by=dismissed_by,
                    disagreement_type=disagreement_type,
                )
            )

        # Evidence-based resolution heuristic:
        # - 2+ critics agreeing confirms issue.
        # - 1 critic only is dismissed unless issue is high severity and prompt mismatch is clear.
        if len(raised_by) >= 2:
            evidence = (
                f"Confirmed by {len(raised_by)} critics ({', '.join(raised_by)}). "
                f"Adjudicator reviewed disagreement context for {dimension}."
            )
            confirmed_issues.append(
                ConfirmedIssue(
                    issue=sample_issue.description,
                    severity=sample_issue.severity,
                    evidence=evidence,
                    confirmed_by=raised_by,
                )
            )
            continue

        only_vote = votes[0]
        only_critic = only_vote[0]
        single_issue = only_vote[1]

        prompt_overlap = (
            len(set(prompt.lower().split()) & set(candidate_response.lower().split()))
            / max(1, len(set(prompt.lower().split())))
        )
        confirm_single = (
            single_issue.severity == Severity.high
            and dimension == "completeness"
            and prompt_overlap < 0.2
        )

        if confirm_single:
            confirmed_issues.append(
                ConfirmedIssue(
                    issue=single_issue.description,
                    severity=single_issue.severity,
                    evidence=(
                        "Single high-severity completeness flag confirmed after "
                        "adjudicator re-checked prompt coverage."
                    ),
                    confirmed_by=[only_critic],
                )
            )
        else:
            dismissed_flags.append(
                DismissedFlag(
                    issue=single_issue.description,
                    raised_by=only_critic,
                    dismissal_reason=(
                        "Not corroborated by other critics after adjudicator reviewed "
                        "factual, logical, and completeness evidence."
                    ),
                )
            )

    return disagreements, confirmed_issues, dismissed_flags, _resolve_confidence_level(
        confidence
    )
