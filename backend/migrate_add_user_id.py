"""scripts 테이블에 user_id UUID 컬럼을 추가하는 마이그레이션."""
import os
from pathlib import Path
from dotenv import load_dotenv
import sqlalchemy as sa

load_dotenv(Path(__file__).parent / ".env")

engine = sa.create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)

with engine.connect() as conn:
    conn.execute(sa.text("ALTER TABLE scripts ADD COLUMN IF NOT EXISTS user_id UUID"))
    conn.commit()
    print("완료: user_id UUID 컬럼 추가 (또는 이미 있음)")
