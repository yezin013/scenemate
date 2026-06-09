"""notebook.ipynb 생성용 빌더. 한 번 실행 후 지워도 됨.

설계 v3: 목적/행동 중심. 외모·성격을 대사에서 '묘사'하지 말고,
구체적 상황 속 인물이 '목적'을 향해 말로 행동하게. (키워드 억지 삽입 방지)
"""
import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []
md = lambda s: cells.append(nbf.v4.new_markdown_cell(s))
code = lambda s: cells.append(nbf.v4.new_code_cell(s))

md("""# SceneMate · STEP 0 — 대사 프롬프트 검증 (v3: 목적·행동 중심)

**바뀐 점:** 외모/성격을 대사에 끼워넣지 않는다. 대신 *구체적 상황 속에서 인물이 분명한 목적을 향해 상대를 말로 움직이는* 독백을 만든다.

**판정 기준**
1. 인물의 **목적**이 분명한가 (왜 이 말을 하는가)
2. **상황·전사·상대**가 잡혀 개연성이 있는가 (시작→전환→고조)
3. 외모/성격 키워드를 **억지로 언급하지 않는가** (행동/태도로만 드러나는가)
4. 두 트랙(외모 인물상 / 성격 인물상)이 뚜렷이 다른 방향인가
5. 길이가 오디션 독백에 맞는가 (말로 1~2분)
6. 목소리가 전달 스타일에 반영됐는가""")

md("""## 1. 환경 셋업 & 연결 테스트
`.env` 에 `GOOGLE_API_KEY` 필요.""")

code("""import os, json, time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.environ.get("GOOGLE_API_KEY", "")
assert API_KEY and "여기에" not in API_KEY, ".env 에 본인 Gemini API 키를 넣어주세요!"

client = genai.Client(api_key=API_KEY)
MODEL = "gemini-2.5-flash-lite"   # 무료 한도 넉넉. 최종 품질은 2.5-flash로 비교.

resp = client.models.generate_content(model=MODEL, contents="한국어로 '연결 성공'이라고만 답해줘.")
print("Gemini 응답:", resp.text.strip())""")

md("""## 2. mock 입력 — 페르소나 6개
P1: 외모↔말투 상충 / P2: 외모↔성격 온도차 / P6: 성격↔목소리 상충.""")

code('''PERSONAS = [
    {
        "name": "P1 · 차가운 외모 + 애교 말투 (외모↔말투 상충 ★)",
        "appearance_keywords": "또렷한 이목구비, 날카로운 눈매, 단정하게 넘긴 검은 머리, 모노톤 셔츠, 무표정에 가까운 차분한 표정, 도시적이고 서늘한 분위기",
        "self_intro": "겉으로는 차가워 보인다는 말을 많이 듣지만 실제로는 애교가 많고 감정 표현이 풍부해요. 내향적이지만 무대에서는 에너지가 확 올라가요.",
        "voice_tone": "말끝이 부드럽게 올라가고 톤이 밝음. 말 사이에 웃음이 섞이고 애교 섞인 말투. 속도는 약간 빠른 편.",
    },
    {
        "name": "P2 · 따뜻한 외모 + 냉소적/날 선 성격 (외모↔성격 온도차 ★)",
        "appearance_keywords": "둥근 인상, 부드러운 눈매, 자연스러운 갈색 웨이브, 베이지 니트, 잔잔한 미소, 편안하고 친근한 분위기",
        "self_intro": "겉보기엔 순하고 편안해 보인다는 말을 듣지만, 실제로는 할 말은 다 하는 편이에요. 불합리한 건 못 참고 직설적이고요. 세상에 큰 기대가 없어서 좀 냉소적으로 보는 편이라, 사람들이 의외라고 놀라요.",
        "voice_tone": "차분하고 또박또박하지만 약간 건조하고 무심한 톤, 감정을 쉽게 드러내지 않고 단정적으로 말함.",
    },
    {
        "name": "P3 · 중성적 외모 + 발랄/장난기",
        "appearance_keywords": "중성적인 분위기, 짧은 단발, 큰 눈, 캐주얼한 오버핏 셔츠, 장난스러운 표정, 자유롭고 경쾌한 인상",
        "self_intro": "에너지가 넘치고 장난을 좋아해요. 분위기 메이커라는 말을 자주 듣고, 코믹한 역할을 좋아해요.",
        "voice_tone": "높고 통통 튀는 톤, 리듬감 있는 말투, 빠른 속도, 감탄사가 많음.",
    },
    {
        "name": "P4 · 강렬한 외모 + 내성적 말투",
        "appearance_keywords": "강한 눈빛, 짙은 눈썹, 각진 턱선, 블랙 가죽 재킷, 다부진 인상, 카리스마 있는 분위기",
        "self_intro": "겉모습은 세 보이는데 사실 조용하고 낯을 많이 가려요. 말수가 적고 생각이 많은 편이에요.",
        "voice_tone": "조용하고 낮은 목소리, 말수 적고 머뭇거림이 있음, 느리고 신중한 말투.",
    },
    {
        "name": "P5 · 청순한 외모 + 당찬 말투",
        "appearance_keywords": "맑은 피부, 큰 눈망울, 긴 생머리, 화이트 원피스, 청순하고 여린 인상",
        "self_intro": "여려 보인다는 말을 듣지만 성격은 당차고 자기 주장이 분명해요. 주도적인 역할을 좋아해요.",
        "voice_tone": "맑고 또렷한 목소리, 자신감 있는 어조, 단정적인 말투, 분명한 발음.",
    },
    {
        "name": "P6 · 애교 성격 + 허스키 목소리 (성격↔목소리 상충 ★)",
        "appearance_keywords": "동그란 눈, 부드러운 단발, 파스텔톤 가디건, 친근하고 귀여운 인상",
        "self_intro": "장난도 많고 애교도 많은 편이에요. 사람들에게 먼저 다가가 분위기를 띄우는 걸 좋아하고, 감정 표현이 솔직해요.",
        "voice_tone": "낮고 허스키한 목소리, 약간 쉰 듯한 음색, 느릿하고 무게감 있는 말투.",
    },
]

print(f"페르소나 {len(PERSONAS)}개 준비됨")
for p in PERSONAS:
    print(" -", p["name"])''')

