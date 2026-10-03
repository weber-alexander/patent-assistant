"""Small per-user preferences, e.g. the last used model."""

from __future__ import annotations

import json

from patent_assistant.config import settings


def load() -> dict:
    try:
        return json.loads(settings.state_file.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save(**values: str) -> None:
    state = load() | values
    settings.state_file.write_text(
        json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
    )
