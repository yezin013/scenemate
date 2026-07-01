"""Gemini text-embedding-004 — 대사 텍스트 → 768차원 벡터."""
from llm import client

_MODEL = "text-embedding-004"


def embed_script(title: str | None, setup: str | None, script_text: str) -> list[float]:
    parts = [f"대사: {script_text}"]
    if setup:
        parts.insert(0, f"상황: {setup}")
    if title:
        parts.insert(0, f"제목: {title}")
    result = client.models.embed_content(model=_MODEL, contents="\n".join(parts))
    return result.embeddings[0].values
