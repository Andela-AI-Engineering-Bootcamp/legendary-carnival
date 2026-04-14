from app.arbitrator import arbitrate
from app.schemas import VerdictLabel


def test_arbitrate_returns_structured_verdict() -> None:
    result = arbitrate(
        prompt="Explain photosynthesis in two steps.",
        candidate_response=(
            "Photosynthesis uses sunlight to convert water and carbon dioxide "
            "into glucose and oxygen."
        ),
    )

    assert result.request_id
    assert 0.0 <= result.verdict.overall_score <= 1.0
    assert result.verdict.label in {
        VerdictLabel.passed,
        VerdictLabel.review,
        VerdictLabel.fail,
    }
    assert len(result.verdict.critiques) == 3
