"""사진 → 외모 키워드(2단계 정책 우회) → 외모 기반 대사 검증.
사용법: python vision_test.py <이미지경로>
결과는 vision_result.md (UTF-8)로 저장."""
import os, sys, json, time, re
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])
MODEL = "gemini-2.5-flash-lite"

img_path = sys.argv[1] if len(sys.argv) > 1 else "face.jpg"
with open(img_path, "rb") as f:
    img_bytes = f.read()
ext = img_path.lower().rsplit(".", 1)[-1]
mime = "image/png" if ext == "png" else "image/jpeg"
image_part = types.Part.from_bytes(data=img_bytes, mime_type=mime)


def call(contents, json_mode=False):
    cfg = types.GenerateContentConfig(temperature=0.9,
            response_mime_type="application/json" if json_mode else None)
    for _ in range(5):
        try:
            return client.models.generate_content(model=MODEL, contents=contents, config=cfg)
        except Exception as e:
            m = str(e)
            if any(x in m for x in ("429", "503", "UNAVAILABLE", "RESOURCE_EXHAUSTED")):
                w = re.search(r"retry in ([0-9.]+)", m)
                time.sleep(float(w.group(1)) + 2 if w else 8); continue
            raise
    raise RuntimeError("재시도 초과")


# 1단계: 사진 → 객관적 시각 키워드 (인물 평가/신원 추측 금지)
STAGE1 = ("이 인물 사진을 연기 캐스팅 참고용으로만 봅니다. "
          "보이는 '시각적 특징'을 객관적 키워드 나열로만 묘사하세요. "
          "헤어(길이·색·스타일), 표정, 의상/스타일 톤, 전체적 인상·분위기 위주로. "
          "단, 인물에 대한 평가(예쁘다·차갑다 등)나 신원·정확한 나이·감정 단정은 하지 말고, "
          "눈에 보이는 시각 정보만 담담히 키워드로 적으세요.")
r1 = call([image_part, STAGE1])
stage1_text = (r1.text or "").strip()
refused = (not stage1_text) or any(w in stage1_text for w in ("죄송", "도와드릴 수 없", "can't", "cannot", "unable"))

# 2단계: 키워드 → 외모 기반 대사
STAGE2 = f"""다음은 한 배우 사진에서 뽑은 객관적 외모 키워드입니다.
[외모 키워드]
{stage1_text}

이 첫인상·외모 분위기에 어울리는 오디션용 독백 대사 하나를 창작하세요.
- 한국어, 말로 1~2분(대략 350~550자)
- 회상·추억물 금지, 지금 벌어지는 현재형 상황으로
JSON 형식: {{"title": "...", "setup": "...", "script": "...", "fit_reason": "..."}}"""
d = json.loads(call(STAGE2, json_mode=True).text)

out = []
out.append(f"# Vision 2단계 검증 결과 (model={MODEL})\n")
out.append(f"- 이미지: `{os.path.basename(img_path)}`\n")
out.append("## 1단계 — 사진 → 객관적 외모 키워드\n")
out.append(("⚠️ 정책 거부/거부성 응답 의심" if refused else "✅ 정상 (객관적 키워드 추출, 거부 없음)") + "\n")
out.append(stage1_text + "\n")
out.append("## 2단계 — 키워드 → 외모 기반 대사\n")
out.append(f"### {d['title']} ({len(d['script'])}자)")
out.append(f"*상황: {d['setup']}*\n")
out.append(d["script"])
out.append(f"\n> 어울리는 이유: {d['fit_reason']}\n")

with open("vision_result.md", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("VISION OK | refused =", refused)
