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
MODEL = "gemini-2.5-flash-lite"   # 반복 검증용(무료 한도 넉넉). 품질 비교는 _compare.py(2.5-flash).

# 노트북에서 PERSONAS / build_prompt / SYSTEM_INSTRUCTION 정의만 재사용 (연결테스트 셀은 제외)
nb = nbformat.read("notebook.ipynb", as_version=4)
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
            if any(x in msg for x in ("429", "503", "UNAVAILABLE", "RESOURCE_EXHAUSTED")):
                m = re.search(r"retry in ([0-9.]+)", msg)
                wait = (float(m.group(1)) + 2) if m else 12
                print(f"  한도/과부하 → {wait:.0f}s 대기 후 재시도")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("재시도 초과 — 오늘 한도 소진 가능")


def char_overlap(a, b):
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0


REPORT = "result.md"
lines = [f"# STEP 0 검증 결과 (v3 목적·행동 중심 · model={MODEL})\n"]


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
    for track, label in [(a, "🅰 외모 기반"), (b, "🅱 성격 기반")]:
        lines.append(f"### {label} — {track['title']} ({len(track['script'])}자)")
        lines.append(f"*상황: {track.get('situation','-')}*")
        lines.append(f"*목적: {track.get('objective','-')}*")
        lines.append(f"*목소리: {track.get('voice_style','-')}*\n")
        lines.append(track["script"])
        lines.append("")
    lines.append("---\n")
    flush()  # 매 페르소나마다 저장
    time.sleep(7)  # 호출 간격: 분당 한도 폭주 방지

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
