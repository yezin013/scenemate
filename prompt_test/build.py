"""notebook.ipynb 생성용 빌더. 한 번 실행 후 지워도 됨.

설계 v2: 트랙 = 내용 축(외모 / 성격), 목소리 = 두 트랙 공통 '전달 스타일' 제약.
"""
import nbformat as nbf

nb = nbf.v4.new_notebook()
cells = []
md = lambda s: cells.append(nbf.v4.new_markdown_cell(s))
code = lambda s: cells.append(nbf.v4.new_code_cell(s))

md("""# SceneMate · STEP 0 — 대사 창작 프롬프트 검증 (v2)

**목표:** 인프라를 짜기 전에, 대사 창작 프롬프트가 쓸 만한 오디션 독백을 뽑는지 먼저 검증.

**설계 v2 — 트랙 정의 변경**
- 🅰 **외모 기반**: 외모 첫인상에 충실한 *내용* + 목소리가 *스타일*로 반영
- 🅱 **성격 기반**: 실제 내면·성격에 충실한 *내용* + 목소리가 *스타일*로 반영
- **목소리·말투 = 내용 축이 아니라 전달 스타일 축.** 두 트랙 모두에 어조·리듬·호흡·단어 선택으로 입힌다. (허스키한 목소리에 과한 애교체 X)

**안전:** mock 텍스트만 사용 → 생체정보 미전송 → Gemini 무료 티어로 안전.

**판정 기준**
1. 두 트랙(외모 / 성격)이 실제로 다른 방향인가
2. 길이가 오디션 독백에 맞는가 (말로 1~2분)
3. 외모↔말투 상충(P1), 성격↔목소리 상충(P6)을 제대로 다루는가
4. 목소리가 두 트랙의 스타일에 실제로 반영됐는가
5. 같은 입력 3번 → 일관성이 있는가""")

md("""## 1. 환경 셋업 & 연결 테스트

`.env` 파일에 `GOOGLE_API_KEY=...` 를 채워야 한다. (`.gitignore`로 깃 제외됨)""")

code("""import os, json, time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()  # .env 에서 GOOGLE_API_KEY 로드
API_KEY = os.environ.get("GOOGLE_API_KEY", "")
assert API_KEY and "여기에" not in API_KEY, ".env 파일에 본인 Gemini API 키를 넣어주세요!"

client = genai.Client(api_key=API_KEY)
# 반복 검증용 기본 모델. gemini-2.5-flash / 2.0-flash 무료 티어는 하루 요청 한도가
# 매우 빡빡(20)해서 금방 막힌다. 무료 한도가 가장 넉넉한 flash-lite로 프롬프트를 다듬고,
# 최종 품질 비교가 필요할 때만 gemini-2.5-flash로 바꿔 소량 확인한다.
MODEL = "gemini-2.5-flash-lite"

# 연결 테스트
resp = client.models.generate_content(model=MODEL, contents="한국어로 '연결 성공'이라고만 답해줘.")
print("Gemini 응답:", resp.text.strip())""")

md("""## 2. mock 입력 — 페르소나 6개

각 페르소나 = **외모 키워드** + **자기소개(성격)** + **목소리·말투**.
- P1: *외모↔말투* 상충 (차가운 외모 + 애교 말투)
- P6: *성격↔목소리* 상충 (애교 성격 + 허스키 목소리) ← v2에서 추가""")

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

md("""## 3. 프롬프트 설계 v2 (내용=외모/성격, 목소리=공통 스타일)

- 트랙 A = 외모 기반 내용 / 트랙 B = 성격 기반 내용
- **목소리는 두 트랙 공통**으로 어조·리듬·호흡·단어 선택에 반영
- 성격↔목소리 상충 시: *내용은 성격, 전달 톤은 목소리*에 맞춰 조정
- 각 트랙에 `voice_style` 필드를 둬서 "목소리를 어떻게 반영했는지" 스스로 밝히게 함 (판정 기준 4 확인용)""")

