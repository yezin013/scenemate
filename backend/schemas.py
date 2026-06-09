"""요청/응답 데이터 형식 (Pydantic)."""
from datetime import datetime
from pydantic import BaseModel


class ScriptCreate(BaseModel):
    """대사 저장 요청 형식."""
    script_text: str
    source: str = "manual"
    track: str | None = None
    title: str | None = None
    setup: str | None = None
    fit_reason: str | None = None
    voice_style: str | None = None
    inputs: dict | None = None


class ScriptOut(BaseModel):
    """대사 응답 형식."""
    id: int
    created_at: datetime
    source: str
    track: str | None = None
    title: str | None = None
    setup: str | None = None
    script_text: str
    fit_reason: str | None = None
    voice_style: str | None = None
    inputs: dict | None = None

    model_config = {"from_attributes": True}  # SQLAlchemy 객체 → Pydantic 변환 허용
