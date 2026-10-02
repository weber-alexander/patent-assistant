"""Minimal local retrieval (RAG) without an external database.

Documents (PDF/TXT) live in the knowledge folder, the index is a JSON file.
Curated rule files (rules_*.txt) are split by blank lines: one rule per passage.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pypdf import PdfReader

from patent_assistant import llm
from patent_assistant.config import settings

INDEX_FILE = settings.knowledge_dir / "index.json"
SUPPORTED_SUFFIXES = (".pdf", ".txt")
RULES_PREFIX = "rules"

_cache: dict = {"mtime": None, "passages": []}


@dataclass(frozen=True)
class Passage:
    source: str
    text: str
    score: float = 0.0

    @property
    def is_rule(self) -> bool:
        return self.source.startswith(RULES_PREFIX)


def list_documents() -> list[Path]:
    settings.knowledge_dir.mkdir(exist_ok=True)
    return sorted(
        p for p in settings.knowledge_dir.iterdir() if p.suffix.lower() in SUPPORTED_SUFFIXES
    )


def _read(path: Path) -> str:
    if path.suffix.lower() == ".pdf":
        return "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
    return path.read_text(encoding="utf-8", errors="ignore")


def _split_paragraphs(text: str) -> list[str]:
    blocks = re.split(r"\n\s*\n", text.replace("\r\n", "\n"))
    return [" ".join(b.split()) for b in blocks if b.strip()]


def _split_chunks(text: str, size: int = 1000, overlap: int = 150) -> list[str]:
    """Split long text into overlapping chunks, preferably at sentence ends."""
    text = " ".join(text.split())
    chunks, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            period = text.rfind(". ", start + size // 2, end)
            if period != -1:
                end = period + 1
        chunks.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return chunks


def _normalize(vector: list[float]) -> list[float]:
    length = math.sqrt(sum(x * x for x in vector)) or 1.0
    return [round(x / length, 5) for x in vector]


def build_index(on_progress: Callable[[float], None] | None = None, batch: int = 16) -> int:
    """Read all documents, embed them and write the index. Returns the passage count."""
    entries = []
    for path in list_documents():
        text = _read(path)
        parts = _split_paragraphs(text) if path.suffix.lower() == ".txt" else _split_chunks(text)
        entries.extend({"source": path.stem, "text": part} for part in parts)

    for i in range(0, len(entries), batch):
        group = entries[i : i + batch]
        for entry, vector in zip(group, llm.embed([e["text"] for e in group]), strict=True):
            entry["vector"] = _normalize(vector)
        if on_progress:
            on_progress(min(1.0, (i + batch) / len(entries)))

    INDEX_FILE.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")
    return len(entries)


def _load_index() -> list[dict]:
    if not INDEX_FILE.exists():
        return []
    mtime = INDEX_FILE.stat().st_mtime
    if _cache["mtime"] != mtime:
        _cache["passages"] = json.loads(INDEX_FILE.read_text(encoding="utf-8"))
        _cache["mtime"] = mtime
    return _cache["passages"]


def index_summary() -> str:
    entries = _load_index()
    if not entries:
        return "Noch kein Index vorhanden."
    counts: dict[str, int] = {}
    for entry in entries:
        counts[entry["source"]] = counts.get(entry["source"], 0) + 1
    details = ", ".join(f"{source}: {n}" for source, n in sorted(counts.items()))
    return f"Index: {len(entries)} Abschnitte ({details})"


def search(query: str, k: int = 4) -> list[Passage]:
    """Return the k passages that are semantically closest to the query."""
    entries = _load_index()
    if not entries:
        return []
    query_vector = _normalize(llm.embed([query])[0])
    scored = sorted(
        ((sum(a * b for a, b in zip(query_vector, e["vector"], strict=True)), e) for e in entries),
        key=lambda pair: pair[0],
        reverse=True,
    )
    return [Passage(e["source"], e["text"], score) for score, e in scored[:k]]


def rules_for(query: str, limit: int = 4) -> list[Passage]:
    """Prefer curated rules; fall back to raw documents if no rules exist."""
    candidates = search(query, k=15)
    rules = [p for p in candidates if p.is_rule][:limit]
    return rules or candidates[:2]
