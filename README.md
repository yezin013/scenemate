# SceneMate (씬메이트)

**AI 오디션 독백 대사 매칭 서비스.** 사진과 자기소개 텍스트 두 가지만으로 사용자의 외모·성격을 분석·구조화하고, 가장 잘 어울리는 오디션 독백을 **두 가지 방향(외모 기반 / 성격 기반)** 으로 창작해 추천한다.

연극영화과 전공자가 직접 겪은 문제에서 출발한 프로젝트다. 기존엔 오디션 준비생이 수십 편의 희곡·시나리오를 직접 읽으며 자신에게 맞는 독백을 찾아야 했고, 외모·말투와 실제로 잘 어울리는지 객관적으로 판단하기 어려웠다. 외모·성격을 대사와 연결하는 로직을 AI 파이프라인으로 구현한다.

> **대사 DB는 없다.** 저작권 문제를 피하고 완전한 개인화를 위해, 요청이 들어올 때마다 AI가 그 사람에게 맞는 대사를 새로 창작한다. 창작된 결과물만 아카이브에 저장된다.

## 핵심 원칙

- **인프라 한 줄 짜기 전에, 대사 창작 프롬프트가 "쓸 만한가"부터 검증한다.** 여기서 통과 못 하면 나머지를 다 만들어도 의미가 없다.
- MVP(대사 추천 + 아카이브)를 완성한 뒤 v2, v3 순서로 확장한다.

## 두 트랙 대사 추천

같은 사람이라도 외모의 첫인상과 실제 내면·성격은 다를 수 있다. 두 가지를 분리해 각각에 맞는 독백을 창작한다.

| 트랙 | 분석 기반 | 대사 방향 | 활용 상황 |
|---|---|---|---|
| **A — 외모 기반** | Vision AI 외모 키워드 | 첫인상에 충실한 대사 | 외모를 살리고 싶을 때 |
| **B — 성격 기반** | 자기소개 텍스트 구조화 | 내면·성격에 충실한 대사 | 반전 매력을 보여줄 때 |

> 예: 외모는 차갑고 도시적이지만 말투는 사랑스럽고 애교 있는 경우 → 트랙 A는 차갑고 강렬한 도시적 독백, 트랙 B는 따뜻하고 사랑스러운 독백을 각각 창작.

## 현재 진행 상황

- ✅ **STEP 0 — 프롬프트 검증** (`prompt_test/`)
  대사 창작 프롬프트를 노트북으로 검증. 단순 생성을 넘어 **자가교정·심판(judge) 파이프라인**까지 구축(judge 채점 → 결함 교정 → 재생성). mock 텍스트 입력이라 Gemini 무료 티어로 안전.
- ✅ **MVP 백엔드** (`backend/`) — FastAPI 동작. 대사 생성(`/generate`, `/generate-from-photo`), 아카이브(`/scripts`), Supabase Auth(JWT 인증, user_id 분리) 완료. Railway 배포 완료(`scenemate-production.up.railway.app`).
- ✅ **MVP 프론트엔드** (`frontend/`) — React + Vite. 사진/자기소개 입력 → 백엔드 호출 → 두 트랙 결과 표시, 아카이브, 오디션 피드백 기록까지 연결됨. Vercel 배포 완료(`scenemate-alpha.vercel.app`).
- 🟡 **v3 — 대사 분석 공부** — 구현 중. 아래 설계 참조.

## 폴더 구조

```
scenemate/
├─ prompt_test/             # STEP 0 프롬프트 검증
│  ├─ notebook.ipynb            # 메인 검증 노트북
│  ├─ build.py                  # 노트북 빌더(재생성용)
│  ├─ run.py                    # 전체 페르소나 일괄 실행 + 결과 저장
│  ├─ judge_check.py            # 생성 대사 채점(judge)
│  ├─ validation_agent.py       # 자가교정 에이전트(채점→교정→재생성)
│  ├─ fixer_check.py            # 클리셰 등 케이스 교정 테스트
│  ├─ vision_test.py            # 사진→키워드 추출(Vision) 검증
│  ├─ result.md / *_report.md   # 생성·검증 결과 리포트
│  └─ .env.example              # 환경변수 예시 (.env 는 깃 제외)
├─ backend/                 # FastAPI 백엔드
│  ├─ main.py                   # API 진입점(생성·아카이브·분석·헬스체크)
│  ├─ generator.py              # 대사 2트랙 생성(11개 작법 규칙 프롬프트)
│  ├─ vision.py                 # 사진 → 외모 키워드 추출(2단계 정책 우회)
│  ├─ auth.py                   # JWT 검증 (Supabase Auth)
│  ├─ db.py / models.py / schemas.py / init_db.py
│  └─ .env.example              # DATABASE_URL, GOOGLE_API_KEY, SUPABASE_JWT_SECRET 예시
└─ frontend/                # React + Vite 프론트엔드
   ├─ src/App.jsx               # 입력 폼 + 결과 화면 + 아카이브 + 분석 화면
   ├─ src/supabase.js           # Supabase 클라이언트
   └─ .env.example              # VITE_API_URL, VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY 예시
```

