"""대사 분석 — 레이어별 힌트 + AI 전체 분석 (Gemini)."""
from llm import gen_json

LAYER_LABELS = {
    "subtext": "서브텍스트",
    "action_verb": "행동 동사",
    "emotion_arc": "감정선 흐름",
    "context": "상황·전사",
    "character_bg": "인물 배경",
    "relationship": "관계 분석",
    "real_goal": "진짜 목표",
}

_HINT_SYSTEM = """당신은 연기 분석 코치입니다. 사용자가 독백 대사를 특정 레이어로 분석하고 있습니다.
사용자의 초안을 검토하고, 더 깊이 탐구하도록 이끄는 힌트를 주세요.
답을 직접 주지 말고, 생각을 자극하는 질문이나 새로운 관점을 제안하세요. 2~3문장으로 간결하게.
JSON: {"hint": "..."}"""

_FULL_SYSTEM = """당신은 전문 연기 분석가입니다. 주어진 독백 대사를 7개 레이어로 분석하세요.
각 레이어는 2~4문장, 구체적이고 전문적으로.
JSON:
{
  "subtext": "...",
  "action_verb": "...",
  "emotion_arc": "...",
  "context": "...",
  "character_bg": "...",
  "relationship": "...",
  "real_goal": "..."
}"""


def _script_info(script_text: str, title: str | None, setup: str | None) -> str:
    return f"제목: {title or '없음'}\n상황: {setup or '없음'}\n\n대사:\n{script_text}"


def get_hint(script_text: str, title: str | None, setup: str | None, layer: str, draft: str) -> str:
    label = LAYER_LABELS.get(layer, layer)
    prompt = (
        f"{_script_info(script_text, title, setup)}\n\n"
        f"[분석 레이어: {label}]\n"
        f"사용자 초안: {draft or '(미작성)'}\n\n"
        "이 레이어에 대한 힌트를 주세요."
    )
    result = gen_json(prompt, system=_HINT_SYSTEM, temperature=0.7)
    return result.get("hint", "")


def get_full_analysis(script_text: str, title: str | None, setup: str | None) -> dict:
    return gen_json(_script_info(script_text, title, setup), system=_FULL_SYSTEM, temperature=0.7)
