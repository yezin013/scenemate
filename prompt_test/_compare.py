"""2.5-flash 품질 비교 — 문제됐던 P2, P5만 생성. (한도 아끼려 2명만)"""
import os, json, time, re, nbformat
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
MODEL = "gemini-2.5-flash"

nb = nbformat.read("notebook.ipynb", as_version=4)
ns = {"client": client, "types": types, "json": json, "MODEL": MODEL}
for i in (4, 6):
    exec(nb.cells[i].source, ns)
PERSONAS, bp, SI = ns["PERSONAS"], ns["build_prompt"], ns["SYSTEM_INSTRUCTION"]


def gen(persona):
    for _ in range(6):
        try:
            r = client.models.generate_content(
                model=MODEL, contents=bp(persona),
                config=types.GenerateContentConfig(
                    system_instruction=SI, response_mime_type="application/json", temperature=0.9))
            return json.loads(r.text)
        except Exception as e:
            m = str(e)
            if any(x in m for x in ("429", "503", "UNAVAILABLE", "RESOURCE")):
                w = re.search(r"retry in ([0-9.]+)", m)
                time.sleep(float(w.group(1)) + 3 if w else 15)
                continue
            raise
    raise RuntimeError("재시도 초과")


out = [f"# 2.5-flash 품질 비교 (P2, P5)\n"]
for idx in (1, 4):
    p = PERSONAS[idx]
    print("생성:", p["name"])
    r = gen(p)
    out.append(f"## {p['name']}\n")
    out.append(f"- 입력 외모: {p['appearance_keywords']}")
    out.append(f"- 입력 성격: {p['self_intro']}")
    out.append(f"- 입력 말투: {p['voice_tone']}\n")
    for k, lab in [("track_A_appearance", "🅰 외모 기반"), ("track_B_personality", "🅱 성격 기반")]:
        t = r[k]
        out.append(f"### {lab} — {t['title']} ({len(t['script'])}자)")
        out.append(f"*상황: {t.get('situation','-')}*")
        out.append(f"*목적: {t.get('objective','-')}*")
        out.append(f"*목소리: {t.get('voice_style','-')}*\n")
        out.append(t["script"])
        out.append("")
    out.append("---\n")
    time.sleep(10)

open("compare_25flash.md", "w", encoding="utf-8").write("\n".join(out))
print("DONE")
