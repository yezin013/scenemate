"""SceneMate STEP 0 — 대사 자가교정 에이전트 (validation + auto-fix)

흐름:  생성(Gemini) → 검사(regex 룰 + Gemini 판단) → 교정(Gemini, 최대 N회) → 리포트
설계 원칙:
  - '프롬프트'는 건드리지 않는다. 생성된 '대사 출력'만 검사·교정한다. (네가 프롬프트 통제권 유지)
  - 기계적 결함(공백/문법)은 regex로 무료·결정적 처리, 판단이 필요한 것만 LLM.
  - 원본 결함 + 교정본을 함께 기록 → 눈은 편하게, 동시에 "프롬프트 어디 고칠지" 신호도 얻는다.
  - 무한루프 방지를 위해 교정은 MAX_PASSES 회로 상한.

실행:  prompt_test 폴더에서  python validation_agent.py        (전체 페르소나)
       빠른 테스트는        python validation_agent.py 1     (앞 1개만 → 한도 절약)
"""
import os, re, json, time, sys, nbformat
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

# 검사/교정 모델은 상수로 분리 → 원하면 더 센 모델(gemini-2.5-flash)이나 다른 LLM으로 교체 가능.
# (교차검증을 원하면 JUDGE를 Gemini가 아닌 다른 모델로 두는 게 이상적이지만, 지금은 무료·셋업 기준 Gemini.)
GEN_MODEL   = "gemini-2.5-flash-lite"   # 대사 생성
JUDGE_MODEL = "gemini-2.5-flash-lite"   # 검사·교정 (품질 더 원하면 "gemini-2.5-flash")
MAX_PASSES  = 2                          # 교정 반복 상한 (이 횟수 넘으면 사람에게 넘김)
LEN_MIN, LEN_MAX = 300, 600             # 오디션 독백 적정 길이(자)

# ---------- 0) 노트북에서 페르소나/프롬프트 정의 재사용 (중복 정의 방지) ----------
nb = nbformat.read("notebook.ipynb", as_version=4)
_ns = {"client": client, "types": types, "json": json, "MODEL": GEN_MODEL}
for idx in (4, 6):                       # cell 4 = PERSONAS, cell 6 = build_prompt/SYSTEM_INSTRUCTION
    exec(nb.cells[idx].source, _ns)
PERSONAS = _ns["PERSONAS"]
build_prompt = _ns["build_prompt"]
SYSTEM_INSTRUCTION = _ns["SYSTEM_INSTRUCTION"]

if len(sys.argv) > 1:                     # 인자로 개수 주면 앞에서 그만큼만 (한도 절약용 빠른 테스트)
    PERSONAS = PERSONAS[: int(sys.argv[1])]


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


def _gen_json(model, contents, system=None, temperature=0.9, tries=5):
    """JSON 응답 생성 공통 래퍼 — 429(무료 한도)는 안내된 시간만큼 대기 후 재시도."""
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
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                m = re.search(r"retry in ([0-9.]+)", msg)
                wait = (float(m.group(1)) + 2) if m else 20
                print(f"    429 한도 → {wait:.0f}s 대기 후 재시도")
                time.sleep(wait)
                continue
            raise
    raise RuntimeError("재시도 초과 — 오늘 한도 소진 가능")


# ---------- 1) 생성 ----------
def generate(persona):
    return _gen_json(GEN_MODEL, build_prompt(persona), system=SYSTEM_INSTRUCTION)


# ---------- 2-a) 규칙 검사(무료·결정적) + 자동 정리 ----------
def rule_clean(text):
    """기계적 공백/문법 결함을 결정적으로 교정. (위반목록, 정리된 텍스트) 반환."""
    text = text or ""
    issues = []
    if "  " in text:                    issues.append("이중 공백")
    if re.search(r"\s[.,!?…]", text):   issues.append("문장부호 앞 공백")
    if text != text.strip():            issues.append("앞뒤 공백")
    if "\n\n" in text:                  issues.append("빈 줄")
    cleaned = re.sub(r"[ \t]+", " ", text)             # 다중 공백 → 1칸
    cleaned = re.sub(r"\s+([.,!?…])", r"\1", cleaned)  # 부호 앞 공백 제거
    cleaned = re.sub(r"\n{2,}", "\n", cleaned).strip()
    return issues, cleaned


# ---------- 2-b) LLM 판단 검사 ----------
JUDGE_SYS = (
    "당신은 한국 연극영화과 오디션 독백 대사의 품질을 검수하는 깐깐한 드라마투르그입니다. "
    "주어진 기준으로 대사를 평가하고 위반을 정확히 짚으세요. 애매하면 NG 쪽으로, 관대하게 넘기지 마세요."
)

