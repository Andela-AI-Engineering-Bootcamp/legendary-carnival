from __future__ import annotations


def is_api_key_valid(provided_key: str | None, expected_key: str | None) -> bool:
    if not expected_key:
        return True
    return bool(provided_key) and provided_key == expected_key
