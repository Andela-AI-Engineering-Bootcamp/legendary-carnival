from __future__ import annotations

import json
from typing import Any

import httpx


class OpenRouterClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        app_name: str,
        site_url: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.app_name = app_name
        self.site_url = site_url
        self.timeout_seconds = timeout_seconds

    def critique(
        self,
        model: str,
        dimension: str,
        prompt: str,
        candidate_response: str,
    ) -> dict[str, Any]:
        system = (
            "You are a strict LLM evaluator. Return only valid JSON with keys: "
            "score (0 to 1 float), rationale (string), issues (array). "
            "Each issue must have quote, description, severity where severity "
            "is one of: low, medium, high."
        )
        user = (
            f"Dimension: {dimension}\n\n"
            f"Original prompt:\n{prompt}\n\n"
            f"Candidate response:\n{candidate_response}\n\n"
            "Evaluate the response against the dimension and return JSON only."
        )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.site_url or "https://localhost",
            "X-Title": self.app_name,
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

        content = data["choices"][0]["message"]["content"]
        return json.loads(content)
