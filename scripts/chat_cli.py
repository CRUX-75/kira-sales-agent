"""Talk to Kira in the terminal, with no channel and no server. From the repository root:

    python scripts/chat_cli.py

Uses the configured wording provider (WORDING_PROVIDER in .env; "none" = templates only) and
DATABASE_URL (memory if unset, so the conversation is lost when you quit).
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import get_settings  # noqa: E402
from app.infrastructure.service_factory import build_conversation_service  # noqa: E402


def main() -> None:
    service = build_conversation_service(get_settings())
    conversation_id = f"cli-{sys.argv[1] if len(sys.argv) > 1 else 'local'}"
    print("Kira demo. Type 'exit' to quit.\n")
    while True:
        try:
            text = input("Du:   ")
        except (EOFError, KeyboardInterrupt):
            break
        if text.strip().lower() in {"exit", "quit"}:
            break
        result = service.handle(conversation_id, text)
        for message in result.messages:
            tag = " [LLM]" if message.source == "llm" else ""
            print(f"Kira: {message.text}{tag}")
        print(f"      (state: {result.session.state.value})\n")


if __name__ == "__main__":
    main()
