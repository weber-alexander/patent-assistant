"""Saving and loading projects as JSON files."""

from __future__ import annotations

import json
import re
from pathlib import Path

from patent_assistant.config import settings
from patent_assistant.prompts import SECTIONS

FORMAT_VERSION = 1
FIELDS: tuple[str, ...] = ("project_name", "invention", "known_prior_art", *SECTIONS)

# Field names of the German prototype (files saved before format version 1)
LEGACY_KEYS = {
    "projektname": "project_name",
    "erfindung": "invention",
    "stand_bekannt": "known_prior_art",
    "ansprueche": "claims",
    "titel": "title",
    "gebiet": "field",
    "stand": "prior_art",
    "aufgabe": "problem",
    "loesung": "solution",
    "ausfuehrung": "embodiment",
    "zusammenfassung": "abstract",
    "fragen": "questions",
}


def empty_project() -> dict[str, str]:
    return dict.fromkeys(FIELDS, "")


def safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^\w\-]", "_", name.strip()).strip("_")
    return cleaned or "projekt"


def _path(name: str) -> Path:
    settings.projects_dir.mkdir(exist_ok=True)
    return settings.projects_dir / f"{name}.json"


def list_projects() -> list[str]:
    settings.projects_dir.mkdir(exist_ok=True)
    return sorted(p.stem for p in settings.projects_dir.glob("*.json"))


def exists(name: str) -> bool:
    return _path(name).exists()


def load_project(name: str) -> dict[str, str]:
    raw = json.loads(_path(name).read_text(encoding="utf-8"))
    project = empty_project()
    for key, value in raw.items():
        key = LEGACY_KEYS.get(key, key)
        if key in project and isinstance(value, str):
            project[key] = value
    return project


def save_project(name: str, data: dict[str, str]) -> Path:
    path = _path(name)
    content = {"format_version": FORMAT_VERSION, **{f: data.get(f, "") for f in FIELDS}}
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
