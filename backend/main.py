"""SceneMate API — FastAPI 진입점."""
from typing import List

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from db import get_db
import models
from schemas import ScriptCreate, ScriptOut, GenerateRequest, GenerateResponse
from generator import generate_dialogues

app = FastAPI(title="SceneMate API", version="0.1.0")


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


# ── 대사 생성 (AI) ────────────────────────────────────────
@app.post("/generate", response_model=GenerateResponse)
def generate(payload: GenerateRequest, db: Session = Depends(get_db)):
    """입력 3종(외모키워드·자기소개·말투) → 대사 두 개 생성. save=True면 아카이브 저장."""
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
        saved_ids = [o.id for o in objs]

    return {**result, "saved_ids": saved_ids}


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
