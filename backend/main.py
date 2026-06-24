"""SceneMate API — FastAPI 진입점."""
from datetime import datetime, timezone
from typing import List

from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from db import get_db
import models
from schemas import (ScriptCreate, ScriptOut, GenerateRequest, GenerateResponse, FeedbackItem,
                     HintRequest, HintResponse, AnalysisLayers, AnalysisOut, ANALYSIS_LAYER_KEYS)
from generator import generate_dialogues
from judge import refine_track
from vision import extract_keywords
from auth import get_current_user
from admin import router as admin_router
from analyze import get_hint, get_full_analysis

app = FastAPI(title="SceneMate API", version="0.1.0")

# 개발용: 프론트엔드(브라우저)에서 API 호출 허용. 배포 시엔 도메인을 좁히는 게 좋음.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin_router)


# ── 헬스체크 ──────────────────────────────────────────────
@app.get("/")
def root():
    return {"service": "SceneMate API", "status": "ok"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    version = db.execute(text("select version()")).scalar()
    return {"db": "connected", "version": version[:60]}


# ── judge+fixer 정제 헬퍼 ────────────────────────────────
def _refine_result(result: dict, appearance_keywords: str, self_intro: str) -> dict:
    """생성된 두 트랙을 judge+fixer 파이프라인으로 정제."""
    for track_key, track_kind in [("track_A_appearance", "A"), ("track_B_personality", "B")]:
        refined = refine_track(appearance_keywords, self_intro, track_kind, result[track_key])
        result[track_key] = refined["final"]
    return result


# ── 생성 결과 저장 헬퍼 ───────────────────────────────────
def _save_tracks(db: Session, result: dict, inputs: dict, user_id: str) -> list[int]:
    objs = []
    for key, track_name in [("track_A_appearance", "appearance"),
                            ("track_B_personality", "personality")]:
        t = result[key]
        objs.append(models.Script(
            source="ai", track=track_name,
            title=t.get("title"), setup=t.get("situation"),
            script_text=t["script"], fit_reason=t.get("objective"),
            inputs=inputs, user_id=user_id,
        ))
    db.add_all(objs)
    db.commit()
    for o in objs:
        db.refresh(o)
    return [o.id for o in objs]


# ── 대사 생성: 텍스트 입력 ────────────────────────────────
@app.post("/generate", response_model=GenerateResponse)
def generate(payload: GenerateRequest, db: Session = Depends(get_db),
             user_id: str = Depends(get_current_user)):
    """입력 2종(외모키워드·자기소개) → 대사 2개."""
    result = generate_dialogues(payload.appearance_keywords, payload.self_intro)
    result = _refine_result(result, payload.appearance_keywords, payload.self_intro)
    saved_ids = None
    if payload.save:
        inputs = {"appearance_keywords": payload.appearance_keywords, "self_intro": payload.self_intro}
        saved_ids = _save_tracks(db, result, inputs, user_id)
    return {**result, "appearance_keywords": payload.appearance_keywords, "saved_ids": saved_ids}


# ── 대사 생성: 사진 업로드 → Vision 키워드 추출 ───────────
@app.post("/generate-from-photo", response_model=GenerateResponse)
def generate_from_photo(
    photo: UploadFile = File(...),
    self_intro: str = Form(...),
    save: bool = Form(False),
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
):
    """사진 + 자기소개 → Vision으로 외모 키워드 추출 후 대사 2개 생성."""
    image_bytes = photo.file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="empty photo")
    keywords = extract_keywords(image_bytes, photo.content_type or "image/jpeg")
    result = generate_dialogues(keywords, self_intro)
    result = _refine_result(result, keywords, self_intro)
    saved_ids = None
    if save:
        inputs = {"appearance_keywords": keywords, "self_intro": self_intro}
        saved_ids = _save_tracks(db, result, inputs, user_id)
    return {**result, "appearance_keywords": keywords, "saved_ids": saved_ids}


