"""요청/응답 데이터 형식 (Pydantic)."""
from datetime import datetime
from pydantic import BaseModel


# ── 대사 생성 ─────────────────────────────────────────────
class GenerateRequest(BaseModel):
    """대사 생성 요청 (외모 키워드 + 자기소개)."""
    appearance_keywords: str
    self_intro: str
    save: bool = False   # True면 생성된 두 트랙을 scripts에 자동 저장


class Track(BaseModel):
    """대사 한 트랙 (v3: 목적·행동 중심)."""
    title: str
    situation: str          # 상대 + 전사 + 지금 상황
    objective: str          # 인물의 목적(행동 동사)
    script: str


class GenerateResponse(BaseModel):
    track_A_appearance: Track
    track_B_personality: Track
    appearance_keywords: str | None = None   # (사진 입력 시) Vision이 뽑은 키워드
    saved_ids: list[int] | None = None       # save=True일 때 저장된 행 id


class FeedbackItem(BaseModel):
    """오디션 피드백 한 건. (PATCH 입력 겸 응답 항목)"""
    date: str | None = None        # 오디션 날짜 (YYYY-MM-DD)
    venue: str | None = None       # 작품·오디션명/장소
    result: str | None = None      # 합격 / 불합격 / 대기 등
    memo: str | None = None        # 자유 메모
    created_at: str | None = None  # 서버 기록 시각 (응답 전용 — 입력값은 무시)


class ScriptCreate(BaseModel):
    """대사 저장 요청 형식."""
    script_text: str
    source: str = "manual"
    track: str | None = None
    title: str | None = None
    setup: str | None = None
    fit_reason: str | None = None
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
    inputs: dict | None = None
    feedback: list[FeedbackItem] | None = None   # 누적 오디션 피드백

    model_config = {"from_attributes": True}  # SQLAlchemy 객체 → Pydantic 변환 허용


class AdminScriptOut(ScriptOut):
    """어드민 전용 응답 — user_id 포함."""
    user_id: str | None = None
