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
5. 길이가 오디션 독백에 맞는가 (말로 1~2분)""")

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
P1: 외모↔말투 상충 / P2: 외모↔성격 온도차 / P6: 외모↔성격 상충.""")

code('''PERSONAS = [
    {
        "name": "P1 · 차가운 외모 + 애교 말투 (외모↔말투 상충 ★)",
        "appearance_keywords": "또렷한 이목구비, 날카로운 눈매, 단정하게 넘긴 검은 머리, 모노톤 셔츠, 무표정에 가까운 차분한 표정, 도시적이고 서늘한 분위기",
        "self_intro": "겉으로는 차가워 보인다는 말을 많이 듣지만 실제로는 애교가 많고 감정 표현이 풍부해요. 내향적이지만 무대에서는 에너지가 확 올라가요.",
    },
    {
        "name": "P2 · 따뜻한 외모 + 냉소적/날 선 성격 (외모↔성격 온도차 ★)",
        "appearance_keywords": "둥근 인상, 부드러운 눈매, 자연스러운 갈색 웨이브, 베이지 니트, 잔잔한 미소, 편안하고 친근한 분위기",
        "self_intro": "겉보기엔 순하고 편안해 보인다는 말을 듣지만, 실제로는 할 말은 다 하는 편이에요. 불합리한 건 못 참고 직설적이고요. 세상에 큰 기대가 없어서 좀 냉소적으로 보는 편이라, 사람들이 의외라고 놀라요.",
    },
    {
        "name": "P3 · 중성적 외모 + 발랄/장난기",
        "appearance_keywords": "중성적인 분위기, 짧은 단발, 큰 눈, 캐주얼한 오버핏 셔츠, 장난스러운 표정, 자유롭고 경쾌한 인상",
        "self_intro": "에너지가 넘치고 장난을 좋아해요. 분위기 메이커라는 말을 자주 듣고, 코믹한 역할을 좋아해요.",
    },
    {
        "name": "P4 · 강렬한 외모 + 내성적 말투",
        "appearance_keywords": "강한 눈빛, 짙은 눈썹, 각진 턱선, 블랙 가죽 재킷, 다부진 인상, 카리스마 있는 분위기",
        "self_intro": "겉모습은 세 보이는데 사실 조용하고 낯을 많이 가려요. 말수가 적고 생각이 많은 편이에요.",
    },
    {
        "name": "P5 · 청순한 외모 + 당찬 말투",
        "appearance_keywords": "맑은 피부, 큰 눈망울, 긴 생머리, 화이트 원피스, 청순하고 여린 인상",
        "self_intro": "여려 보인다는 말을 듣지만 성격은 당차고 자기 주장이 분명해요. 주도적인 역할을 좋아해요.",
    },
    {
        "name": "P6 · 애교 성격 + 차분한 외모 (외모↔성격 상충 ★)",
        "appearance_keywords": "동그란 눈, 부드러운 단발, 파스텔톤 가디건, 친근하고 귀여운 인상",
        "self_intro": "장난도 많고 애교도 많은 편이에요. 사람들에게 먼저 다가가 분위기를 띄우는 걸 좋아하고, 감정 표현이 솔직해요.",
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
    "script": "독백 본문 (한국어, 말로 1~2분, 약 350~550자)"
  },
  "track_B_personality": {
    "title": "대사 제목",
    "situation": "상대(관계) + 전사 + 지금 상황을 2~3문장으로",
    "objective": "이 인물이 지금 이 말로 이루려는 목적 (행동 동사로 한 줄)",
    "script": "독백 본문 (한국어, 말로 1~2분, 약 350~550자)"
  }
}
"""

def build_prompt(persona: dict) -> str:
    return f"""다음은 한 배우의 분석 결과입니다.

[외모 키워드]
{persona['appearance_keywords']}

[자기소개 — 성격/내면]
{persona['self_intro']}

이 배우에게 어울리는 오디션 독백을 두 방향으로 창작하세요.
- track_A_appearance: 사진을 처음 본 관객이 받는 '첫인상'(예: 청순하고 여린 / 차갑고 도시적 / 강렬하고 카리스마 있는)을 실제로 풍기는 인물. 그 첫인상이 인물의 분위기·태도에서 분명히 느껴져야 합니다(단, 외모를 대사로 설명하진 말 것). 드라마는 그 인상에 어울리거나, 그 인상을 살짝 비트는 방향으로 잡으세요. ※ 외모와 동떨어진 엉뚱한 설정(예: 사물·피조물이 말하기 등)으로 빠지지 마세요.
- track_B_personality: 자기소개의 실제 성격·내면에서 나오는 인물. 첫인상과 달라도 됩니다.

[반드시 지킬 작법 규칙 — 가장 중요]
1) 먼저 '주어진 상황'을 분명히 설계하세요: 상대(누구에게 말하는가/관계), 전사(직전에 무슨 일이 있었는가, 왜 지금 이 말을 하는가), 목적(이 인물이 지금 이 말로 무엇을 이루려 하는가 — 행동 동사로), 무엇이 걸려 있는가(stakes).
2) 독백은 그 '목적을 향해 상대를 움직이려는 행동'이어야 합니다. 자기 감정·외모·성격을 설명·소개하는 대사 금지.
3) 외모·성격 키워드를 대사 안에서 직접 언급하거나 묘사하지 마세요. ('내 차가운 눈빛', '난 원래 애교가 많아' 같은 자기묘사 금지) — 오직 인물이 말하고 행동하는 방식으로만 드러나게.
4) 개연성: 왜 지금 이 말을 하는지 분명하고, 시작 → 전환(turn) → 고조의 흐름이 있어야 합니다. 한 가지 목적에 집중.
5) 다음 클리셰 금지: ① 회상·추억물(오래된 물건—사진·앨범·편지·꽃다발 등—을 보며 과거나 떠난 사람을 그리워하기), ② 연인과의 이별·재회에 매달리는 장면의 반복. 지금 벌어지는 현재형 사건으로 가세요.
6) 트랙별 관계·장르 강제 배정: track_A와 track_B는 '상대와의 관계'도, '장르'도 서로 달라야 합니다. 두 트랙 모두 연인 관계로 가지 마세요(최소 한 트랙은 비연애). 관계는 다양하게(가족·직장/사회·친구·선후배·낯선 사람·공적 갈등 등), 장르도 서로 다르게 배정하세요. 장르 예: 가족극, 직장/사회극, 스릴러/범죄, 의료, 법정, 코미디, 생존/재난, 청춘 성장물 등.
7) 호칭·말투(존댓말/반말) 일관성 — 매우 중요: situation에서 정한 상대와의 관계에 맞는 말투를 처음부터 끝까지 일관되게 쓰세요.
   - 친구·후배·동생 등 또래나 아랫사람 → 반말 + 이름("민지야")이나 "너". 절대 존댓말 쓰지 말 것.
   - 손위지만 가까운 사이(오빠·언니·형·누나·선배 등) → 반말을 쓰더라도 상대를 "너"라고 부르지 말고, 그 호칭(오빠/형/선배 등)이나 이름으로 부르세요.
   - 윗사람·낯선 사람·공적 관계 → 존댓말 + 적절한 호칭(선생님/직책 등).
   - 한 대사 안에서 존댓말↔반말을 섞거나, 부르는 말을 도중에 바꾸지(이름→"당신") 마세요.
   - "당신"은 한국어 일상에서 어색하거나 다투는 뉘앙스라 특별한 의도가 없으면 쓰지 말고, 이름·"너"·관계 호칭으로 부르세요.
   - situation에 적은 상대(예: "후배 민지")와 script에서 실제로 부르는 호칭·말투가 반드시 일치해야 합니다.
   - 말투뿐 아니라 '태도'도 관계의 위계에 맞아야 합니다. 손윗사람·스승·상사에게는 예의를 지키세요. 인물이 강하게 항의하더라도, 아랫사람이 윗사람을 가르치려 들거나 무례하게 비꼬는 대사(예: 제자가 스승에게 "뭘 배우신 거예요?")는 쓰지 마세요. 위계가 단어 선택과 태도에 자연스럽게 묻어나야 합니다.
8) 상대와의 티키타카(주고받기)는 써도 좋고 오히려 권장합니다. 단: ① 상대의 대사를 따로 적지 말고, 인물이 그 말을 받아 반응하는 방식으로만 상대의 말·행동이 자연스럽게 드러나게 하세요. ② 혼자 연기해도 상황과 상대의 반응이 충분히 이해되어야 합니다. 상대 의존이 과해서 한쪽 말만 들으면 무슨 상황인지 모를 정도면 안 됩니다. ③ situation에만 적어두지 말고, '상대가 누구인지·지금 무슨 상황인지·인물이 뭘 원하는지'가 대사 자체에서 관객에게 그려져야 합니다.
9) 자연스러운 구어체로 쓰세요 — 매우 중요: 실제 사람이 말하듯 문장이 흐르게 하세요. 한 호흡에 두세 문장씩 자연스럽게 이어 붙이고, 한두 단어짜리 토막 문장을 연달아 늘어놓지 마세요. 과도한 말줄임표(…)나 잦은 마침표로 잘게 끊으면 사람이 아니라 AI가 쓴 것처럼 어색해집니다. 머뭇거림·끊김은 정말 필요한 한두 군데에만. 문장 사이에 이중 공백을 넣지 마세요.
10) 제목(title)은 장면의 핵심 감정이나 상황이 직관적으로 와닿는 한국어로 지으세요. 비즈니스·전문 용어나 모호한 추상어(예: "정식발주", "돌아온 제안")는 쓰지 마세요.
11) 행동·동작·표정 등 '지문'은 반드시 괄호 ()로 묶어 입으로 말하는 대사와 구분하세요. 예: (얼음을 손바닥에 덜어낸다) 차가운 게 올라오네. 괄호 밖은 전부 소리 내어 말하는 대사여야 합니다.
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
- 판정 기준 5가지로 직접 읽고 합격/불합격 결정.
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
