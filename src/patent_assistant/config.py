"""Central configuration.

Every value can be overridden with an environment variable, e.g.
PA_CHAT_MODELS="qwen3:8b,qwen3:4b-instruct" to offer larger models.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    ollama_host: str
    chat_models: tuple[str, ...]
    embed_model: str
    temperature: float
    context_window: int
    projects_dir: Path
    knowledge_dir: Path

    @property
    def llm_options(self) -> dict[str, float | int]:
        """Options passed to every chat request."""
        return {"temperature": self.temperature, "num_ctx": self.context_window}

    @property
    def required_models(self) -> tuple[str, ...]:
        """Models that must be available in Ollama."""
        return (self.chat_models[0], self.embed_model)


def load_settings() -> Settings:
    models = os.getenv("PA_CHAT_MODELS", "qwen3:4b-instruct,qwen3:1.7b")
    return Settings(
        # Explicit loopback address: OLLAMA_HOST=0.0.0.0 does not work as a client target
        ollama_host=os.getenv("PA_OLLAMA_HOST", "http://127.0.0.1:11434"),
        chat_models=tuple(m.strip() for m in models.split(",") if m.strip()),
        embed_model=os.getenv("PA_EMBED_MODEL", "bge-m3"),
        temperature=float(os.getenv("PA_TEMPERATURE", "0.3")),
        context_window=int(os.getenv("PA_CONTEXT_WINDOW", "8192")),
        projects_dir=Path(os.getenv("PA_PROJECTS_DIR", "projects")),
        knowledge_dir=Path(os.getenv("PA_KNOWLEDGE_DIR", "knowledge")),
    )


settings = load_settings()
