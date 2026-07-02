"""사진 → 외모 키워드 추출 (Vision 2단계 정책 우회).

인물 평가가 아니라 '객관적 시각 특징'만 한 줄(콤마)로 추출 → 대사 생성에 사용.
"""
import os
import time
import re
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(Path(__file__).parent / ".env")
_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
MODEL = "gemini-2.5-flash-lite"

_STAGE1 = (
    "이 인물 사진을 연기 캐스팅 참고용으로만 봅니다. "
    "보이는 '시각적 특징'을 객관적 키워드 한 줄(쉼표로 구분)로만 답하세요. "
    "헤어(길이·색·스타일), 표정, 의상/스타일 톤, 전체적 인상·분위기 위주로. "
    "단, 인물 평가(예쁘다·차갑다 등)나 신원·정확한 나이·감정 단정은 하지 말고, "
    "눈에 보이는 시각 정보만 담담히 적으세요. 설명 문장 없이 키워드만."
)


_RATE_LIMIT_ERRORS = ("429", "503", "UNAVAILABLE", "RESOURCE_EXHAUSTED")
_MAX_SLEEP = 10   # Gemini retry-after가 길어도 최대 10초만 대기


def extract_keywords(image_bytes: bytes, mime_type: str = "image/jpeg") -> str:
    """사진 바이트 → 객관적 외모 키워드 문자열."""
    part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
    for _ in range(3):
        try:
            r = _client.models.generate_content(model=MODEL, contents=[part, _STAGE1])
            return (r.text or "").strip()
        except Exception as e:
            msg = str(e)
            if any(x in msg for x in _RATE_LIMIT_ERRORS):
                m = re.search(r"retry in ([0-9.]+)", msg)
                time.sleep(min(float(m.group(1)) + 1 if m else 8, _MAX_SLEEP))
                continue
            raise
    raise RuntimeError("rate_limit")
