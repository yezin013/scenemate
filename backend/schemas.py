"""요청/응답 데이터 형식 (Pydantic)."""
from datetime import datetime
from pydantic import BaseModel


# ── 대사 생성 ─────────────────────────────────────────────
class GenerateRequest(BaseModel):
    """대사 생성 요청 (입력 3종 텍스트)."""
    appearance_keywords: str
    self_intro: str
    voice_tone: str
    save: bool = False   # True면 생성된 두 트랙을 scripts에 자동 저장


class Track(BaseModel):
    """대사 한 트랙 (v3: 목적·행동 중심)."""
    title: str
    situation: str          # 상대 + 전사 + 지금 상황
    objective: str          # 인물의 목적(행동 동사)
    script: str
    voice_style: str | None = None


class GenerateResponse(BaseModel):
    track_A_appearance: Track
    track_B_personality: Track
    appearance_keywords: str | None = None   # (사진 입력 시) Vision이 뽑은 키워드
    saved_ids: list[int] | None = None       # save=True일 때 저장된 행 id


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
