"""Knowledge-base loader (single source of truth: data/kb/studio_aurea.json)."""

import json
from pathlib import Path
from typing import Any

DEFAULT_KB_PATH = Path(__file__).resolve().parents[2] / "data" / "kb" / "studio_aurea.json"


def load_kb(path: Path | None = None) -> dict[str, Any]:
    with (path or DEFAULT_KB_PATH).open(encoding="utf-8") as handle:
        return json.load(handle)
