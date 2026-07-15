"""시뮬레이터 STEP 2-a — 면접관 프롬프트 멀티턴 시뮬레이션 + 자동 판정.

validation_agent.py의 _gen_json(캐시·429 재시도 포함)을 그대로 재사용한다.
GENAI_CACHE=1 이면 동일 입력(모델·시스템·히스토리·temperature)은 캐시에서 읽어 호출 0회.

실행:
    prompt_test 폴더에서
    python simulator_run.py                 # easy/medium/hard x strong/weak, 총 6개 대화
    python simulator_run.py easy strong      # 특정 조합만 (한도 절약용 빠른 테스트)
    GENAI_CACHE=1 python simulator_run.py    # 캐시 사용(반복 실행 시 호출 0회)
"""
import os, sys, json, time, re, hashlib

from google import genai
from google.genai import types
from dotenv import load_dotenv
from simulator_prompts import (
    build_interviewer_system,
    build_opening_user_turn,
    build_actor_system,
    DIFFICULTY,
    ACTOR_STYLES,
    FIXTURE_SCRIPT,
)

MODEL = "gemini-2.5-flash-lite"
MAX_TURNS_HARD_CAP = 8  # 모델이 done을 안 내려도 강제 종료하는 안전장치

load_dotenv()
_client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

# validation_agent.py와 동일한 캐시 래퍼(입력 해시 → 파일). 그쪽은 임포트 시 sys.argv를
# 읽어 PERSONAS를 슬라이스하므로(CLI 인자 충돌) 여기서는 독립시켜 재사용한다.
_CACHE_ON = os.environ.get("GENAI_CACHE") == "1"
_CACHE_DIR = ".genai_cache"


def _parse_json(text):
    s = (text or "").strip()
    if s.startswith("```"):
        s = re.sub(r"^```[a-zA-Z]*\s*", "", s)
        s = re.sub(r"\s*```$", "", s).strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        i = s.find("{")
        if i == -1:
            raise
        return json.JSONDecoder().raw_decode(s[i:])[0]


def _cache_path(model, contents, system, temperature):
    raw = json.dumps([model, system, contents, temperature], ensure_ascii=False, default=str)
    return os.path.join(_CACHE_DIR, hashlib.sha256(raw.encode("utf-8")).hexdigest() + ".json")