md("""## 3. 프롬프트 설계 v3 (목적·행동 중심)

- 외모/성격은 '어떤 인물이고 목적을 어떻게 추구하는가'에만 반영 → **대사에서 직접 언급 금지**
- 먼저 상황(상대·전사·목적·stakes) 설계 → 그 목적을 향해 말로 행동하는 독백
- 출력에 situation/objective를 명시해 개연성을 눈으로 확인""")

code('''SYSTEM_INSTRUCTION = (
    "당신은 한국 연극영화과 오디션용 독백 대사를 쓰는 전문 극작가이자 연기 디렉터입니다. "
    "좋은 오디션 독백은 '인물이 분명한 목적을 가지고, 구체적인 상황 속에서, 상대를 향해 말로 행동하는 것'입니다. "
    "인물의 외모나 성격을 대사에서 설명하거나 드러내려 하지 마세요. 그것들은 어떤 인물인지와 "
    "목적을 어떻게 추구하는지에만 자연스럽게 배어나야 합니다. "
    "기존 희곡·영화 대사를 인용하지 말고 100% 새로 창작하세요."
)

OUTPUT_SCHEMA_DESC = """
반드시 아래 JSON 형식으로만 답하세요 (다른 설명 금지):
{
  "track_A_appearance": {
    "title": "대사 제목",
    "situation": "상대(관계) + 전사(직전에 무슨 일이 있었는가) + 지금 상황을 2~3문장으로",
    "objective": "이 인물이 지금 이 말로 이루려는 목적 (행동 동사로 한 줄: 설득한다/추궁한다/붙잡는다/거절한다/감춘다 등)",
    "script": "독백 본문 (한국어, 말로 1~2분, 약 350~550자)",
    "voice_style": "어조·리듬에 목소리를 어떻게 반영했는지 1줄"
  },
  "track_B_personality": {
    "title": "대사 제목",
    "situation": "상대(관계) + 전사 + 지금 상황을 2~3문장으로",
    "objective": "이 인물이 지금 이 말로 이루려는 목적 (행동 동사로 한 줄)",
    "script": "독백 본문 (한국어, 말로 1~2분, 약 350~550자)",
    "voice_style": "어조·리듬에 목소리를 어떻게 반영했는지 1줄"
  }
}
"""

def build_prompt(persona: dict) -> str:
    return f"""다음은 한 배우의 분석 결과입니다.

[외모 키워드]
{persona['appearance_keywords']}

[자기소개 — 성격/내면]
{persona['self_intro']}

[목소리·말투]
{persona['voice_tone']}

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
{OUTPUT_SCHEMA_DESC}"""

def generate_dialogues(persona: dict, temperature: float = 0.9) -> dict:
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

print("프롬프트/생성 함수 준비 완료")''')

md("""## 4. 빠른 테스트 — 상충 케이스 P1, P6""")

code('''def show_result(persona_name: str, result: dict):
    print("=" * 70)
    print("페르소나:", persona_name)
    for key, label in [("track_A_appearance", "\U0001F170 외모 기반"),
                       ("track_B_personality", "\U0001F171 성격 기반")]:
        t = result[key]
        body = t["script"]
        print("\\n" + "-" * 70)
        print(f"{label}  |  {t['title']}  ({len(body)}자)")
        print("상황:", t.get("situation", "-"))
        print("목적:", t.get("objective", "-"))
        print("목소리:", t.get("voice_style", "-"))
        print()
        print(body)
    print("=" * 70)

for idx in (0, 5):
    show_result(PERSONAS[idx]["name"], generate_dialogues(PERSONAS[idx]))
    time.sleep(2)''')

md("""## 5. 전체 페르소나 6개 생성""")

code('''results = []
for p in PERSONAS:
    print("생성 중:", p["name"])
    try:
        r = generate_dialogues(p)
        results.append((p, r))
    except Exception as e:
        print("  ⚠️ 실패:", e)
    time.sleep(2)

print(f"\\n완료: {len(results)}/{len(PERSONAS)}\\n")
for p, r in results:
    show_result(p["name"], r)''')

md("""## 6. 자동 체크 (두 트랙 차이)""")

code('''def char_overlap(a: str, b: str) -> float:
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0

print(f"{'페르소나':<40} A길이  B길이  문자겹침도")
for p, r in results:
    a = r["track_A_appearance"]["script"]
    b = r["track_B_personality"]["script"]
    print(f"{p['name'][:38]:<40} {len(a):>4}  {len(b):>4}   {char_overlap(a, b):.2f}")''')

md("""## 7. 다음 단계
- 판정 기준 6가지로 직접 읽고 합격/불합격 결정.
- 불합격이면 → 이 노트북(또는 build.py)의 프롬프트만 고쳐 반복.
- 합격이면 → `backend/generator.py`에 동일 프롬프트 반영.""")

nb["cells"] = cells
nb["metadata"] = {
    "kernelspec": {"display_name": "Python 3 (scenemate)", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.12"},
}

with open("notebook.ipynb", "w", encoding="utf-8") as f:
    nbf.write(nb, f)
print("notebook.ipynb 생성 완료, 셀", len(cells), "개")
