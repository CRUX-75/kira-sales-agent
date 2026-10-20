"""OpenAI Chat Completions adapter (one HTTP attempt per call; retries live in render_message).

`reasoning_effort` controls hidden reasoning tokens, which are billed as output tokens.
"""

import httpx

from app.application.prompts import build_prompt
from app.application.wording import Usage, WordingRequest
from app.infrastructure.llm_common import post_json


class OpenAIWordingClient:
    URL = "https://api.openai.com/v1/chat/completions"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-6-luna",
        *,
        effort: str = "low",
        timeout: float = 8.0,
        max_completion_tokens: int = 500,
        http: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._effort = effort
        self._timeout = timeout
        self._max_completion_tokens = max_completion_tokens
        self._http = http or httpx.Client()
        self.label = f"openai:{model}:{effort}"
        self.last_usage: Usage | None = None

    def reword(self, request: WordingRequest) -> str:
        self.last_usage = None
        prompt = build_prompt(request)
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": prompt.system},
                {"role": "user", "content": prompt.user},
            ],
            "max_completion_tokens": self._max_completion_tokens,
            "reasoning_effort": self._effort,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        data = post_json(self._http, self.URL, headers=headers, body=body, timeout=self._timeout)
        usage = data.get("usage") or {}
        self.last_usage = Usage(usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
        choices = data.get("choices") or [{}]
        return (choices[0].get("message") or {}).get("content") or ""
