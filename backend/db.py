"""DB 연결 모듈 — Supabase(PostgreSQL)에 SQLAlchemy로 연결."""
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# backend/.env 에서 DATABASE_URL 로드 (실행 위치와 무관하게)
load_dotenv(Path(__file__).parent / ".env")
DATABASE_URL = os.environ.get("SUPABASE_DATABASE_URL") or os.environ.get("DATABASE_URL", "")
if not DATABASE_URL:
    raise RuntimeError("SUPABASE_DATABASE_URL (or DATABASE_URL) 환경변수가 설정되지 않았습니다.")

# pool_pre_ping: 끊긴 연결 자동 감지 (Supabase pooler 환경에서 유용)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


def get_db():
    """FastAPI 의존성: 요청마다 DB 세션을 열고 끝나면 닫는다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