# ── 아카이브 (대사 저장/조회) ─────────────────────────────
@app.post("/scripts", response_model=ScriptOut)
def create_script(payload: ScriptCreate, db: Session = Depends(get_db),
                  user_id: str = Depends(get_current_user)):
    """대사 한 개 저장."""
    obj = models.Script(**payload.model_dump(), user_id=user_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.get("/scripts", response_model=List[ScriptOut])
def list_scripts(db: Session = Depends(get_db), user_id: str = Depends(get_current_user)):
    """저장된 대사 목록 — 본인 것만 (최신순)."""
    return (db.query(models.Script)
              .filter(models.Script.user_id == user_id)
              .order_by(models.Script.created_at.desc())
              .all())


@app.get("/scripts/{script_id}", response_model=ScriptOut)
def get_script(script_id: int, db: Session = Depends(get_db),
               user_id: str = Depends(get_current_user)):
    """대사 한 개 조회 (본인 것만)."""
    obj = db.get(models.Script, script_id)
    if obj is None or obj.user_id != user_id:
        raise HTTPException(status_code=404, detail="script not found")
    return obj


@app.patch("/scripts/{script_id}/feedback", response_model=ScriptOut)
def add_feedback(script_id: int, item: FeedbackItem, db: Session = Depends(get_db),
                 user_id: str = Depends(get_current_user)):
    """대사에 오디션 피드백 한 건을 누적(append)한다."""
    obj = db.get(models.Script, script_id)
    if obj is None or obj.user_id != user_id:
        raise HTTPException(status_code=404, detail="script not found")

    entry = item.model_dump(exclude={"created_at"})        # 클라이언트가 보낸 created_at은 버림
    if not any(v for v in entry.values()):                 # 전부 빈 값이면 거부
        raise HTTPException(status_code=400, detail="empty feedback")
    entry["created_at"] = datetime.now(timezone.utc).isoformat()

    # JSONB 컬럼은 새 리스트로 재할당해야 SQLAlchemy가 변경을 감지한다.
    obj.feedback = list(obj.feedback or []) + [entry]
    db.commit()
    db.refresh(obj)
    return obj


# ── 대사 분석 ─────────────────────────────────────────────
def _analysis_to_out(row: models.Analysis) -> AnalysisOut:
    return AnalysisOut(
        id=row.id,
        created_at=row.created_at,
        script_id=row.script_id,
        user_analysis=AnalysisLayers(**{k: getattr(row, k) or "" for k in ANALYSIS_LAYER_KEYS}),
        ai_analysis=row.ai_analysis or {},
    )


@app.post("/scripts/{script_id}/analyze", response_model=HintResponse)
def analyze_hint(script_id: int, payload: HintRequest, db: Session = Depends(get_db),
                 user_id: str = Depends(get_current_user)):
    """특정 레이어에 대한 힌트 반환 (저장 없음)."""
    obj = db.get(models.Script, script_id)
    if obj is None or obj.user_id != user_id:
        raise HTTPException(status_code=404, detail="script not found")
    if payload.layer not in ANALYSIS_LAYER_KEYS:
        raise HTTPException(status_code=400, detail=f"unknown layer: {payload.layer}")
    hint = get_hint(obj.script_text, obj.title, obj.setup, payload.layer, payload.draft)
    return {"hint": hint}


@app.get("/scripts/{script_id}/analyze/full", response_model=AnalysisOut)
def get_analysis(script_id: int, db: Session = Depends(get_db),
                 user_id: str = Depends(get_current_user)):
    """저장된 분석 조회."""
    obj = db.get(models.Script, script_id)
    if obj is None or obj.user_id != user_id:
        raise HTTPException(status_code=404, detail="script not found")
    row = (db.query(models.Analysis)
             .filter_by(script_id=script_id, user_id=user_id)
             .first())
    if row is None:
        raise HTTPException(status_code=404, detail="analysis not found")
    return _analysis_to_out(row)


@app.post("/scripts/{script_id}/analyze/full", response_model=AnalysisOut)
def analyze_full(script_id: int, payload: AnalysisLayers, db: Session = Depends(get_db),
                 user_id: str = Depends(get_current_user)):
    """사용자 7개 레이어 저장 + AI 전체 분석 생성 → 비교용 응답."""
    obj = db.get(models.Script, script_id)
    if obj is None or obj.user_id != user_id:
        raise HTTPException(status_code=404, detail="script not found")

    ai = get_full_analysis(obj.script_text, obj.title, obj.setup)

    row = (db.query(models.Analysis)
             .filter_by(script_id=script_id, user_id=user_id)
             .first())
    if row:
        for k, v in payload.model_dump().items():
            setattr(row, k, v)
        row.ai_analysis = ai
    else:
        row = models.Analysis(
            script_id=script_id, user_id=user_id,
            **payload.model_dump(), ai_analysis=ai,
        )
        db.add(row)

    db.commit()
    db.refresh(row)
    return _analysis_to_out(row)
