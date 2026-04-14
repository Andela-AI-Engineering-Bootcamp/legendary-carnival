from __future__ import annotations

from typing import TypedDict

from app.adjudicator import adjudicate
from app.critics import run_critics_with_trace
from app.schemas import CritiqueReport


class ArbitrationState(TypedDict):
    prompt: str
    candidate_response: str
    critiques: list[CritiqueReport]


def run_pipeline(prompt: str, candidate_response: str, settings) -> tuple:
    critiques, traces = run_critics_with_trace(
        prompt=prompt,
        candidate_response=candidate_response,
        settings=settings,
    )
    disagreements, confirmed_issues, dismissed_flags, confidence_level = adjudicate(
        prompt=prompt,
        candidate_response=candidate_response,
        critiques=critiques,
        confidence=0.5,
    )
    return critiques, traces, disagreements, confirmed_issues, dismissed_flags, confidence_level
