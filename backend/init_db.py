"""scripts 테이블을 Supabase(PostgreSQL)에 생성한다. (idempotent — 이미 있으면 건너뜀)

실행: backend 폴더에서  python init_db.py

원리:
- SQLAlchemy 모델(models.py)을 '정답'으로 삼아 테이블을 만든다 → 코드와 DB 스키마가 항상 일치.
- create_all 은 '없는 테이블만' 만든다(기존 테이블/데이터는 건드리지 않음).
- 단, 이미 있는 테이블의 '컬럼 변경'은 못 한다(그건 마이그레이션 영역). 컬럼을 바꿀 땐 DB에서 직접 ALTER 하거나 테이블을 지우고 다시 생성.
"""
import sys
from sqlalchemy import inspect, text

from db import engine, Base
import models  # noqa: F401 — import해야 모델이 Base.metadata에 등록됨


def main():
    # 1) 연결 확인 ----------------------------------------------------
    try:
        with engine.connect() as conn:
            ver = conn.execute(text("select version()")).scalar()
        print("✅ Supabase 연결 OK:", ver[:60])
    except Exception as e:
        print("❌ 연결 실패 — backend/.env의 DATABASE_URL 확인 필요:\n  ", e)
        sys.exit(1)

    # 2) 생성 전 상태 -------------------------------------------------
    before = set(inspect(engine).get_table_names())
    print("생성 전 테이블:", sorted(before) or "없음")

    # 3) 테이블 생성 (없는 것만) -------------------------------------
    Base.metadata.create_all(engine)

    after = set(inspect(engine).get_table_names())
    created = after - before
    print("이번에 생성된 테이블:", sorted(created) or "없음(이미 존재)")

    # 4) scripts 스키마 확인 -----------------------------------------
    if "scripts" not in after:
        print("⚠️ scripts 테이블이 여전히 보이지 않습니다.")
        sys.exit(1)
    print("\nscripts 컬럼:")
    for c in inspect(engine).get_columns("scripts"):
        null = "" if c.get("nullable", True) else " NOT NULL"
        print(f"  - {c['name']}: {c['type']}{null}")
    print("\n완료 — scripts 테이블 준비됨.")


if __name__ == "__main__":
    main()
