"""대사 생성 — STEP 0 v3(목적·행동 중심) 프롬프트를 백엔드용으로 이식.

외모/성격은 대사에서 직접 언급하지 않고, 구체적 상황 속 인물이 '목적'을 향해
상대를 말로 움직이는 독백을 만든다.
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
    "당신은 한국 연극영화과 오디션용 독백 대사를 쓰는 전문 극작가이자 연기 디렉터입니다. "
    "좋은 오디션 독백은 '인물이 분명한 목적을 가지고, 구체적인 상황 속에서, 상대를 향해 "
    "말로 행동하는 것'입니다. 인물의 외모나 성격을 대사에서 설명하거나 드러내려 하지 마세요. "
    "그것들은 어떤 인물인지와 목적을 어떻게 추구하는지에만 자연스럽게 배어나야 합니다. "
    "기존 희곡·영화 대사를 인용하지 말고 100% 새로 창작하세요."
)

_SCHEMA = """
반드시 아래 JSON 형식으로만 답하세요 (다른 설명 금지):
{
  "track_A_appearance": {
    "title": "대사 제목",
    "situation": "상대(관계) + 전사(직전에 무슨 일) + 지금 상황을 2~3문장으로",
    "objective": "이 인물이 지금 이 말로 이루려는 목적 (행동 동사 한 줄)",
    "script": "독백 본문 (한국어, 말로 1~2분, 약 350~550자)",
    "voice_style": "어조·리듬에 목소리를 어떻게 반영했는지 1줄"
  },
  "track_B_personality": {
    "title": "대사 제목",
    "situation": "상대(관계) + 전사 + 지금 상황을 2~3문장으로",
    "objective": "이 인물이 지금 이 말로 이루려는 목적 (행동 동사 한 줄)",
    "script": "독백 본문 (한국어, 말로 1~2분, 약 350~550자)",
    "voice_style": "어조·리듬에 목소리를 어떻게 반영했는지 1줄"
  }
}
"""


def build_prompt(appearance_keywords: str, self_intro: str, voice_tone: str) -> str:
    return f"""다음은 한 배우의 분석 결과입니다.

[외모 키워드]
{appearance_keywords}

[자기소개 — 성격/내면]
{self_intro}

[목소리·말투]
{voice_tone}

이 배우에게 어울리는 오디션 독백을 두 방향으로 창작하세요.
- track_A_appearance: 외모 첫인상에서 연상되는 인물상을 가진 캐릭터.
- track_B_personality: 실제 성격·내면에서 나오는 인물상을 가진 캐릭터.

[반드시 지킬 작법 규칙 — 가장 중요]
1) 먼저 '주어진 상황'을 분명히 설계하세요: 상대(누구에게 말하는가/관계), 전사(직전에 무슨 일이 있었는가, 왜 지금 이 말을 하는가), 목적(이 인물이 지금 이 말로 무엇을 이루려 하는가 — 행동 동사로), 무엇이 걸려 있는가(stakes).
2) 독백은 그 '목적을 향해 상대를 움직이려는 행동'이어야 합니다. 자기 감정·외모·성격을 설명·소개하는 대사 금지.
3) 외모/성격/목소리 키워드를 대사 안에서 직접 언급하거나 묘사하지 마세요. ('내 차가운 눈빛', '난 원래 애교가 많아' 같은 자기묘사 금지) — 오직 인물이 말하고 행동하는 방식으로만 드러나게.
4) 개연성: 왜 지금 이 말을 하는지 분명하고, 시작 → 전환(turn) → 고조의 흐름이 있어야 합니다. 한 가지 목적에 집중.
5) 회상·추억 클리셰(오래된 물건 보며 떠난 사람 그리워하기) 금지. 지금 벌어지는 현재형 장면으로.
6) 두 트랙은 인물·상황·목적이 뚜렷이 다른 방향이어야 합니다.

[목소리 규칙 — 두 트랙 공통]
'목소리·말투'는 내용이 아니라 전달 스타일(어조·리듬·호흡·단어 선택)을 결정합니다. 두 대사 모두 이 목소리로 자연스럽게 말할 수 있어야 하고, 어울리지 않는 표현은 피하세요. 성격과 목소리가 충돌하면 내용은 성격을, 전달 톤은 목소리를 따르세요.
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