def judge(persona, track_kind, track):
    """한 트랙을 4개 기준으로 OK/NG 판정. track_kind: 'A'(외모) | 'B'(성격)."""
    kind_label = "외모(첫인상)" if track_kind == "A" else "성격(내면)"
    fit_rule = (
        "이 대사가 [외모 키워드]의 구체적 분위기에서 출발한 캐릭터인가. 외모와 무관하면 NG."
        if track_kind == "A" else
        "이 대사가 [자기소개=성격/내면]에 충실한 캐릭터인가. 성격과 무관하면 NG."
    )
    prompt = f"""[배우 분석]
외모 키워드: {persona['appearance_keywords']}
자기소개(성격): {persona['self_intro']}
목소리·말투: {persona['voice_tone']}

[검수 대상 — {kind_label} 기반 트랙]
제목: {track.get('title','')}
상황: {track.get('situation','')}
대사: {track.get('script','')}

다음 4가지를 각각 OK/NG로 판정하고 근거를 한 줄로 쓰세요.
1) 호칭일관성: 화자가 부르는 말 상대/호칭이 대사 중간에 뒤죽박죽 바뀌지 않는가.
2) 회상클리셰: 시계·사진·앨범·편지·인형 등 오래된 물건을 보며 과거나 떠난 사람을 추억하는 감상적 회상 독백이면 NG. 지금 벌어지는 사건(행동·결정·대립·설득·고백)이면 OK.
3) 트랙적합성: {fit_rule}
4) 말투자연스러움: 실제 사람이 입으로 말하듯 들리는가 — '말투·문장 자체의 자연스러움'만 본다. 로봇 같은 반복('나는 ~한다' 나열)·토막토막 끊김·문어체/낭독체·번역투가 있으면 NG. ※ 감정이 강한 것, 또는 페르소나 톤(차분/차가움 등)과 안 맞는 것은 여기서 NG 사유가 '아니다'(그건 트랙적합성에서 본다). 자연스러운 한국어 구어라면 감정적이어도 OK.

반드시 아래 JSON으로만 답하세요:
{{"호칭일관성":{{"status":"OK","근거":""}},"회상클리셰":{{"status":"OK","근거":""}},"트랙적합성":{{"status":"OK","근거":""}},"말투자연스러움":{{"status":"OK","근거":""}}}}"""
    return _gen_json(JUDGE_MODEL, prompt, system=JUDGE_SYS, temperature=0.2)


def ng_list(verdict):
    """판정 dict에서 NG 항목만 '항목: 근거' 문자열 리스트로."""
    return [f"{k}: {v.get('근거','')}".strip() for k, v in verdict.items() if v.get("status") == "NG"]


# ---------- 3) 교정 ----------
def fix(persona, track_kind, track, issues):
    """지적된 문제를 고쳐 대사를 다시 씀. 구조적 문제(트랙적합성/회상)면 상황도 바꿈, 자연스러움 최우선."""
    kind_label = "외모(첫인상)" if track_kind == "A" else "성격(내면)"
    prompt = f"""아래 오디션 독백 대사에 지적된 문제들이 있습니다. 지적된 문제'만' 고쳐서 다시 쓰세요.

[배우] 외모: {persona['appearance_keywords']} / 성격: {persona['self_intro']} / 목소리: {persona['voice_tone']}
[이 트랙] {kind_label} 기반
[제목] {track.get('title','')}
[상황] {track.get('situation','')}
[현재 대사]
{track.get('script','')}

[고쳐야 할 문제]
- """ + "\n- ".join(issues) + f"""

규칙:
- 최우선: '실제 사람이 입으로 말하는 자연스러움'. 어떤 경우에도 문어체·낭독체·로봇 같은 말투로 만들지 말 것. (차분하거나 차가운 톤이어도 반드시 사람의 구어여야 한다.)
- '트랙적합성' 또는 '회상 클리셰'가 지적됐으면 → 단어만 비틀지 말고 상황·소재 자체를 바꿔라. 그 외모/성격에 자연스럽게 어울리는 '다른 상황'을 새로 골라라. (시계·사진·편지 등 회상 소재는 버린다.)
- 그 외 국소 문제(호칭 등)는 상황·캐릭터를 유지하고 해당 부분만 고친다.
- 행동·동작·표정 지문은 반드시 괄호 ()로 묶어 '말로 하는 대사'와 구분한다. 예: (얼음을 손바닥에 덜어낸다) 차가운 감촉이 올라온다.
- 길이는 {LEN_MIN}~{LEN_MAX}자를 지킨다. 줄이지 말 것 — {LEN_MIN}자 미만이면 상황·심리 묘사를 더 채워 늘린다.
반드시 JSON으로만: {{"title":"...","situation":"...","objective":"...","script":"...","voice_style":"..."}}"""
    return _gen_json(JUDGE_MODEL, prompt, system=SYSTEM_INSTRUCTION, temperature=0.7)


