"""Build the configured wording client. `none` disables the LLM (templates only)."""

from app.application.wording import WordingClient
from app.config import Settings
from app.infrastructure.llm_anthropic import AnthropicWordingClient
from app.infrastructure.llm_openai import OpenAIWordingClient


def build_wording_client(settings: Settings) -> WordingClient | None:
    provider = settings.wording_provider.strip().lower()
    if provider in ("", "none"):
        return None
    options = {"effort": settings.wording_effort, "timeout": settings.wording_timeout_seconds}
    if provider == "openai":
        if not settings.openai_api_key:
            raise ValueError("WORDING_PROVIDER=openai requires OPENAI_API_KEY")
        model = settings.wording_model or "gpt-6-luna"
        return OpenAIWordingClient(settings.openai_api_key, model, **options)
    if provider == "anthropic":
        if not settings.anthropic_api_key:
            raise ValueError("WORDING_PROVIDER=anthropic requires ANTHROPIC_API_KEY")
        model = settings.wording_model or "claude-haiku-5-5"
        return AnthropicWordingClient(settings.anthropic_api_key, model, **options)
    raise ValueError(f"Unknown WORDING_PROVIDER: {settings.wording_provider!r}")
