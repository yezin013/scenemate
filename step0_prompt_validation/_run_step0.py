"""노트북의 정의(페르소나/프롬프트)를 재사용해 v2 검증을 돌린다.
- 429(무료 한도) 만나면 안내된 시간만큼 대기 후 재시도
- 페르소나 1개 생성될 때마다 리포트를 즉시 저장(중간에 죽어도 손실 X)
"""
import os, json, time, re, nbformat
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
MODEL = "gemini-2.5-flash-lite"   # 무료 한도 가장 넉넉한 모델로 검증

# 노트북에서 PERSONAS / build_prompt / SYSTEM_INSTRUCTION 정의만 재사용 (연결테스트 셀은 제외)
nb = nbformat.read("dialogue_prompt_test.ipynb", as_version=4)
ns = {"client": client, "types": types, "json": json, "MODEL": MODEL}
for idx in (4, 6):
    exec(nb.cells[idx].source, ns)
PERSONAS = ns["PERSONAS"]
build_prompt = ns["build_prompt"]
SYSTEM_INSTRUCTION = ns["SYSTEM_INSTRUCTION"]


def gen(persona, temperature=0.9, tries=5):
    for _ in range(tries):
        try:
            resp = client.models.generate_content(
                model=MODEL,
                contents=build_prompt(persona),
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_mime_type="application/json",
                    temperature=temperature,
                ),
            )
            return json.loads(resp.text)
        except Exception as e:
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                m = re.search(r"retry in ([0-9.]+)", msg)
                wait = (float(m.group(1)) + 2) if m else 20
                print(f"  429 한도 → {wait:.0f}s 대기 후 재시도")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("재시도 초과 — 오늘 한도 소진 가능")


def char_overlap(a, b):
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0


REPORT = "step0_report.md"
lines = [f"# STEP 0 검증 리포트 (v2 · model={MODEL})\n"]


def flush():
    with open(REPORT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


results = []
for p in PERSONAS:
    print("생성 중:", p["name"])
    try:
        r = gen(p)
    except Exception as e:
        lines.append(f"## {p['name']}\n\n⚠️ 실패: {e}\n"); flush(); continue
    results.append((p, r))
    a, b = r["track_A_appearance"], r["track_B_personality"]
    lines.append(f"## {p['name']}\n")
    lines.append(f"- 입력 외모: {p['appearance_keywords']}")
    lines.append(f"- 입력 성격: {p['self_intro']}")
    lines.append(f"- 입력 말투: {p['voice_tone']}\n")
    lines.append(f"### 🅰 외모 기반 — {a['title']} ({len(a['script'])}자)")
    lines.append(f"*상황: {a['setup']}*")
    lines.append(f"*목소리 반영: {a.get('voice_style','-')}*\n")
    lines.append(a["script"])
    lines.append(f"\n> 어울리는 이유: {a['fit_reason']}\n")
    lines.append(f"### 🅱 성격 기반 — {b['title']} ({len(b['script'])}자)")
    lines.append(f"*상황: {b['setup']}*")
    lines.append(f"*목소리 반영: {b.get('voice_style','-')}*\n")
    lines.append(b["script"])
    lines.append(f"\n> 어울리는 이유: {b['fit_reason']}\n")
    lines.append("---\n")
    flush()  # 매 페르소나마다 저장
    time.sleep(4)

# 자동 체크
lines.append("## 자동 체크\n")
lines.append("| 페르소나 | A길이 | B길이 | 문자겹침도(낮을수록 다른 방향) |")
lines.append("|---|---|---|---|")
for p, r in results:
    a = r["track_A_appearance"]["script"]
    b = r["track_B_personality"]["script"]
    lines.append(f"| {p['name']} | {len(a)} | {len(b)} | {char_overlap(a, b):.2f} |")
lines.append("")
flush()

print("DONE", len(results), "personas")