# ---------- 한 트랙 진단 (rule + 길이 + judge) ----------
def _diagnose(persona, track_kind, track):
    """통합 진단 → (이슈리스트, 정리된 track)."""
    t = dict(track)
    rule_issues, t["script"] = rule_clean(t.get("script", ""))
    length = len(t["script"])
    len_issue = [] if LEN_MIN <= length <= LEN_MAX else [f"길이 {length}자 (목표 {LEN_MIN}~{LEN_MAX})"]
    verdict = judge(persona, track_kind, t); time.sleep(2)
    return rule_issues + len_issue + ng_list(verdict), t


# ---------- 검사 + 교정 + 악화방지(회귀 가드) ----------
def validate_track(persona, track_kind, track):
    """원본 진단 → 교정 시도. 단, 교정본이 원본보다 '나아질 때만' 채택한다.
    나아지지 않으면(같거나 더 나쁨) 교정본을 버리고 직전 최선본을 유지 → 악화 방지."""
    issues, cur = _diagnose(persona, track_kind, track)             # 원본 진단
    log = {"passes": [{"pass": 0, "issues": issues}], "reverted": False}
    best, best_issues = cur, issues
    for p in range(1, MAX_PASSES + 1):
        if not best_issues:                                         # 이미 깨끗 → 끝
            break
        cand = fix(persona, track_kind, best, best_issues); time.sleep(2)
        cand_issues, cand = _diagnose(persona, track_kind, cand)    # 교정본 재진단
        log["passes"].append({"pass": p, "issues": cand_issues})
        if len(cand_issues) < len(best_issues):                     # 나아짐 → 채택
            best, best_issues = cand, cand_issues
        else:                                                       # 안 나아짐 → 교정본 폐기, 최선본 유지
            log["reverted"] = True
            break
    log["final"] = best
    log["best_issues"] = best_issues
    log["ok"] = (len(best_issues) == 0)
    return log


# ---------- 메인: 페르소나별 생성→검증→리포트 ----------
REPORT = "validation_report.md"

def main():
    out = [f"# 대사 자가교정 리포트 (gen={GEN_MODEL} · judge={JUDGE_MODEL} · max_passes={MAX_PASSES})\n"]

    def flush():
        with open(REPORT, "w", encoding="utf-8") as f:
            f.write("\n".join(out))

    for persona in PERSONAS:
        print("▶", persona["name"])
        out.append(f"## {persona['name']}\n")
        try:
            result = generate(persona); time.sleep(2)
        except Exception as e:
            out.append(f"⚠️ 생성 실패: {e}\n\n---\n"); flush(); continue

        for kind, key, label in [("A", "track_A_appearance", "🅰 외모 기반"),
                                 ("B", "track_B_personality", "🅱 성격 기반")]:
            log = validate_track(persona, kind, result.get(key, {}))
            status = "✅ 통과" if log["ok"] else f"❌ {MAX_PASSES}회 교정 후에도 잔여 문제"
            fin = log["final"]
            first_issues = log["passes"][0]["issues"]
            out.append(f"### {label} — {status}")
            out.append(f"- 원본 결함: {', '.join(first_issues) if first_issues else '없음 (원본부터 깨끗)'}")
            revert_note = "  (교정이 더 나빠져 폐기 → 직전 최선본 유지)" if log.get("reverted") else ""
            out.append(f"- 교정 횟수: {len(log['passes']) - 1}회{revert_note}")
            out.append(f"\n**최종 ({len(fin.get('script',''))}자) — {fin.get('title','')}**")
            out.append(f"*상황: {fin.get('situation','')}*")
            out.append(f"*목소리 반영: {fin.get('voice_style','-')}*\n")
            out.append(fin.get("script", ""))
            if not log["ok"]:
                out.append(f"\n> ⚠️ 잔여 문제(사람이 확인): {', '.join(log['best_issues'])}")
            out.append("")
            flush()           # 트랙마다 저장 (중간에 죽어도 손실 X)
        out.append("---\n")
        flush()

    print("DONE →", REPORT)


if __name__ == "__main__":
    main()
