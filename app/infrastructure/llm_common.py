"""Shared HTTP helper for LLM provider adapters."""

from typing import Any

import httpx


class LLMError(RuntimeError):
    """Provider returned an error status. The message keeps the body snippet for diagnosis."""


def post_json(
    http: httpx.Client, url: str, *, headers: dict[str, str], body: dict[str, Any], timeout: float
) -> dict[str, Any]:
    response = http.post(url, headers=headers, json=body, timeout=timeout)
    if response.status_code >= 400:
        raise LLMError(f"HTTP {response.status_code}: {response.text[:300]}")
    return response.json()
