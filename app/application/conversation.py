"""Conversation use case: one user message in, the messages to send back out.

It joins the pieces without knowing any channel: session repository, planner, wording client
and clock are injected. Channel adapters (Telegram, WhatsApp, CLI) call `handle` and send the
returned messages.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.application.planner import plan_turn
from app.application.ports import SessionRepository
from app.application.wording import RenderedMessage, WordingClient, render_turn
from app.domain.state_machine import Session

MAX_INPUT_CHARS = 1000  # caps LLM cost and abuse; longer texts are truncated
BERLIN = ZoneInfo("Europe/Berlin")


def berlin_now() -> datetime:
    """Naive local time of the studio. Containers run in UTC, so never use datetime.now()."""
    return datetime.now(UTC).astimezone(BERLIN).replace(tzinfo=None)


def normalize_input(text: str) -> str:
    return " ".join(text.split())[:MAX_INPUT_CHARS]


@dataclass(frozen=True)
class ConversationResult:
    messages: tuple[RenderedMessage, ...]
    session: Session
    topic: str
    session_reset: bool  # a stored session could not be read and a new one was started


class ConversationService:
    def __init__(
        self,
        sessions: SessionRepository,
        kb: dict[str, Any],
        wording: WordingClient | None = None,
        *,
        clock: Callable[[], datetime] = berlin_now,
        max_retries: int = 2,
    ) -> None:
        self._sessions = sessions
        self._kb = kb
        self._wording = wording
        self._clock = clock
        self._max_retries = max_retries

    def handle(self, conversation_id: str, text: str) -> ConversationResult:
        text = normalize_input(text)
        session, reset = self._load(conversation_id)
        plan = plan_turn(session, text, self._kb, self._clock())
        messages = render_turn(plan, self._wording, max_retries=self._max_retries, user_text=text)
        self._sessions.save(conversation_id, plan.session)
        return ConversationResult(messages, plan.session, plan.topic, reset)

    def _load(self, conversation_id: str) -> tuple[Session, bool]:
        try:
            stored = self._sessions.get(conversation_id)
        except (ValueError, KeyError, TypeError):  # unreadable or unsupported stored data
            return Session(), True
        return (stored or Session()), False
