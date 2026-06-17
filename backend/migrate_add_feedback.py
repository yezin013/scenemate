"""scripts 테이블에 feedback(JSONB) 컬럼을 추가한다. (idempotent)

init_db.py의 create_all 은 '기존 테이블의 컬럼 추가'를 못 하므로 별도 ALTER가 필요하다.
이미 컬럼이 있으면 IF NOT EXISTS 로 건너뛴다 → 여러 번 돌려도 안전.

실행: backend 폴더에서  python migrate_add_feedback.py
(또는 Supabase SQL 편집기에서 아래 SQL 한 줄을 직접 실행해도 동일)
    ALTER TABLE scripts ADD COLUMN IF NOT EXISTS feedback JSONB;
"""
import sys
from sqlalchemy import text, inspect

from db import engine

SQL = "ALTER TABLE scripts ADD COLUMN IF NOT EXISTS feedback JSONB;"


def main():
    cols_before = {c["name"] for c in inspect(engine).get_columns("scripts")}
    if "feedback" in cols_before:
        print("이미 feedback 컬럼이 있습니다 — 변경 없음.")
        return

    with engine.begin() as conn:        # begin(): 성공 시 자동 commit
        conn.execute(text(SQL))

    cols_after = {c["name"] for c in inspect(engine).get_columns("scripts")}
    if "feedback" not in cols_after:
        print("❌ feedback 컬럼이 추가되지 않았습니다.")
        sys.exit(1)
    print("✅ feedback(JSONB) 컬럼 추가 완료.")


if __name__ == "__main__":
    main()
