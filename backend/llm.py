"""Gemini 호출 공통 모듈 — 클라이언트 + JSON 응답 래퍼(429/503 재시도).

생성(generator)·판정(judge)·교정(fixer)이 공유한다.
(기존 generator.py·vision.py는 각자 클라이언트를 만들지만, 신규 judge/fixer는 이 공용 헬퍼를 쓴다.)
"""
import os
import json
import re
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(Path(__file__).parent / ".env")
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
MODEL = "gemini-2.5-flash-lite"   # 개발용. 최종 품질은 gemini-2.5-flash로.


def _parse_json(text):
    """모델이 코드펜스/잡설을 덧붙여도 첫 JSON 객체만 견고하게 뽑아낸다."""
    s = (text or "").strip()
    if s.startswith("```"):                          # ```json ... ``` 펜스 제거
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        i = s.find("{")                              # 앞 잡설 건너뛰고
        if i == -1:
            raise
        return json.JSONDecoder().raw_decode(s[i:])[0]  # 첫 JSON만, 뒤 잡음 무시


_MAX_SLEEP = 10


def gen_json(contents, system=None, temperature=0.9, model=MODEL, tries=3):
    """JSON 응답 생성 공통 래퍼 — 429(한도)·503(과부하)은 최대 10초 대기 후 재시도."""
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        temperature=temperature,
    )
    for _ in range(tries):
        try:
            resp = client.models.generate_content(model=model, contents=contents, config=cfg)
            return _parse_json(resp.text)
        except Exception as e:
            msg = str(e)
            if any(x in msg for x in ("429", "503", "UNAVAILABLE", "RESOURCE_EXHAUSTED")):
                m = re.search(r"retry in ([0-9.]+)", msg)
                time.sleep(min(float(m.group(1)) + 1 if m else 8, _MAX_SLEEP))
                continue
            raise
    raise RuntimeError("rate_limit")
