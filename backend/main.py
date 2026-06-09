"""SceneMate API — FastAPI 진입점."""
from typing import List

from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from db import get_db
import models
from schemas import ScriptCreate, ScriptOut

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
