"""어드민 전용 인증 + 라우터.

ADMIN_USER_ID 환경변수에 등록된 UUID 소유자만 /admin/* 접근 가능.
"""
import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from db import get_db
from auth import get_current_user
from schemas import AdminScriptOut
import models

ADMIN_USER_ID = os.environ.get("ADMIN_USER_ID", "")


def require_admin(user_id: str = Depends(get_current_user)) -> str:
    """현재 사용자가 ADMIN_USER_ID와 일치하는지 확인."""
    if not ADMIN_USER_ID or user_id != ADMIN_USER_ID:
        raise HTTPException(status_code=403, detail="forbidden")
    return user_id


router = APIRouter(prefix="/admin", dependencies=[Depends(require_admin)])


@router.get("/check")
def check():
    """어드민 여부 확인용 — 200이면 어드민, 403이면 일반 사용자."""
    return {"admin": True}


@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    """전체 사용 통계."""
    total_scripts = db.query(func.count(models.Script.id)).scalar()
    total_users = db.query(
        func.count(func.distinct(models.Script.user_id))
    ).scalar()
    track_counts = (
        db.query(models.Script.track, func.count(models.Script.id))
        .group_by(models.Script.track)
        .all()
    )
    return {
        "total_scripts": total_scripts,
        "total_users": total_users,
        "by_track": {t: c for t, c in track_counts},
    }


@router.get("/scripts", response_model=List[AdminScriptOut])
def all_scripts(db: Session = Depends(get_db)):
    """전체 사용자 대사 목록 (최신순 200개)."""
    return (
        db.query(models.Script)
        .order_by(models.Script.created_at.desc())
        .limit(200)
        .all()
    )