## 셋업 & 실행

```bash
git clone https://github.com/yezin013/scenemate.git
cd scenemate
```

### STEP 0 — 프롬프트 검증

```bash
# 가상환경 (conda 예시)
conda create -n scenemate python=3.12 -y
conda activate scenemate
pip install -r requirements.txt

# API 키 설정: prompt_test/.env.example → .env 로 복사 후 GOOGLE_API_KEY 입력
cd prompt_test
python run.py          # 또는: jupyter lab notebook.ipynb
```

### 백엔드 (FastAPI)

```bash
cd backend
pip install -r requirements.txt

# .env.example → .env 로 복사 후 값 입력
#   GOOGLE_API_KEY=...                          (Gemini)
#   DATABASE_URL=postgresql://...               (Supabase Session pooler 연결 문자열)
#   SUPABASE_JWT_SECRET=...                     (Supabase JWT Secret)

uvicorn main:app --reload      # 기본 http://localhost:8000
```

주요 엔드포인트: `GET /health`, `GET /health/db`, `POST /generate`(텍스트), `POST /generate-from-photo`(사진), `GET·POST /scripts`(아카이브), `POST /analyze`(힌트), `POST /analyze/full`(전체 분석).

### 프론트엔드 (React + Vite)

```bash
cd frontend
npm install

# (선택) 백엔드를 8000 외 포트로 띄운다면: .env.example → .env 복사 후 VITE_API_URL 수정
npm run dev          # 기본 http://localhost:5173
```

## 입력 분석 구조

| 입력 | 방식 | 분석 방법 | 분석 결과 |
|---|---|---|---|
| 사진 | 파일 업로드 | Vision AI(Gemini) **2단계 구조** | 외모·인상 키워드 추출 |
| 자기소개 | 자유 텍스트 | LLM 구조화 | 성격·말투 분석 |

**Vision AI 2단계 정책 우회** — Vision에 "이 사람은 차갑다"처럼 인물을 평가하도록 직접 요청하면 정책상 거부될 수 있다. 이를 우회하기 위해:
1. 사진 → "시각적 특징 키워드만 객관적으로 묘사"(헤어·표정·전체 인상) 추출
2. 키워드 텍스트 → 대사 톤 결정 → 대사 창작

> fallback: 거부 시 사용자가 외모 키워드를 직접 입력하는 방식으로 전환.

## 대사 창작 품질 기준

대사 품질이 서비스 성패를 좌우한다. 단순 생성에 그치지 않고 **자가교정·심판(judge) 파이프라인**으로 품질을 보장한다. 생성된 대사를 별도 LLM 심판이 채점해, 트랙 부적합·말투 비일관·클리셰 등 결함이 발견되면 자동 재생성한다. 회상 클리셰 등 특정 패턴은 fixer 모듈이 별도 교정한다.

판정 기준: ① 트랙 분리(두 트랙이 실제로 다른 방향인가) ② 적정 길이(1~2분 분량) ③ 상충 입력 처리(차가운 외모 + 애교 말투를 두 트랙으로 분리) ④ 일관성(같은 입력 반복 시 일관된 결과). 세부 작법은 `generator.py`의 11개 작법 규칙(호칭·존댓말 일관성, 클리셰 금지, 구어체, 지문 괄호, 과잉 감정 지양 등)으로 강제한다.

## v3 — 대사 분석 공부 설계

