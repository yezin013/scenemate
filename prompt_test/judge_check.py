"""validation_agent의 '검사기(judge)'가 제대로 판정하는지 검증하는 보정 테스트.

방법: 정답을 아는 '함정 케이스'(일부러 결함 심은 것 + 깨끗한 것)를 judge에 넣고,
      judge의 OK/NG가 기대값과 맞는지 대조 → 검사기 신뢰도를 숫자로 측정.
  - 결함 케이스: 해당 항목을 NG로 '잡아내야' 통과
  - 클린 케이스: 모든 항목 OK여야 통과 (멀쩡한 걸 NG로 잡으면 false positive)

실행: prompt_test 폴더에서  python judge_check.py   (인자 없이)
"""
import os, sys, time
os.environ.setdefault("GENAI_CACHE", "1")      # 픽스처 검증: 같은 입력은 캐시 → 첫 1회만 실제 호출
try:
    sys.stdout.reconfigure(encoding="utf-8")   # 윈도 콘솔(cp949)에서도 한글/기호 안전
except Exception:
    pass

from validation_agent import judge, rule_clean

# ---------- PART 1. 규칙 검사(regex) — API 없이 즉시 ----------
RULE_CASES = [
    ("안녕  하세요",   "이중 공백"),
    ("말이에요 .",     "문장부호 앞 공백"),
    (" 앞뒤 여백 ",    "앞뒤 공백"),
    ("깨끗한 문장이에요.", None),   # 결함 없어야 함
]

def check_rules():
    print("=" * 60)
    print("PART 1. 규칙 검사(regex)  — 정답 결정적")
    ok = 0
    for text, expect in RULE_CASES:
        issues, _ = rule_clean(text)
        if expect is None:
            passed = (len(issues) == 0)
        else:
            passed = any(expect in i for i in issues)
        ok += passed
        mark = "✅" if passed else "❌"
        print(f"  {mark} {repr(text):<22} 기대={expect or '없음':<14} 실제={issues}")
    print(f"  → 규칙 {ok}/{len(RULE_CASES)} 통과\n")
    return ok, len(RULE_CASES)


# ---------- PART 2. LLM 판정 검사 — 함정 케이스 ----------
# 각 케이스: 판정에 필요한 persona 맥락 + track + track_kind + 기대 NG 항목
CASES = [
    {
        "name": "회상 클리셰",
        "kind": "A",
        "persona": {
            "appearance_keywords": "도시적이고 서늘한 분위기, 날카로운 눈매, 무표정에 가까운 차분함",
            "self_intro": "차가워 보이지만 속은 여리다.",
            "voice_tone": "차분하고 낮은 톤.",
        },
        "track": {
            "title": "오래된 시계",
            "situation": "혼자 방에서 옛 물건을 본다.",
            "script": ("낡은 회중시계를 손바닥에 올려놓는다. 똑딱이는 소리가 아직도 그대로네. "
                       "네가 떠나던 날도 이 시계는 이렇게 움직이고 있었지. 함께 걷던 골목, 네가 좋아하던 그 노래, "
                       "다 어제 일 같은데. 사진첩을 넘기다 보면 그때의 우리가 웃고 있어. 보고 싶다. 정말 너무 보고 싶다."),
        },
        "expect_ng": ["회상클리셰"],
    },
    {
        "name": "호칭 뒤죽박죽",
        "kind": "B",
        "persona": {
            "appearance_keywords": "평범한 인상.",
            "self_intro": "직설적이고 할 말은 다 한다.",
            "voice_tone": "또렷하고 단정적.",
        },
        "track": {
            "title": "따지기",
            "situation": "약속을 어긴 상대를 추궁한다.",
            "script": ("너 정말 이럴 거야? 당신이 이렇게 나올 줄은 몰랐어요. 그쪽이 먼저 약속을 어겼잖아. "
                       "선생님, 제발 다시 생각해 주세요. 야, 내 말 듣고 있어? 당신 같은 사람은 처음 봐요."),
        },
        "expect_ng": ["호칭일관성"],
    },
    {
        "name": "트랙적합성 위반(차가운 외모인데 애교 코미디)",
        "kind": "A",
        "persona": {
            "appearance_keywords": "도시적이고 서늘한 분위기, 날카로운 눈매, 단정한 검은 머리, 무표정",
            "self_intro": "사실은 장난기 많다.",
            "voice_tone": "밝고 통통 튀는 톤.",
        },
        "track": {
            "title": "강아지",
            "situation": "길에서 강아지를 본다.",
            "script": ("꺄악! 강아지다! 너무너무 귀여워! 봐봐, 꼬리 흔드는 거 봐! 나 이런 거 진짜 못 참아. "
                       "우리 집에 데려가면 안 될까? 응? 응? 제발! 완전 사랑스러워, 어떡해, 심장 터질 것 같아!"),
        },
        "expect_ng": ["트랙적합성"],   # 외모(서늘·무표정)와 정반대 내용
    },
    {
        "name": "AI 토막 말투",
        "kind": "B",
        "persona": {
            "appearance_keywords": "평범한 인상.",
            "self_intro": "감정이 풍부하다.",
            "voice_tone": "자연스럽고 따뜻한 말투.",
        },
        "track": {
            "title": "이별",
            "situation": "헤어진 상대 앞에 서 있다.",
            "script": ("나는 화가 난다. 나는 슬프다. 그것은 사실이다. 당신은 나를 떠났다. 나는 그것을 이해한다. "
                       "나는 그것을 이해하지 못한다. 감정은 복잡하다. 나는 말한다. 나는 멈춘다. 끝이다."),
        },
        "expect_ng": ["말투자연스러움"],
    },
    {
        "name": "클린(모두 OK 기대)",
        "kind": "B",
        "persona": {
            "appearance_keywords": "맑은 인상, 큰 눈망울.",
            "self_intro": "여려 보이지만 당차고 주도적이다.",
            "voice_tone": "맑고 또렷한 목소리, 자신감 있는 어조.",
        },
        "track": {
            "title": "내 차례",
            "situation": "팀에서 자기 의견을 분명히 밀어붙이는 순간.",
            "script": ("잠깐만요. 다들 결정 났다고 생각하시는 거 아는데, 한 번만 더 들어주세요. "
                       "이대로 가면 우리가 제일 자신 있던 부분을 통째로 버리는 거예요. 저는 그게 아깝습니다. "
                       "겁나서 이러는 거 아니에요. 제가 끝까지 책임질 테니까, 제 방식대로 한 번만 해보게 해주세요. "
                       "안 되면 그때 제가 깔끔하게 물러날게요. 어때요, 한 번만 믿어주실래요?"),
        },
        "expect_ng": [],
    },
]


