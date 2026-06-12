"""validation_agent의 '교정기(fixer)'가 제대로 고치는지 검증하는 테스트.

방식: 결함 대사 → judge가 지적 → fixer가 교정 → 다시 judge로 재검사.
  - 해결: 원래 NG였던 항목이 OK로 바뀌었나
  - 부작용: 교정하면서 '새로운' NG가 생기진 않았나 (이게 많으면 fixer가 출렁이는 것)
  - 보존: 원본·교정본을 나란히 출력 → 상황/캐릭터 유지 여부는 사람이 눈으로 확인

실행: prompt_test 폴더에서  python fixer_check.py
"""
import sys, io, contextlib, time
try:
    sys.stdout.reconfigure(encoding="utf-8")   # 윈도 콘솔(cp949)에서도 한글/기호 안전
except Exception:
    pass

from validation_agent import judge, fix, rule_clean
from judge_check import CASES

REPORT = "fixer_report.md"


class _Tee:
    """화면과 파일에 동시에 출력하기 위한 간단한 분배기."""
    def __init__(self, *streams): self.streams = streams
    def write(self, s):
        for st in self.streams: st.write(s)
    def flush(self):
        for st in self.streams: st.flush()

DEFECTS = [c for c in CASES if c["expect_ng"]]   # 클린 케이스(고칠 것 없음)는 제외


def diagnose(persona, kind, track):
    """rule + judge 통합 진단. (지적문자열, NG축집합, 정리된track, verdict) 반환."""
    t = dict(track)
    rule_issues, t["script"] = rule_clean(t["script"])
    verdict = judge(persona, kind, t)
    ng = {k for k, v in verdict.items() if v.get("status") == "NG"}
    issues = [f"[공백] {r}" for r in rule_issues] + [f"{a}: {verdict[a].get('근거','')}" for a in ng]
    return issues, ng, t, verdict


def run():
    tot_flagged = tot_resolved = tot_new = tot_kept = 0
    for c in DEFECTS:
        p, kind = c["persona"], c["kind"]
        issues0, ng0, orig, _ = diagnose(p, kind, c["track"]); time.sleep(2)   # 진단
        fixed = fix(p, kind, orig, issues0); time.sleep(2)                      # 교정
        issues1, ng1, fixedc, v1 = diagnose(p, kind, fixed); time.sleep(2)     # 재검사

        resolved = ng0 - ng1     # 사라진 NG
        still    = ng0 & ng1     # 그대로 남은 NG
        newly    = ng1 - ng0     # 새로 생긴 NG(부작용)
        tot_flagged += len(ng0); tot_resolved += len(resolved); tot_new += len(newly)

        kindlbl = "🅰 외모기반" if kind == "A" else "🅱 성격기반"
        print("=" * 66)
        print(f"[케이스: {c['name']}]   {kindlbl}")
        print("-" * 66)
        print(f"① 원본 ({len(orig['script'])}자):\n   {orig['script']}")
        print("\n② 지적된 문제 (judge가 잡은 것):")
        for it in issues0:
            print(f"   - {it}")
        print(f"\n③ 교정본 ({len(fixedc['script'])}자) — {fixedc.get('title','')}:\n   {fixedc['script']}")
        print("\n④ 재검사:")
        print(f"   ✅ 해결됨 : {sorted(resolved) or '없음'}")
        print(f"   ⚠️ 안 고쳐짐: {sorted(still) or '없음'}")
        print(f"   ❌ 새 부작용: {sorted(newly) or '없음'}")
        for a in newly:
            print(f"        └ {a}: {v1[a].get('근거','')}")
        guard_keep = len(ng1) >= len(ng0)        # 안 나아짐 → 가드가 원본 유지
        tot_kept += guard_keep
        print(f"   🛡 악화방지: {'발동 → 교정본 폐기, 원본 유지' if guard_keep else '미발동 → 교정본 채택(개선됨)'}"
              f"  (원본 NG {len(ng0)} → 교정본 NG {len(ng1)})")
        print()
        time.sleep(1)

    print("=" * 66)
    print("FIXER 검증 요약")
    print(f"  지적 NG 총 {tot_flagged}개 중 해결 {tot_resolved}개   (해결률 {tot_resolved}/{tot_flagged})")
    print(f"  새 부작용 총 {tot_new}개   (낮을수록 좋음 — 많으면 fixer가 출렁임)")
    print(f"  악화방지 발동 {tot_kept}/{len(DEFECTS)}개   (교정이 안 나아져 원본 유지한 케이스)")
    print("=" * 66)


if __name__ == "__main__":
    buf = io.StringIO()
    with contextlib.redirect_stdout(_Tee(sys.stdout, buf)):   # 화면 + 버퍼 동시 출력
        run()
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())
    print(f"\n→ 리포트 저장: {REPORT}")
