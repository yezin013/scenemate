"""SceneMate API — FastAPI 진입점."""
from fastapi import FastAPI, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from db import get_db

app = FastAPI(title="SceneMate API", version="0.1.0")


@app.get("/")
def root():
    return {"service": "SceneMate API", "status": "ok"}


@app.get("/health")
def health():
    """서버 자체가 살아있는지."""
    return {"status": "healthy"}


@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    """DB(Supabase)에 실제로 붙는지 확인."""
    version = db.execute(text("select version()")).scalar()
    return {"db": "connected", "version": version[:60]}
