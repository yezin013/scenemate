# SceneMate (씬메이트)

AI 오디션 독백 대사 매칭 서비스. 사진·자기소개·목소리 세 가지로 사용자의 외모·성격·목소리를 분석해, 가장 잘 어울리는 오디션 독백을 **두 가지 방향(외모 기반 / 성격 기반)**으로 창작·추천한다.

> 핵심 원칙: **인프라를 짜기 전에 대사 창작 프롬프트가 "쓸 만한가"부터 검증한다.**

## 현재 진행 상황

- ✅ **STEP 0 — 프롬프트 검증** (`step0_prompt_validation/`)
  대사 창작 프롬프트를 Jupyter 노트북으로 검증 중. mock 텍스트 입력이라 Gemini 무료 티어로 안전.
- ⬜ MVP (① 대사 추천 + ② 아카이브) — `backend/`, `frontend/` (예정)

## 폴더 구조

```
scenemate/
├─ step0_prompt_validation/   # STEP 0 프롬프트 검증
│  ├─ dialogue_prompt_test.ipynb   # 메인 검증 노트북
│  ├─ _build_notebook.py           # 노트북 빌더(재생성용)
│  ├─ _run_step0.py                # 전체 페르소나 일괄 실행 + 리포트 저장
│  ├─ step0_report.md              # 생성 결과 리포트
│  └─ .env.example                 # 환경변수 예시 (.env 는 깃 제외)
├─ backend/    # (예정) FastAPI + PostgreSQL/pgvector + Redis
└─ frontend/   # (예정) React + Tailwind
```

## 다른 컴퓨터에서 클론 후 셋업

```bash
git clone https://github.com/yezin013/scenemate.git
cd scenemate

# 1) 가상환경 (conda 예시)
conda create -n scenemate python=3.12 -y
conda activate scenemate

# 2) 패키지 설치
pip install -r requirements.txt

# 3) API 키 설정 (.env 는 깃에 없으므로 직접 생성)
#    step0_prompt_validation/.env.example 를 .env 로 복사 후 본인 키 입력
#    GOOGLE_API_KEY=...

# 4) STEP 0 실행
cd step0_prompt_validation
jupyter lab dialogue_prompt_test.ipynb
```

## 기술 스택

Vision AI(Gemini) · STT(Whisper) · FastAPI · PostgreSQL + pgvector · Redis · React · WebSocket

## 주의

- **`.env`(API 키)는 절대 커밋하지 않는다.** (`.gitignore`로 제외됨)
- 실제 사용자 얼굴·음성을 다루는 MVP 단계부터는 Gemini 무료 티어 대신 유료 티어(데이터 미사용 보장)로 전환한다.
