from app.arbitrator import arbitrate
from app.config import get_settings
from app.storage import Storage


def test_storage_retrieval_and_analytics() -> None:
    storage = Storage("sqlite:///:memory:")
    result = arbitrate(
        prompt="Explain photosynthesis in two steps.",
        candidate_response=(
            "Photosynthesis uses sunlight to convert water and carbon dioxide "
            "into glucose and oxygen."
        ),
        settings=get_settings(),
    )
    storage.save(
        prompt="Explain photosynthesis in two steps.",
        candidate_response=(
            "Photosynthesis uses sunlight to convert water and carbon dioxide "
            "into glucose and oxygen."
        ),
        arbitration_response=result,
    )

    loaded = storage.get_by_request_id(result.request_id)
    assert loaded is not None
    assert loaded["request_id"] == result.request_id

    analytics = storage.get_analytics()
    assert analytics.total_arbitrations >= 1
