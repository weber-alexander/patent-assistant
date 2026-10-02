"""Thin wrapper around the Ollama client."""

from __future__ import annotations

from collections.abc import Callable

import ollama

from patent_assistant.config import settings

ProgressCallback = Callable[[float], None]

client = ollama.Client(host=settings.ollama_host)


def strip_thinking(text: str) -> str:
    """Remove a reasoning block (<think>...</think>) emitted by some models."""
    if "</think>" in text:
        text = text.split("</think>")[-1]
    return text.replace("<think>", "").strip()


def is_server_running() -> bool:
    try:
        client.list()
    except Exception:
        return False
    return True


def missing_models(required: tuple[str, ...] = settings.required_models) -> list[str]:
    """Return the required models that are not installed in Ollama."""
    installed: set[str] = set()
    for model in client.list().models:
        installed.add(model.model)
        installed.add(model.model.removesuffix(":latest"))
    return [name for name in required if name not in installed]


def pull_model(name: str, on_progress: ProgressCallback) -> None:
    """Download a model and report progress between 0 and 1."""
    for update in client.pull(name, stream=True):
        if update.total and update.completed:
            on_progress(update.completed / update.total)
    on_progress(1.0)


def generate(
    model: str,
    system_prompt: str,
    user_prompt: str,
    expected_length: int,
    on_progress: ProgressCallback | None = None,
) -> str:
    """Run a chat request and return the cleaned answer.

    Progress is an estimate (generated length vs. expected length),
    because the final length of an answer is unknown in advance.
    """
    text = ""
    stream = client.chat(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        stream=True,
        options=settings.llm_options,
    )
    for chunk in stream:
        text += chunk.message.content or ""
        if on_progress:
            on_progress(min(0.95, len(text) / max(expected_length, 1)))
    if on_progress:
        on_progress(1.0)
    return strip_thinking(text)


def embed(texts: list[str]) -> list[list[float]]:
    """Create embedding vectors for semantic search."""
    return client.embed(model=settings.embed_model, input=texts).embeddings