def check_judge():
    print("=" * 60)
    print("PART 2. LLM 판정 검사  — 함정 케이스 대조")
    caught = 0          # 결함 케이스에서 심은 문제를 잡은 수
    defect_total = 0
    false_pos = 0       # 클린 케이스에서 멀쩡한 걸 NG로 잡은 수
    for c in CASES:
        verdict = judge(c["persona"], c["kind"], c["track"])
        actual_ng = {k for k, v in verdict.items() if v.get("status") == "NG"}
        expect = set(c["expect_ng"])
        if expect:                                  # 결함 케이스
            defect_total += 1
            hit = expect.issubset(actual_ng)
            caught += hit
            extra = actual_ng - expect
            mark = "✅ 잡음" if hit else "❌ 놓침"
            print(f"\n  [{c['name']}]  {mark}")
            print(f"    기대 NG: {sorted(expect)}   실제 NG: {sorted(actual_ng)}")
            if extra:
                print(f"    (참고: 추가로 잡은 항목 {sorted(extra)} — 과한지 눈으로 확인)")
        else:                                       # 클린 케이스
            fp = len(actual_ng)
            false_pos += fp
            mark = "✅ 전부 OK" if fp == 0 else f"⚠️ {fp}개 오탐"
            print(f"\n  [{c['name']}]  {mark}")
            print(f"    실제 NG: {sorted(actual_ng) or '없음'}")
            for k in actual_ng:
                print(f"      - {k}: {verdict[k].get('근거','')}")
        time.sleep(2)
    print(f"\n  → 결함 탐지: {caught}/{defect_total}  |  클린 오탐: {false_pos}개")
    return caught, defect_total, false_pos


if __name__ == "__main__":
    r_ok, r_tot = check_rules()
    caught, dtot, fp = check_judge()
    print("\n" + "=" * 60)
    print("판정 요약")
    print(f"  규칙 검사   : {r_ok}/{r_tot} 통과")
    print(f"  결함 탐지   : {caught}/{dtot} (높을수록 좋음 — 놓치면 게이트로 못 믿음)")
    print(f"  클린 오탐   : {fp}개 (낮을수록 좋음 — 많으면 너무 빡셈/과교정)")
    print("=" * 60)
