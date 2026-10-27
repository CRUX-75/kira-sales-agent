"""Wire the conversation service from settings (the composition root)."""

from app.application.conversation import ConversationService
from app.config import Settings
from app.infrastructure.kb import load_kb
from app.infrastructure.llm_factory import build_wording_client
from app.infrastructure.session_factory import build_session_repository


def build_conversation_service(settings: Settings) -> ConversationService:
    return ConversationService(
        sessions=build_session_repository(settings),
        kb=load_kb(),
        wording=build_wording_client(settings),
    )
