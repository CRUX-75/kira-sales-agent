"""Anthropic Messages API adapter (one HTTP attempt per call; retries live in render_message).

Claude Haiku 5.5 rejects sampling parameters (temperature, top_p, top_k) and manual thinking
budgets with HTTP 400, so none of them is sent. Thinking tokens count against `max_tokens`,
hence the generous limit; `effort` is the lever for cost and latency.
"""

import httpx

from app.application.prompts import build_prompt
from app.application.wording import Usage, WordingRequest
from app.infrastructure.llm_common import post_json


class AnthropicWordingClient:
    URL = "https://api.anthropic.com/v1/messages"
    API_VERSION = "2023-06-01"

    def __init__(
        self,
        api_key: str,
        model: str = "claude-haiku-5-5",
        *,
        effort: str = "low",
        timeout: float = 8.0,
        max_tokens: int = 500,
        http: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._effort = effort
        self._timeout = timeout
        self._max_tokens = max_tokens
        self._http = http or httpx.Client()
        self.label = f"anthropic:{model}:{effort}"
        self.last_usage: Usage | None = None

    def reword(self, request: WordingRequest) -> str:
        self.last_usage = None
        prompt = build_prompt(request)
        body = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "system": prompt.system,
            "messages": [{"role": "user", "content": prompt.user}],
            "output_config": {"effort": self._effort},
        }
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": self.API_VERSION,
            "content-type": "application/json",
        }
        data = post_json(self._http, self.URL, headers=headers, body=body, timeout=self._timeout)
        usage = data.get("usage") or {}
        self.last_usage = Usage(usage.get("input_tokens", 0), usage.get("output_tokens", 0))
        return "".join(
            b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
        )
