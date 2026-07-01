"""대사 교정(fixer) — 기계적 공백 정리(rule_clean) + judge 지적사항 LLM 재작성(fix).

prompt_test/validation_agent.py에서 추출. notebook.ipynb 의존 제거하고
입력을 (외모 키워드, 자기소개) 두 문자열로 받도록 바꿈.
교정 시 작법관은 생성기(generator.py)와 단일 출처를 공유한다.
"""
import re

from llm import gen_json
from generator import SYSTEM_INSTRUCTION   # 생성·교정이 같은 작법 원칙을 공유

LEN_MIN, LEN_MAX = 300, 600   # 오디션 독백 적정 길이(자)


def rule_clean(text):
    """기계적 공백/문법 결함을 결정적으로 교정. (위반목록, 정리된 텍스트) 반환. (LLM 호출 없음)"""
    text = text or ""
    issues = []
    if "  " in text:                    issues.append("이중 공백")
    if re.search(r"\s[.,!?…]", text):   issues.append("문장부호 앞 공백")
    if text != text.strip():            issues.append("앞뒤 공백")
    if "\n\n" in text:                  issues.append("빈 줄")
    cleaned = re.sub(r"[ \t]+", " ", text)             # 다중 공백 → 1칸
    cleaned = re.sub(r"\s+([.,!?…])", r"\1", cleaned)  # 부호 앞 공백 제거
    cleaned = re.sub(r"\n{2,}", "\n", cleaned).strip()
    return issues, cleaned


def fix(appearance_keywords, self_intro, track_kind, track, issues):
    """지적된 문제'만' 고쳐 대사를 다시 씀. track_kind: 'A'(외모) | 'B'(성격).

    구조적 문제(트랙적합성/회상)면 상황도 바꾸고, '자연스러움'을 최우선으로 둔다.
    """
    kind_label = "외모(첫인상)" if track_kind == "A" else "성격(내면)"
    prompt = f"""아래 오디션 독백 대사에 지적된 문제들이 있습니다. 지적된 문제'만' 고쳐서 다시 쓰세요.

[배우] 외모: {appearance_keywords} / 성격: {self_intro}
[이 트랙] {kind_label} 기반
[제목] {track.get('title','')}
[상황] {track.get('situation','')}
[현재 대사]
{track.get('script','')}

[고쳐야 할 문제]
- """ + "\n- ".join(issues) + f"""

규칙:
- 최우선: '실제 사람이 입으로 말하는 자연스러움'. 어떤 경우에도 문어체·낭독체·로봇 같은 말투로 만들지 말 것. (차분하거나 차가운 톤이어도 반드시 사람의 구어여야 한다.) AI 감성 클리셰("이대로만 ~주세요", "부디 ~해 주시길", "그게 바로 ~입니다", "내 마음속 깊은 곳에서" 등 과잉 문학체·기원체)도 금지.
- '트랙적합성' 또는 '회상 클리셰'가 지적됐으면 → 단어만 비틀지 말고 상황·소재 자체를 바꿔라. 그 외모/성격에 자연스럽게 어울리는 '다른 상황'을 새로 골라라. (시계·사진·편지 등 회상 소재는 버린다.)
- 그 외 국소 문제(호칭 등)는 상황·캐릭터를 유지하고 해당 부분만 고친다.
- 행동·동작·표정 지문은 반드시 괄호 ()로 묶어 '말로 하는 대사'와 구분한다. 예: (얼음을 손바닥에 덜어낸다) 차가운 감촉이 올라온다.
- 길이는 {LEN_MIN}~{LEN_MAX}자를 지킨다. 줄이지 말 것 — {LEN_MIN}자 미만이면 상황·심리 묘사를 더 채워 늘린다.
반드시 JSON으로만: {{"title":"...","situation":"...","objective":"...","script":"..."}}"""
    return gen_json(prompt, system=SYSTEM_INSTRUCTION, temperature=0.7)
