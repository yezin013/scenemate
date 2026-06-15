"""validation_agent 응답 캐시 검증 — Gemini 실제 호출 0회 (한도 안 씀).

방식: client.models.generate_content를 '가짜'로 대체해 네트워크를 차단하고,
      GENAI_CACHE 캐시 레이어(validation_agent._gen_json)가 의도대로 도는지 확인한다.
  ① 새 입력      → 실제 호출 발생
  ② 같은 입력 재호출 → 캐시 적중 → 실제 호출 X (← 한도 절약의 핵심)
  ③ 다른 입력      → 새로 호출
  ④ 캐시본 == 원본 응답 (일관성)

judge/fixer 프롬프트가 아니라 '캐시 동작' 자체의 회귀 테스트다.
실행: prompt_test 폴더에서  python cache_check.py
"""
import os, sys, shutil
os.environ["GENAI_CACHE"] = "1"            # validation_agent import '전에' 캐시 ON
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import validation_agent as va

shutil.rmtree(va._CACHE_DIR, ignore_errors=True)   # 깨끗한 상태에서 시작

calls = {"n": 0}
class _FakeResp:
    def __init__(self, text): self.text = text

def _fake_generate(model, contents, config):       # 네트워크 대신 가짜 응답 반환
    calls["n"] += 1
    return _FakeResp('{"호칭일관성":{"status":"OK","근거":"테스트"}}')

va.client.models.generate_content = _fake_generate

persona = {"appearance_keywords": "x", "self_intro": "y"}
track   = {"title": "t", "situation": "s", "script": "안녕하세요. 테스트 대사입니다."}
track2  = dict(track, script="다른 대사예요.")

r1 = va.judge(persona, "A", track);   n1 = calls["n"]   # 새 입력  → 호출
r2 = va.judge(persona, "A", track);   n2 = calls["n"]   # 동일 입력 → 캐시 적중
r3 = va.judge(persona, "A", track2);  n3 = calls["n"]   # 다른 입력 → 호출

print("=" * 58)
print("validation_agent 캐시 검증  (Gemini 실제 호출 0회)")
print("-" * 58)
print(f"① 새 입력 1회       → 누적 실제 호출 {n1}              (기대 1)")
print(f"② 동일 입력 재호출   → 누적 실제 호출 {n2} (증가 {n2 - n1})    (기대 +0, 캐시 적중)")
print(f"③ 다른 입력 호출     → 누적 실제 호출 {n3} (증가 {n3 - n2})    (기대 +1)")
print(f"④ 캐시본 == 원본 응답: {r1 == r2}")
ok = (n1 == 1) and (n2 == n1) and (n3 == n2 + 1) and (r1 == r2)
print("-" * 58)
print("결과:", "✅ 캐시 정상" if ok else "❌ 캐시 이상")
print("=" * 58)

shutil.rmtree(va._CACHE_DIR, ignore_errors=True)   # 잔여물 정리
sys.exit(0 if ok else 1)
