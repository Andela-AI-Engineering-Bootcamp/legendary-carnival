from app.security import is_api_key_valid


def test_api_key_validation_disabled_without_expected_key() -> None:
    assert is_api_key_valid(None, None)
    assert is_api_key_valid("anything", None)


def test_api_key_validation_requires_exact_match() -> None:
    expected = "super-secret"
    assert not is_api_key_valid(None, expected)
    assert not is_api_key_valid("wrong", expected)
    assert is_api_key_valid("super-secret", expected)
