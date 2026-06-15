"""DB 저장/조회 흐름 검증 — Gemini 0콜.

scripts 테이블에 수동 행을 넣고(insert) → 읽고(select) → 지운다(delete, 정리).
API의 /scripts 저장·조회가 쓰는 것과 같은 경로(models.py + db.py)를 그대로 태운다.
실행: backend 폴더에서  python db_check.py
"""
import sys
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from db import SessionLocal
import models

db = SessionLocal()
try:
    obj = models.Script(
        source="manual", track="appearance",
        title="__연결테스트__", script_text="DB 흐름 확인용 임시 대사입니다.",
        inputs={"test": True},
    )
    db.add(obj); db.commit(); db.refresh(obj)
    print(f"① insert OK  → id={obj.id}, created_at={obj.created_at}")

    got = db.get(models.Script, obj.id)
    print(f"② select OK  → '{got.title}' | inputs={got.inputs}")

    total = db.query(models.Script).count()
    print(f"③ 현재 scripts 총 행 수 = {total}")

    db.delete(got); db.commit()
    print("④ delete OK  → 테스트 행 정리됨")
    print("\n✅ DB 저장/조회 흐름 정상 (아카이브 CRUD 작동)")
finally:
    db.close()
