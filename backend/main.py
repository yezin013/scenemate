"""SceneMate API — FastAPI 진입점."""
from typing import List

from fastapi import FastAPI, Depends, HTTPException, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from db import get_db
import models
from schemas import ScriptCreate, ScriptOut, GenerateRequest, GenerateResponse
from generator import generate_dialogues
from vision import extract_keywords

app = FastAPI(title="SceneMate API", version="0.1.0")

# 개발용: 프론트엔드(브라우저)에서 API 호출 허용. 배포 시엔 도메인을 좁히는 게 좋음.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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


# ── 생성 결과 저장 헬퍼 ───────────────────────────────────
def _save_tracks(db: Session, result: dict, inputs: dict) -> list[int]:
    objs = []
    for key, track_name in [("track_A_appearance", "appearance"),
                            ("track_B_personality", "personality")]:
        t = result[key]
        objs.append(models.Script(
            source="ai", track=track_name,
            title=t.get("title"), setup=t.get("setup"),
            script_text=t["script"], fit_reason=t.get("fit_reason"),
            voice_style=t.get("voice_style"), inputs=inputs,
        ))
    db.add_all(objs)
    db.commit()
    for o in objs:
        db.refresh(o)
    return [o.id for o in objs]


# ── 대사 생성: 텍스트 입력 ────────────────────────────────
@app.post("/generate", response_model=GenerateResponse)
def generate(payload: GenerateRequest, db: Session = Depends(get_db)):
    """입력 3종(외모키워드·자기소개·말투 텍스트) → 대사 2개."""
    result = generate_dialogues(
        payload.appearance_keywords, payload.self_intro, payload.voice_tone
    )
    saved_ids = None
    if payload.save:
        inputs = {
            "appearance_keywords": payload.appearance_keywords,
            "self_intro": payload.self_intro,
            "voice_tone": payload.voice_tone,
        }
        saved_ids = _save_tracks(db, result, inputs)
    return {**result, "appearance_keywords": payload.appearance_keywords, "saved_ids": saved_ids}


# ── 대사 생성: 사진 업로드 → Vision 키워드 추출 ───────────
@app.post("/generate-from-photo", response_model=GenerateResponse)
def generate_from_photo(
    photo: UploadFile = File(...),
    self_intro: str = Form(...),
    voice_tone: str = Form(...),
    save: bool = Form(False),
    db: Session = Depends(get_db),
):
    """사진 + 자기소개 + 말투 → Vision으로 외모 키워드 추출 후 대사 2개 생성."""
    image_bytes = photo.file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="empty photo")
    keywords = extract_keywords(image_bytes, photo.content_type or "image/jpeg")
    result = generate_dialogues(keywords, self_intro, voice_tone)
    saved_ids = None
    if save:
        inputs = {"appearance_keywords": keywords, "self_intro": self_intro, "voice_tone": voice_tone}
        saved_ids = _save_tracks(db, result, inputs)
    return {**result, "appearance_keywords": keywords, "saved_ids": saved_ids}


# ── 아카이브 (대사 저장/조회) ─────────────────────────────
@app.post("/scripts", response_model=ScriptOut)
def create_script(payload: ScriptCreate, db: Session = Depends(get_db)):
    """대사 한 개 저장."""
    obj = models.Script(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.get("/scripts", response_model=List[ScriptOut])
def list_scripts(db: Session = Depends(get_db)):
    """저장된 대사 목록 (최신순)."""
    return db.query(models.Script).order_by(models.Script.created_at.desc()).all()


@app.get("/scripts/{script_id}", response_model=ScriptOut)
def get_script(script_id: int, db: Session = Depends(get_db)):
    """대사 한 개 조회."""
    obj = db.get(models.Script, script_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="script not found")
    return obj
