import json

import httpx
import pytest

from app.application.wording import WordingRequest
from app.config import Settings
from app.infrastructure.llm_anthropic import AnthropicWordingClient
from app.infrastructure.llm_common import LLMError
from app.infrastructure.llm_factory import build_wording_client
from app.infrastructure.llm_openai import OpenAIWordingClient

REQUEST = WordingRequest("ASK_ZONE_1", "Welche Zone stört dich am meisten?", (), 1, user_text="hey")


def make_http(handler):
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_anthropic_request_shape_and_parsing():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["headers"] = request.headers
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "content": [
                    {"type": "thinking", "thinking": "..."},
                    {"type": "text", "text": "Welche Zone zuerst?"},
                ],
                "usage": {"input_tokens": 120, "output_tokens": 15},
            },
        )

    client = AnthropicWordingClient("secret", http=make_http(handler))
    assert client.reword(REQUEST) == "Welche Zone zuerst?"
    body = seen["body"]
    assert seen["url"] == "https://api.anthropic.com/v1/messages"
    assert seen["headers"]["x-api-key"] == "secret"
    assert seen["headers"]["anthropic-version"] == "2023-06-01"
    assert body["model"] == "claude-haiku-5-5"
    assert body["output_config"] == {"effort": "low"}
    assert body["max_tokens"] >= 300  # thinking tokens count against max_tokens
    assert body["system"] and body["messages"][0]["role"] == "user"
    for forbidden in ("temperature", "top_p", "top_k", "thinking"):  # HTTP 400 on Haiku 5.5
        assert forbidden not in body
    assert (client.last_usage.input_tokens, client.last_usage.output_tokens) == (120, 15)
    assert client.label == "anthropic:claude-haiku-5-5:low"


def test_openai_request_shape_and_parsing():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["headers"] = request.headers
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "Welche Zone zuerst?"}}],
                "usage": {"prompt_tokens": 110, "completion_tokens": 40},
            },
        )

    client = OpenAIWordingClient("secret", effort="none", http=make_http(handler))
    assert client.reword(REQUEST) == "Welche Zone zuerst?"
    body = seen["body"]
    assert seen["url"] == "https://api.openai.com/v1/chat/completions"
    assert seen["headers"]["authorization"] == "Bearer secret"
    assert body["model"] == "gpt-6-luna"
    assert body["reasoning_effort"] == "none"
    assert [m["role"] for m in body["messages"]] == ["system", "user"]
    assert "temperature" not in body
    assert (client.last_usage.input_tokens, client.last_usage.output_tokens) == (110, 40)
    assert client.label == "openai:gpt-6-luna:none"


@pytest.mark.parametrize("cls", [AnthropicWordingClient, OpenAIWordingClient])
def test_http_errors_become_llm_error_with_the_body(cls):
    def handler(request):
        return httpx.Response(400, json={"error": "`temperature` is deprecated for this model."})

    client = cls("secret", http=make_http(handler))
    with pytest.raises(LLMError, match="400.*temperature"):
        client.reword(REQUEST)
    assert client.last_usage is None


def test_openai_empty_choices_return_empty_text():
    client = OpenAIWordingClient("k", http=make_http(lambda r: httpx.Response(200, json={})))
    assert client.reword(REQUEST) == ""


def test_factory_none_and_providers():
    assert build_wording_client(Settings(wording_provider="none")) is None
    openai = build_wording_client(Settings(wording_provider="openai", openai_api_key="k"))
    assert openai.label == "openai:gpt-6-luna:low"
    claude = build_wording_client(
        Settings(
            wording_provider="anthropic", anthropic_api_key="k", wording_model="claude-sonnet-5-5"
        )
    )
    assert claude.label == "anthropic:claude-sonnet-5-5:low"


def test_factory_rejects_missing_keys_and_unknown_providers():
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        build_wording_client(Settings(wording_provider="openai", openai_api_key=None))
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        build_wording_client(Settings(wording_provider="anthropic", anthropic_api_key=None))
    with pytest.raises(ValueError, match="Unknown"):
        build_wording_client(Settings(wording_provider="foo"))