아카이브에 저장된 기존 대사를 선택해 7개 레이어로 직접 분석하고, 막힐 때 AI 힌트를 요청하며, 완료 후 AI 분석과 나란히 비교하는 기능. **AI가 정답을 주는 게 아니라, 사용자가 먼저 생각하는 과정을 설계**한다.

### 전체 흐름

```
아카이브에서 대사 선택
    ↓
분석 화면 진입 — 7개 레이어 입력 폼
    ↓
막힐 때 → 레이어별 힌트 요청 (AI가 방향만 제시, 정답 아님)
    ↓
분석 완료 → AI 전체 분석 생성
    ↓
내 분석 / AI 분석 나란히 비교
    ↓
결과 저장 (analysis 테이블)
```

### 7개 분석 레이어

| # | 레이어 | 설명 |
|---|---|---|
| 1 | **서브텍스트** | 표면적 말 vs 실제 의도 |
| 2 | **행동 동사** | 화자가 하려는 행동 (설득/회유/공격/숨김 등) |
| 3 | **감정선 흐름** | 시작 → 중간 → 끝 감정 온도 변화 |
| 4 | **상황·전사** | 현재 상황 + 이 대사 이전 맥락 |
| 5 | **인물 배경** | 어떤 환경, 어떤 가치관 |
| 6 | **관계 분석** | 상대방과의 관계, 권력 구도 |
| 7 | **진짜 목표** | 단순 감정 표출 / 뭔가를 얻으려는가 / 감추려는가 |

### 백엔드 추가

- `POST /analyze` — 레이어별 힌트 생성 (대사 + 레이어 종류 입력)
- `POST /analyze/full` — 7개 레이어 전체 AI 분석 생성
- `analysis` 테이블 — script_id 참조, 사용자 분석 7개 레이어 + AI 분석 저장

### 프론트엔드 추가

- 아카이브 대사 상세에 **"분석하기"** 버튼
- 분석 화면 — 7개 레이어 입력 폼 + 레이어별 힌트 버튼
- 비교 화면 — 내 분석 / AI 분석 나란히 표시

## 기술 스택

- **현재 사용**: Gemini(`gemini-2.5-flash-lite`, Vision + 대사 생성) · FastAPI · SQLAlchemy · PostgreSQL(Supabase) · Supabase Auth · React 19 · Vite
- **배포**: Railway(백엔드) · Vercel(프론트엔드)
- **계획**: pgvector(대사 벡터화 → 유사도 추천) · Redis(API 비용 캐싱 + WebSocket pub/sub) · WebSocket(시뮬레이터 실시간 스트리밍) · Recharts(성장 그래프) · Tailwind CSS

> 모델은 개발/검증 단계에서 무료 한도가 넉넉한 `gemini-2.5-flash-lite` 사용. 최종 품질은 `gemini-2.5-flash`로 전환 예정. 배포 전 GPT-4o Vision으로 품질 비교 검증.

## 개발 로드맵

| 단계 | 내용 | 상태 |
|---|---|---|
| **STEP 0** | 프롬프트 검증 — 대사 창작 품질 확인 | ✅ 완료 |
| **MVP** | ① AI 맞춤 대사 추천 + ② 나만의 아카이브(저장·피드백 기록) + Supabase Auth + 배포 | ✅ 완료 |
| **v3** | 대사 분석 공부 — 아카이브 대사 선택 → 7개 레이어 직접 분석 → 힌트 → AI 분석 비교 | 🟡 구현 중 |
| **v2** | 오디션 시뮬레이터 — 유형별 AI 면접관 페르소나 + 난이도 조절 + WebSocket | 예정 |

> 시간 박스 원칙(1인 개발 + 학업 병행): MVP(대사 추천 + 아카이브)만으로도 완결된 서비스이며, v2·v3는 확장이다.

## 주의

- **`.env`(API 키·DB 비밀번호)는 절대 커밋하지 않는다.** (`.gitignore`로 제외됨)
- **민감정보(얼굴)**: 한국 PIPA상 얼굴은 생체정보. 입력 파일은 분석 후 즉시 폐기하고 창작 결과물만 DB에 저장한다. 배포 시 동의·처리방침·파기 정책 필요.
- 실제 사용자 사진을 다루는 MVP 단계부터는 Gemini 무료 티어 대신 유료 티어(데이터 미사용 보장)로 전환한다. (무료 티어는 입력 데이터가 모델 개선에 사용될 수 있음)