code('''SYSTEM_INSTRUCTION = (
    "당신은 한국 연극영화과 오디션을 위한 '독백 대사'를 창작하는 전문 극작가입니다. "
    "배우의 외모·성격·목소리 분석 결과를 바탕으로 오디션용 독백을 새로 창작합니다. "
    "외모와 성격은 대사의 '내용/캐릭터'를 결정하고, 목소리·말투는 대사의 '전달 스타일'(어조·리듬·호흡·단어 선택)을 결정합니다. "
    "기존 희곡이나 영화 대사를 인용하지 말고 100% 새로 창작하세요."
)

OUTPUT_SCHEMA_DESC = """
반드시 아래 JSON 형식으로만 답하세요 (다른 설명 금지):
{
  "track_A_appearance": {
    "title": "대사 제목",
    "setup": "이 대사의 상황 설정 한 줄",
    "script": "독백 대사 본문 (한국어, 말로 1~2분 분량, 대략 350~550자)",
    "fit_reason": "이 대사가 '외모/첫인상'과 왜 어울리는지 1~2줄",
    "voice_style": "이 대사의 어조·리듬에 배우의 목소리를 어떻게 반영했는지 1줄"
  },
  "track_B_personality": {
    "title": "대사 제목",
    "setup": "이 대사의 상황 설정 한 줄",
    "script": "독백 대사 본문 (한국어, 말로 1~2분 분량, 대략 350~550자)",
    "fit_reason": "이 대사가 '성격/내면'과 왜 어울리는지 1~2줄",
    "voice_style": "이 대사의 어조·리듬에 배우의 목소리를 어떻게 반영했는지 1줄"
  }
}
"""

def build_prompt(persona: dict) -> str:
    return f"""다음은 한 배우의 분석 결과입니다.

[외모 키워드 — 사진의 객관적 시각 특징]
{persona['appearance_keywords']}

[자기소개 — 성격/내면]
{persona['self_intro']}

[목소리·말투 분석]
{persona['voice_tone']}

이 배우를 위해 오디션용 독백 대사를 두 가지 방향으로 창작하세요.

- track_A_appearance (외모 기반): 사진의 '첫인상·외모 분위기'에 충실한 캐릭터의 대사.
- track_B_personality (성격 기반): 실제 내면·성격에 충실한 캐릭터의 대사.

[외모 트랙(track_A) 다양성 규칙]
- 외모 키워드의 '구체적인' 분위기에서 출발해 캐릭터와 상황을 정하세요.
- 금지: 오래된 물건(시계·사진·앨범·인형·편지 등)을 보며 과거나 떠난 사람을 추억하는 감상적 회상 독백.
- 회상·추억에 기대지 말고, 지금 벌어지는 사건 속에서 인물이 '행동·결정·대립·설득·고백'하는 현재형 상황을 택하세요.
- 외모 분위기에 맞는 장르를 적극 활용하세요. (예: 서늘함→스릴러/심문, 강렬함→대결/협상, 발랄함→코미디/소동, 청순+당참→반전 드라마, 따뜻함→일상의 갈등) 매번 다른 장르·상황이 나오게 하세요.

[목소리 규칙 — 두 트랙 공통]
'목소리·말투'는 대사의 내용이 아니라 '전달 스타일'을 결정합니다.
두 대사 모두 이 목소리로 자연스럽게 말할 수 있도록 어조·문장 리듬·호흡·단어 선택을 맞추세요.
목소리에 어울리지 않는 표현(예: 허스키한 목소리에 과한 애교체)은 피하세요.
성격과 목소리가 상충하면, 내용은 성격을 살리되 전달 톤은 목소리에 맞게 조정하세요.

두 트랙은 캐릭터·감정 방향이 뚜렷하게 달라야 합니다.
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

md("""## 4. 빠른 테스트 — 상충 케이스 P1, P6

먼저 두 상충 케이스를 돌려 출력 형태와 품질을 눈으로 확인한다.""")

code('''def show_result(persona_name: str, result: dict):
    print("=" * 70)
    print("페르소나:", persona_name)
    for key, label in [("track_A_appearance", "\U0001F170 외모 기반"),
                       ("track_B_personality", "\U0001F171 성격 기반")]:
        t = result[key]
        body = t["script"]
        print("\\n" + "-" * 70)
        print(f"{label}  |  {t['title']}  ({len(body)}자)")
        print("상황:", t["setup"])
        print("목소리 반영:", t.get("voice_style", "-"))
        print()
        print(body)
        print("\\n어울리는 이유:", t["fit_reason"])
    print("=" * 70)

for idx in (0, 5):  # P1, P6
    show_result(PERSONAS[idx]["name"], generate_dialogues(PERSONAS[idx]))
    time.sleep(2)''')

md("""## 5. 전체 페르소나 6개 생성

무료 티어 분당 한도 보호용으로 호출 사이 2초 간격.""")

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

md("""## 6. 자동 체크 + 일관성 테스트

수치는 1차 거름망일 뿐, 최종 판단은 직접 읽고 한다.
- **길이**: 대략 300~600자(말로 1~2분)
- **문자 겹침도**: 두 트랙이 얼마나 다른가 (낮을수록 다른 방향 → 좋음)
- **일관성**: 같은 입력(P1) 3번 → 제목/길이가 들쭉날쭉하지 않은가""")

code('''def char_overlap(a: str, b: str) -> float:
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0

print(f"{'페르소나':<40} A길이  B길이  문자겹침도")
for p, r in results:
    a = r["track_A_appearance"]["script"]
    b = r["track_B_personality"]["script"]
    print(f"{p['name'][:38]:<40} {len(a):>4}  {len(b):>4}   {char_overlap(a, b):.2f}")

print("\\n[일관성 테스트] P1을 3번 생성 → 트랙 A 제목/길이 비교")
for i in range(3):
    r = generate_dialogues(PERSONAS[0])
    a = r["track_A_appearance"]
    print(f"  {i+1}회차: '{a['title']}' ({len(a['script'])}자)")
    time.sleep(2)''')

md("""## 7. 다음 단계

- 판정 기준 5가지로 직접 읽고 합격/불합격 결정.
- 불합격이면 → `SYSTEM_INSTRUCTION` / `build_prompt` 수정하며 이 노트북만 반복.
- 합격이면 → MVP Phase 1(FastAPI + PostgreSQL + Redis)로 진행.

> 막판 품질 비교는 같은 페르소나를 GPT-4o로도 돌려(기획서 '배포 전 최종 검증') 확인.""")

nb["cells"] = cells
nb["metadata"] = {
    "kernelspec": {"display_name": "Python 3 (scenemate)", "language": "python", "name": "python3"},
    "language_info": {"name": "python", "version": "3.12"},
}

with open("notebook.ipynb", "w", encoding="utf-8") as f:
    nbf.write(nb, f)
print("notebook.ipynb 생성 완료, 셀", len(cells), "개")
