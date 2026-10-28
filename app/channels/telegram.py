"""Telegram channel logic: parsing, access policy, webhook secret and anonymous ids.

Pure functions, no network. A thin HTTP layer (next step) receives the webhook, calls these
functions, runs the conversation service and sends the replies.
"""

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class IncomingMessage:
    update_id: int
    chat_id: int
    text: str | None  # None when the message carries no text (photo, voice, sticker...)
    kind: str  # "text" | "unsupported"


@dataclass(frozen=True)
class Action:
    kind: str  # "ignore" | "reply" (fixed text, no conversation) | "converse"
    text: str = ""  # reply text, or the text to feed into the conversation


def parse_update(update: dict[str, Any]) -> IncomingMessage | None:
    """Return the message to handle, or None for everything we ignore.

    Ignored: updates without a message (edits, member changes, callbacks...), group chats and
    messages sent by bots (avoids bot-to-bot loops and LLM cost).
    """
    update_id = update.get("update_id")
    message = update.get("message")
    if not isinstance(message, dict) or not isinstance(update_id, int):
        return None
    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    chat_id = chat.get("id")
    if chat.get("type") != "private" or sender.get("is_bot"):
        return None
    if not isinstance(chat_id, int) or isinstance(chat_id, bool):
        return None
    text = message.get("text")
    if isinstance(text, str) and text.strip():
        return IncomingMessage(update_id, chat_id, text.strip(), "text")
    return IncomingMessage(update_id, chat_id, None, "unsupported")


def _command(text: str) -> str | None:
    """'/start payload' and '/start@my_bot' both give 'start'."""
    if not text.startswith("/"):
        return None
    head = text.split(maxsplit=1)[0][1:]
    return head.split("@", 1)[0].lower() or None


def decide(
    incoming: IncomingMessage | None, allowed_chat_ids: frozenset[int], kb: dict[str, Any]
) -> Action:
    """Access policy. An empty allowlist means nobody (fail closed), except /id."""
    if incoming is None:
        return Action("ignore")
    templates = kb["templates"]
    command = _command(incoming.text) if incoming.text else None
    if command == "id":  # anyone may learn their own chat id, to be added to the allowlist
        return Action("reply", templates["CHANNEL_CHAT_ID"].format(chat_id=incoming.chat_id))
    if incoming.chat_id not in allowed_chat_ids:
        return Action("reply", templates["CHANNEL_NOT_ALLOWED"])
    if incoming.text is None:
        return Action("reply", templates["CHANNEL_UNSUPPORTED"])
    if command == "start":
        return Action("converse", "Hallo")
    if command == "stop":
        return Action("converse", "Stopp")
    return Action("converse", incoming.text)


def verify_secret(header_value: str | None, expected: str) -> bool:
    """Constant-time check of X-Telegram-Bot-Api-Secret-Token. No secret configured = reject."""
    if not expected or header_value is None:
        return False
    return hmac.compare_digest(header_value.encode(), expected.encode())


def conversation_id(chat_id: int, secret: str) -> str:
    """Anonymous, stable conversation id: HMAC of the chat id. The chat id is never stored."""
    if not secret:
        raise ValueError("CONVERSATION_ID_SECRET is required")
    digest = hmac.new(secret.encode(), f"telegram:{chat_id}".encode(), hashlib.sha256)
    return f"tg_{digest.hexdigest()[:32]}"


def parse_allowed_chat_ids(raw: str) -> frozenset[int]:
    ids: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            ids.add(int(part))
        except ValueError:
            raise ValueError(f"Invalid chat id in TELEGRAM_ALLOWED_CHAT_IDS: {part!r}") from None
    return frozenset(ids)
