"""analysis 테이블을 생성한다. (idempotent)

실행: backend 폴더에서  python migrate_create_analysis.py
(또는 Supabase SQL 편집기에서 아래 SQL을 직접 실행해도 동일)
"""
import sys
from sqlalchemy import text, inspect

from db import engine

SQL = """
CREATE TABLE IF NOT EXISTS analysis (
    id         BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    script_id  BIGINT NOT NULL REFERENCES scripts(id) ON DELETE CASCADE,
    user_id    UUID,
    subtext      TEXT,
    action_verb  TEXT,
    emotion_arc  TEXT,
    context      TEXT,
    character_bg TEXT,
    relationship TEXT,
    real_goal    TEXT,
    ai_analysis  JSONB
);
"""


def main():
    inspector = inspect(engine)
    if "analysis" in inspector.get_table_names():
        print("이미 analysis 테이블이 있습니다. 변경 없음.")
        return

    with engine.begin() as conn:
        conn.execute(text(SQL))

    if "analysis" not in inspect(engine).get_table_names():
        print("[FAIL] analysis 테이블이 생성되지 않았습니다.")
        sys.exit(1)
    print("[OK] analysis 테이블 생성 완료.")


if __name__ == "__main__":
    main()
