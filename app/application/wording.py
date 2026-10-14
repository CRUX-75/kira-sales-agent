"""Wording port: lets an LLM reword `constrained` messages without ever being trusted.

The LLM is a replaceable client behind a Protocol. Every candidate is validated by
deterministic code (style, required facts, no invented numbers, no human claims). On failure
the client is retried with feedback; if all attempts fail, the deterministic template wins.
A provider error can never break a conversation.
"""

from dataclasses import dataclass
from typing import Protocol

from app.application.planner import Message, TurnPlan
from app.domain.validators import human_claims, introduced_numbers, missing_facts, validate_style

DEFAULT_MAX_RETRIES = 2  # first attempt + 2 retries = at most 3 client calls per message


@dataclass(frozen=True)
class WordingRequest:
    intent: str
    base_text: str  # deterministic text: the meaning the LLM must preserve
    required: tuple[str, ...]  # facts that must appear unchanged
    attempt: int  # 1-based
    feedback: tuple[str, ...] = ()  # violations of the previous attempt


class WordingClient(Protocol):
    def reword(self, request: WordingRequest) -> str: ...


@dataclass(frozen=True)
class RenderedMessage:
    intent: str
    text: str
    source: str  # "template" | "llm"
    attempts: int  # client calls made
    failures: tuple[tuple[str, ...], ...] = ()  # violations per failed attempt (observability)


def _normalize(candidate: str | None) -> str:
    text = " ".join((candidate or "").split())
    return text.strip("\"'“”„").strip()


def check_candidate(candidate: str, base_text: str, required: tuple[str, ...]) -> tuple[str, ...]:
    violations = list(validate_style(candidate))
    violations += [f"missing_fact:{fact}" for fact in missing_facts(candidate, required)]
    allowed = " ".join((base_text, *required))
    violations += [f"new_number:{number}" for number in introduced_numbers(candidate, allowed)]
    if human_claims(candidate):
        violations.append("human_claim")
    return tuple(violations)


def render_message(
    message: Message, client: WordingClient | None, *, max_retries: int = DEFAULT_MAX_RETRIES
) -> RenderedMessage:
    if client is None or message.wording != "constrained":
        return RenderedMessage(message.intent, message.text, "template", 0)

    failures: list[tuple[str, ...]] = []
    feedback: tuple[str, ...] = ()
    attempts = max_retries + 1
    for attempt in range(1, attempts + 1):
        request = WordingRequest(message.intent, message.text, message.required, attempt, feedback)
        try:
            candidate = _normalize(client.reword(request))
        except Exception:  # provider errors must never break the conversation
            feedback = ("client_error",)
            failures.append(feedback)
            continue
        feedback = check_candidate(candidate, message.text, message.required)
        if not feedback:
            return RenderedMessage(message.intent, candidate, "llm", attempt, tuple(failures))
        failures.append(feedback)
    return RenderedMessage(message.intent, message.text, "template", attempts, tuple(failures))


def render_turn(
    plan: TurnPlan, client: WordingClient | None, *, max_retries: int = DEFAULT_MAX_RETRIES
) -> tuple[RenderedMessage, ...]:
    return tuple(render_message(m, client, max_retries=max_retries) for m in plan.messages)
