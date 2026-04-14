from app.arbitrator import arbitrate, arbitrate_with_trace
from app.config import get_settings
from app.schemas import VerdictLabel


def test_arbitrate_returns_structured_verdict() -> None:
    result = arbitrate(
        prompt="Explain photosynthesis in two steps.",
        candidate_response=(
            "Photosynthesis uses sunlight to convert water and carbon dioxide "
            "into glucose and oxygen."
        ),
        settings=get_settings(),
    )

    assert result.request_id
    assert 0.0 <= result.verdict.overall_score <= 1.0
    assert result.verdict.label in {
        VerdictLabel.passed,
        VerdictLabel.review,
        VerdictLabel.fail,
    }
    assert len(result.verdict.critiques) == 3


def test_arbitrate_with_trace_includes_per_critic_metadata() -> None:
    result = arbitrate_with_trace(
        prompt="Explain photosynthesis in two steps.",
        candidate_response=(
            "Photosynthesis uses sunlight to convert water and carbon dioxide "
            "into glucose and oxygen."
        ),
        settings=get_settings(),
    )

    assert result.request_id
    assert len(result.verdict.critiques) == 3
    assert len(result.traces) == 3
    assert {t.dimension for t in result.traces} == {
        "factual_accuracy",
        "logical_consistency",
        "completeness",
    }
