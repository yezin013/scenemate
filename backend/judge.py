"""대사 품질 판정(judge) + 자가교정 루프(refine_track).

prompt_test/validation_agent.py에서 추출. notebook.ipynb 의존 제거하고
입력을 (외모 키워드, 자기소개) 두 문자열로 받도록 바꿈.

흐름:  진단(rule_clean + 길이 + LLM judge) → 교정(fixer.fix) 최대 N회.
       단, 교정본이 '나아질 때만' 채택(악화 방지).
Phase 2에서 generator.generate_dialogues()에 연결 예정. (현재 main.py에는 미연결)
"""
from llm import gen_json
from fixer import fix, rule_clean, LEN_MIN, LEN_MAX

MAX_PASSES = 2   # 교정 반복 상한 (이 횟수 넘으면 최선본을 그대로 반환)

JUDGE_SYS = (
    "당신은 한국 연극영화과 오디션 독백 대사의 품질을 검수하는 깐깐한 드라마투르그입니다. "
    "주어진 기준으로 대사를 평가하고 위반을 정확히 짚으세요. 애매하면 NG 쪽으로, 관대하게 넘기지 마세요."
)


def judge(appearance_keywords, self_intro, track_kind, track):
    """한 트랙을 4개 기준으로 OK/NG 판정. track_kind: 'A'(외모) | 'B'(성격)."""
    kind_label = "외모(첫인상)" if track_kind == "A" else "성격(내면)"
    fit_rule = (
        "이 대사가 [외모 키워드]의 구체적 분위기에서 출발한 캐릭터인가. 외모와 무관하면 NG."
        if track_kind == "A" else
        "이 대사가 [자기소개=성격/내면]에 충실한 캐릭터인가. 성격과 무관하면 NG."
    )
    prompt = f"""[배우 분석]
외모 키워드: {appearance_keywords}
자기소개(성격): {self_intro}

[검수 대상 — {kind_label} 기반 트랙]
제목: {track.get('title','')}
상황: {track.get('situation','')}
대사: {track.get('script','')}

다음 4가지를 각각 OK/NG로 판정하고 근거를 한 줄로 쓰세요.
1) 호칭일관성: 화자가 부르는 말 상대/호칭이 대사 중간에 뒤죽박죽 바뀌지 않는가.
2) 회상클리셰: 시계·사진·앨범·편지·인형 등 오래된 물건을 보며 과거나 떠난 사람을 추억하는 감상적 회상 독백이면 NG. 지금 벌어지는 사건(행동·결정·대립·설득·고백)이면 OK.
3) 트랙적합성: {fit_rule}
4) 말투자연스러움: 실제 사람이 입으로 말하듯 들리는가 — '말투·문장 자체의 자연스러움'만 본다. 다음 중 하나라도 있으면 NG: ① 로봇 같은 반복('나는 ~한다' 나열), 토막토막 끊김, 문어체/낭독체/번역투 ② AI 감성 클리셰 — "이대로만 ~주세요", "부디 ~해 주시길", "그게 바로 ~입니다", "당신이(그대가) ~합니다", "내 마음속 깊은 곳에서", "온 힘을 다해", "존재 전체로" 같은 과잉 문학체·기원체 표현. ※ 감정이 강하거나 페르소나 톤(차분/차가움 등)과 안 맞는 것은 여기서 NG 사유가 아니다(트랙적합성에서 본다). 자연스러운 한국어 구어라면 감정적이어도 OK.

반드시 아래 JSON으로만 답하세요:
{{"호칭일관성":{{"status":"OK","근거":""}},"회상클리셰":{{"status":"OK","근거":""}},"트랙적합성":{{"status":"OK","근거":""}},"말투자연스러움":{{"status":"OK","근거":""}}}}"""
    return gen_json(prompt, system=JUDGE_SYS, temperature=0.2)


def ng_list(verdict):
    """판정 dict에서 NG 항목만 '항목: 근거' 문자열 리스트로."""
    return [f"{k}: {v.get('근거','')}".strip() for k, v in verdict.items() if v.get("status") == "NG"]


def diagnose(appearance_keywords, self_intro, track_kind, track):
    """통합 진단 → (이슈리스트, 정리된 track). rule_clean(무료) + 길이 + LLM judge."""
    t = dict(track)
    rule_issues, t["script"] = rule_clean(t.get("script", ""))
    length = len(t["script"])
    len_issue = [] if LEN_MIN <= length <= LEN_MAX else [f"길이 {length}자 (목표 {LEN_MIN}~{LEN_MAX})"]
    verdict = judge(appearance_keywords, self_intro, track_kind, t)
    return rule_issues + len_issue + ng_list(verdict), t


def refine_track(appearance_keywords, self_intro, track_kind, track, max_passes=MAX_PASSES):
    """진단 → 교정 시도. 교정본이 원본보다 '나아질 때만' 채택(악화 방지).

    반환: {final, ok, best_issues, passes(라운드별 이슈), reverted}
    """
    issues, cur = diagnose(appearance_keywords, self_intro, track_kind, track)   # 원본 진단
    log = {"passes": [{"pass": 0, "issues": issues}], "reverted": False}
    best, best_issues = cur, issues
    for p in range(1, max_passes + 1):
        if not best_issues:                                                      # 이미 깨끗 → 끝
            break
        cand = fix(appearance_keywords, self_intro, track_kind, best, best_issues)
        cand_issues, cand = diagnose(appearance_keywords, self_intro, track_kind, cand)
        log["passes"].append({"pass": p, "issues": cand_issues})
        if len(cand_issues) < len(best_issues):                                  # 나아짐 → 채택
            best, best_issues = cand, cand_issues
        else:                                                                    # 안 나아짐 → 폐기
            log["reverted"] = True
            break
    log["final"] = best
    log["best_issues"] = best_issues
    log["ok"] = (len(best_issues) == 0)
    return log
