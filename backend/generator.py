"""대사 생성 — STEP 0에서 검증한 프롬프트를 백엔드용으로 이식.

외모/성격 = 내용 축, 목소리 = 두 트랙 공통 전달 스타일.
"""
import os
import json
import time
import re
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(Path(__file__).parent / ".env")
_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
MODEL = "gemini-2.5-flash-lite"  # 개발용: 무료 한도 넉넉. 최종 품질은 2.5-flash로 비교.

SYSTEM_INSTRUCTION = (
    "당신은 한국 연극영화과 오디션을 위한 '독백 대사'를 창작하는 전문 극작가입니다. "
    "배우의 외모·성격·목소리 분석 결과를 바탕으로 오디션용 독백을 새로 창작합니다. "
    "외모와 성격은 대사의 '내용/캐릭터'를 결정하고, 목소리·말투는 대사의 '전달 스타일'"
    "(어조·리듬·호흡·단어 선택)을 결정합니다. "
    "기존 희곡이나 영화 대사를 인용하지 말고 100% 새로 창작하세요."
)

_SCHEMA = """
반드시 아래 JSON 형식으로만 답하세요 (다른 설명 금지):
{
  "track_A_appearance": {
    "title": "대사 제목",
    "setup": "이 대사의 상황 설정 한 줄",
    "script": "독백 대사 본문 (한국어, 말로 1~2분 분량, 대략 350~550자)",
    "fit_reason": "이 대사가 외모/첫인상과 왜 어울리는지 1~2줄",
    "voice_style": "이 대사의 어조·리듬에 배우의 목소리를 어떻게 반영했는지 1줄"
  },
  "track_B_personality": {
    "title": "대사 제목",
    "setup": "이 대사의 상황 설정 한 줄",
    "script": "독백 대사 본문 (한국어, 말로 1~2분 분량, 대략 350~550자)",
    "fit_reason": "이 대사가 성격/내면과 왜 어울리는지 1~2줄",
    "voice_style": "이 대사의 어조·리듬에 배우의 목소리를 어떻게 반영했는지 1줄"
  }
}
"""


def build_prompt(appearance_keywords: str, self_intro: str, voice_tone: str) -> str:
    return f"""다음은 한 배우의 분석 결과입니다.

[외모 키워드 — 사진의 객관적 시각 특징]
{appearance_keywords}

[자기소개 — 성격/내면]
{self_intro}

[목소리·말투 분석]
{voice_tone}

이 배우를 위해 오디션용 독백 대사를 두 가지 방향으로 창작하세요.

- track_A_appearance (외모 기반): 사진의 '첫인상·외모 분위기'에 충실한 캐릭터의 대사.
- track_B_personality (성격 기반): 실제 내면·성격에 충실한 캐릭터의 대사.

[외모 트랙(track_A) 다양성 규칙]
- 외모 키워드의 구체적인 분위기에서 출발해 캐릭터와 상황을 정하세요.
- 금지: 오래된 물건(시계·사진·앨범·인형·편지 등)을 보며 과거나 떠난 사람을 추억하는 감상적 회상 독백.
- 회상에 기대지 말고, 지금 벌어지는 사건 속에서 인물이 행동·결정·대립·설득·고백하는 현재형 상황을 택하세요.
- 외모 분위기에 맞는 장르를 적극 활용하고, 매번 다른 장르·상황이 나오게 하세요.

[목소리 규칙 — 두 트랙 공통]
'목소리·말투'는 대사의 내용이 아니라 전달 스타일을 결정합니다.
두 대사 모두 이 목소리로 자연스럽게 말할 수 있도록 어조·문장 리듬·호흡·단어 선택을 맞추세요.
목소리에 어울리지 않는 표현(예: 허스키한 목소리에 과한 애교체)은 피하세요.
성격과 목소리가 상충하면, 내용은 성격을 살리되 전달 톤은 목소리에 맞게 조정하세요.

두 트랙은 캐릭터·감정 방향이 뚜렷하게 달라야 합니다.
{_SCHEMA}"""


def generate_dialogues(appearance_keywords: str, self_intro: str,
                       voice_tone: str, temperature: float = 0.9) -> dict:
    """입력 3종 → {track_A_appearance, track_B_personality} 딕셔너리 반환."""
    prompt = build_prompt(appearance_keywords, self_intro, voice_tone)
    for _ in range(5):
        try:
            resp = _client.models.generate_content(
                model=MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    temperature=temperature,
                ),
            )
            return json.loads(resp.text)
        except Exception as e:
            msg = str(e)
            if any(x in msg for x in ("429", "503", "UNAVAILABLE", "RESOURCE_EXHAUSTED")):
                m = re.search(r"retry in ([0-9.]+)", msg)
                time.sleep(float(m.group(1)) + 2 if m else 8)
                continue
            raise
    raise RuntimeError("생성 재시도 초과 (한도/과부하 가능)")