def _gen_json(model, contents, system=None, temperature=0.9, tries=8):
    cfg = types.GenerateContentConfig(
        system_instruction=system,
        response_mime_type="application/json",
        temperature=temperature,
    )
    path = _cache_path(model, contents, system, temperature) if _CACHE_ON else None
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    for _ in range(tries):
        try:
            resp = _client.models.generate_content(model=model, contents=contents, config=cfg)
            data = _parse_json(resp.text)
            if path:
                os.makedirs(_CACHE_DIR, exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            return data
        except Exception as e:
            msg = str(e)
            if any(x in msg for x in ("429", "503", "UNAVAILABLE", "RESOURCE_EXHAUSTED")):
                m = re.search(r"retry in ([0-9.]+)", msg)
                wait = (float(m.group(1)) + 2) if m else 15
                print(f"    한도/과부하 → {wait:.0f}s 대기 후 재시도")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("재시도 초과 — 오늘 한도 소진 가능")


def _to_contents(history):
    """[('user'|'model', text), ...] -> genai contents(list[dict])."""
    return [{"role": role, "parts": [{"text": text}]} for role, text in history]


def run_conversation(difficulty: str, actor_style: str, script: dict = FIXTURE_SCRIPT):
    """면접관 히스토리(면접관=model,배우=user)와 배우 히스토리(배우=model,면접관=user)를
    따로 유지 — 두 롤이 서로 반대 시점에서 채팅을 이어가야 하므로."""
    interviewer_sys = build_interviewer_system(difficulty)
    actor_sys = build_actor_system(actor_style, script)

    opening = build_opening_user_turn(script)
    interviewer_history = [("user", opening)]
    transcript = []  # [(speaker, text)] speaker in {"면접관","배우"}

    for turn in range(MAX_TURNS_HARD_CAP):
        raw = _gen_json(
            MODEL,
            _to_contents(interviewer_history),
            system=interviewer_sys,
            temperature=0.8,
        )
        msg, done = raw.get("message", ""), bool(raw.get("done"))
        interviewer_history.append(("model", json.dumps(raw, ensure_ascii=False)))
        transcript.append(("면접관", msg, done))
        if done:
            break

        # 배우 시점 히스토리: 면접관 발화=user, 배우 자신 답변=model
        actor_history = []
        for spk, text, *_ in transcript:
            actor_history.append(("user" if spk == "면접관" else "model", text))
        actor_raw = _gen_json(MODEL, _to_contents(actor_history), system=actor_sys, temperature=0.9)
        answer = actor_raw.get("answer", "")
        interviewer_history.append(("user", answer))
        transcript.append(("배우", answer, False))
        time.sleep(1)

    return transcript


# ---------- 자동 판정: 대화 로그를 다시 LLM에 보여 난이도·페르소나 일관성 채점 ----------
JUDGE_SYS = (
    "당신은 오디션 시뮬레이터의 '면접관 AI' 품질을 검수하는 QA 담당자입니다. "
    "대화 로그를 읽고 기준별로 OK/NG를 판정하세요. 애매하면 NG 쪽으로."
)


def judge_transcript(difficulty: str, transcript: list) -> dict:
    log_text = "\n".join(f"{spk}: {text}" for spk, text, *_ in transcript)
    guide = DIFFICULTY[difficulty]["guide"]
    prompt = f"""[이 대화에 적용된 난이도 가이드]
{guide}

[대화 로그]
{log_text}

다음 4가지를 각각 OK/NG로 판정하고 근거를 한 줄로 쓰세요.
1) 난이도일치: 실제 면접관의 말투·압박 강도가 위 난이도 가이드와 맞는가.
2) 페르소나일관성: 처음부터 끝까지 같은 한 사람(면접관)처럼 자연스럽게 이어지는가. 인사를 반복하거나 갑자기 태도가 뒤바뀌면 NG.
3) 답변반영: 면접관의 각 질문이 배우의 직전 답변을 반영해 이어지는가 (앵무새처럼 같은 질문 반복이면 NG).
4) 마무리총평: 대화 끝의 총평이 이 대화 내용에 근거해 구체적인가 (뻔한 말만 있으면 NG).

반드시 아래 JSON으로만 답하세요:
{{"난이도일치":{{"status":"OK","근거":""}},"페르소나일관성":{{"status":"OK","근거":""}},"답변반영":{{"status":"OK","근거":""}},"마무리총평":{{"status":"OK","근거":""}}}}"""
    return _gen_json(MODEL, prompt, system=JUDGE_SYS, temperature=0.2)


REPORT = "simulator_result.md"


def main():
    args = sys.argv[1:]
    difficulties = [args[0]] if len(args) >= 1 else list(DIFFICULTY.keys())
    styles = [args[1]] if len(args) >= 2 else list(ACTOR_STYLES.keys())

    lines = [f"# 시뮬레이터 면접관 프롬프트 검증 (model={MODEL})\n"]

    def flush():
        with open(REPORT, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    for difficulty in difficulties:
        for style in styles:
            print(f"▶ {difficulty} x {style}")
            transcript = run_conversation(difficulty, style)
            lines.append(f"## 난이도={DIFFICULTY[difficulty]['label']} / 배우={style}\n")
            for spk, text, *_ in transcript:
                lines.append(f"**{spk}**: {text}\n")
            flush()

            try:
                verdict = judge_transcript(difficulty, transcript)
                time.sleep(1)
            except Exception as e:
                lines.append(f"⚠️ 판정 실패: {e}\n---\n"); flush(); continue

            ng = [f"{k}: {v.get('근거','')}" for k, v in verdict.items() if v.get("status") == "NG"]
            status = "✅ 통과" if not ng else "❌ NG " + " | ".join(ng)
            lines.append(f"**자동판정**: {status}\n")
            lines.append("---\n")
            flush()

    print("DONE →", REPORT)


if __name__ == "__main__":
    main()
