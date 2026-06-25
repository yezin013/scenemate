# SceneMate — MVP 구현 기록

## 프로젝트 개요

**SceneMate**는 연기 전공생을 위한 AI 오디션 독백 대사 매칭 서비스다.
사진과 자기소개(성격·내면)를 입력하면 두 방향으로 독백 대사를 창작 추천한다.

- **Track A (외모 기반)**: 사진에서 추출한 시각 특징 → 외모에 어울리는 대사
- **Track B (성격 기반)**: 자기소개 텍스트 → 내면·성격에 어울리는 대사

대사는 AI가 창작하며, 저장·오디션 피드백 기록 기능을 갖춘 개인 아카이브로 연결된다.

---

## 기술 스택

| 레이어 | 기술 | 선택 이유 |
|--------|------|----------|
| 백엔드 | FastAPI + Uvicorn | 비동기 지원, 자동 문서화, 타입 검증 |
| DB | Supabase Postgres (무료) | 무료 한도, JSONB 지원, Auth 통합 |
| ORM | SQLAlchemy + psycopg2 | Session Pooler 직접 연결 (supabase-py 대신) |
| AI | Google Gemini (`gemini-2.5-flash-lite`) | 무료 한도 최대, Vision + 텍스트 통합 |
| 프론트 | React (Vite) | 가벼운 SPA, 빠른 빌드 |
| 인증 | Supabase Auth + PyJWT | ES256+JWKS로 JWT 검증 (백엔드 직접 처리) |
| 배포 | Railway (백엔드) + Vercel (프론트) | 무료/저비용 PaaS |

### 기술 결정 주의사항

- **Gemini 무료 티어**: 입력 데이터를 학습에 사용할 수 있음. 개발·테스트는 가짜/스톡/본인 사진으로만 진행. 실사용자의 사진·자기소개를 받는 서비스를 운영할 시점에 유료 플랜으로 전환 필수.
- **supabase-py 미사용**: 클라이언트 라이브러리 대신 SQLAlchemy로 Session Pooler에 직접 연결. JSONB 비정형 데이터를 자유롭게 다룰 수 있고 의존성이 단순.
- **목소리(Whisper) 입력 제거** (2026-06-12): 구현 복잡도 대비 핵심 차별점이 아니라고 판단. 외모/성격 두 기준만 유지.
- **Railway `DATABASE_URL` 충돌 주의**: Railway에 자체 PostgreSQL 서비스가 연결돼 있으면 `DATABASE_URL`을 빈 값으로 자동 주입해 덮어씀. 변수명을 `SUPABASE_DATABASE_URL`로 사용해 충돌 회피.

---

## 시스템 아키텍처

```
[브라우저 — Vercel]
  React SPA
    ↓ HTTPS + Bearer JWT
[FastAPI — Railway]
  /generate-from-photo  → vision.py (Gemini Vision)
  /generate             → generator.py (Gemini Text)
                             ↓
                          judge.py → fixer.py (자가교정)
  /scripts              → DB CRUD
  /scripts/{id}/analyze → analyze.py (Gemini — 힌트·전체 분석)
  /admin/*              → require_admin 미들웨어
    ↓ SQLAlchemy (Session Pooler)
[Supabase Postgres]
  scripts  테이블 (JSONB inputs / feedback)
  analysis 테이블 (7개 레이어 + AI 분석 JSONB)

[Supabase Auth]
  JWT 발급(ES256) → 브라우저 보관 → API 헤더로 전달
    → PyJWKClient(JWKS) 검증 → user UUID 반환
```

---

## DB 스키마

### `scripts` 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | bigint PK | 자동 증가 |
| `created_at` | timestamptz | 서버 기본값 |
| `source` | text | `ai` \| `manual` |
| `track` | text | `appearance` \| `personality` |
| `title` | text | 대사 제목 |
| `setup` | text | 상황 설명 |
| `script_text` | text | 독백 대사 본문 |
| `fit_reason` | text | 인물 목적(행동 동사) |
| `inputs` | jsonb | `{appearance_keywords, self_intro}` |
| `feedback` | jsonb | 오디션 피드백 배열 `[{date, venue, result, memo, created_at}]` |
| `user_id` | uuid | Supabase Auth 사용자 UUID |

마이그레이션 스크립트: `backend/migrate_add_feedback.py`, `backend/migrate_add_user_id.py`

### `analysis` 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | bigserial PK | 자동 증가 |
| `created_at` | timestamptz | 서버 기본값 |
| `script_id` | bigint FK→scripts(id) | ON DELETE CASCADE |
| `user_id` | uuid | Supabase Auth 사용자 UUID |
| `subtext` | text | 서브텍스트 (사용자 작성) |
| `action_verb` | text | 행동 동사 (사용자 작성) |
| `emotion_arc` | text | 감정선 흐름 (사용자 작성) |
| `context` | text | 상황·전사 (사용자 작성) |
| `character_bg` | text | 인물 배경 (사용자 작성) |
| `relationship` | text | 관계 분석 (사용자 작성) |
| `real_goal` | text | 진짜 목표 (사용자 작성) |
| `ai_analysis` | jsonb | AI가 생성한 7개 레이어 분석 결과 |

마이그레이션 스크립트: `backend/migrate_create_analysis.py`

---

## 구현 단계별 내역

### STEP 0 — 프롬프트 설계·검증 (`prompt_test/`)

백엔드 개발 전 Jupyter 노트북에서 프롬프트 파이프라인을 검증했다.

**핵심 파일**
- `prompt_test/build.py`: 프롬프트 원본. 실행하면 `notebook.ipynb` 재생성 (API 호출 없음). 노트북을 직접 수정하면 다음 빌드에 덮어씌워지므로, 프롬프트 수정은 항상 `build.py`에서.
- `prompt_test/validation_agent.py`: 생성 → 검사(regex + Gemini judge) → 교정(fixer, 최대 2회) → 악화방지 회귀가드. 출력만 교정하고 프롬프트는 건드리지 않음.
- `prompt_test/judge_check.py` / `fixer_check.py`: 검사기·교정기 성능 단위 테스트. 고정 픽스처로 생성 없이 judge/fix 자체만 검증.

**출력 스키마** (`track_A_appearance` / `track_B_personality` 각각)
```json
{
  "title": "대사 제목",
  "situation": "상대 + 전사 + 지금 상황",
  "objective": "인물의 목적 (행동 동사)",
  "script": "독백 대사 본문"
}
```

**검증 결과** (2026-06-15)
- judge 결함탐지: 4/4, 클린 오탐: 0
- fixer 해결: 6/7, 부작용: 0, 악화방지 가드 정상 발동 1회

**응답 캐시**: `GENAI_CACHE=1` 환경변수 설정 시 `.genai_cache/`에 캐싱. judge_check/fixer_check 실행 시 자동 활성화 — 무료 일일 한도 절약.

---

### MVP Phase 1 — 백엔드 기반 구축

**구현 내용**
- FastAPI 앱 초기화 (`backend/main.py`)
- SQLAlchemy 연결 모듈 (`backend/db.py`) — Session Pooler, `pool_pre_ping=True`
- `scripts` 테이블 모델 (`backend/models.py`)
- Pydantic 스키마 (`backend/schemas.py`)
- DB 초기화 스크립트 (`backend/init_db.py`)
- 헬스체크 엔드포인트: `GET /`, `GET /health`, `GET /health/db`
- 아카이브 CRUD: `POST /scripts`, `GET /scripts`, `GET /scripts/{id}`

---

### MVP Phase 2 — 대사 생성 엔드포인트 + 프론트엔드

**백엔드**
- `backend/generator.py`: Gemini 호출, 2트랙 JSON 파싱
- `backend/llm.py`: Gemini 클라이언트 공통 모듈
- `backend/judge.py`: 대사 결함 검사 (regex + Gemini)
- `backend/fixer.py`: 결함 교정 + 악화방지 회귀가드
- `POST /generate`: 텍스트 입력(외모 키워드 + 자기소개) → 대사 2개 + judge/fixer 자동 적용
- `POST /generate-from-photo`: 사진 업로드 → Vision 키워드 추출 → 대사 2개

**Vision 파이프라인** (`backend/vision.py`)
- Gemini Vision으로 인물 사진의 시각적 특징만 키워드 추출
- "인물 평가" 아닌 "시각 정보"만 추출하도록 프롬프트 설계 (정책 우회)
- 429/503 재시도 로직 내장 (최대 5회)

**프론트엔드** (`frontend/src/App.jsx`)
- React SPA, Vite 빌드, 다크 테마
- 사진 업로드 미리보기 → 자기소개 입력 → 대사 생성 → 2트랙 카드 표시
- 트랙별 아카이브 저장 버튼
- 반응형 레이아웃, 개인정보 고지 문구

---

### 아카이브 기능

- `GET /scripts` — 본인 대사 목록 (최신순), 로그인 필요
- 프론트: "아카이브 보기" 버튼 → 저장된 대사 카드 목록
- 트랙별 색상 구분 (외모 기반 / 성격 기반)

---

### 오디션 피드백 기능

- `PATCH /scripts/{id}/feedback` — 피드백 한 건 누적 append
- 피드백 항목: 날짜, 작품·오디션명, 결과(합격/불합격/대기), 메모
- DB: `scripts.feedback` JSONB 배열로 저장 (`migrate_add_feedback.py`로 컬럼 추가)
- 프론트: 아카이브 각 대사 하단 "+ 피드백 추가" 폼

---

### Supabase Auth 연결

- `backend/auth.py`: Supabase JWT를 **ES256 + JWKS** 방식으로 검증 → `user_id` (UUID) 반환
  - `PyJWKClient`가 `{SUPABASE_URL}/auth/v1/.well-known/jwks.json`에서 공개키 자동 조회·캐싱
  - `PyJWT[crypto]` + `cryptography` 패키지 필요 (ES256 지원)
  - HS256(JWT Secret) 방식은 Supabase가 실제로 ES256을 사용하므로 동작하지 않음
- 모든 API 엔드포인트에 `Depends(get_current_user)` 적용
- `scripts.user_id` 컬럼 추가 (`migrate_add_user_id.py`) — 사용자별 데이터 분리
- 프론트 `frontend/src/supabase.js`: `@supabase/supabase-js` 클라이언트
- 로그인/회원가입/로그아웃 UI (`Login` 컴포넌트)

---

### 어드민 기능

- `backend/admin.py`: `ADMIN_USER_ID` 환경변수와 일치하는 사용자만 `/admin/*` 접근
- `GET /admin/check`: 어드민 여부 확인 (200 = 어드민)
- `GET /admin/stats`: 전체 대사 수, 사용자 수, 트랙별 통계
- `GET /admin/scripts`: 전체 사용자 대사 목록 (최신순 200개, user_id 포함)
- 프론트: 어드민 로그인 시 "관리자 패널" 버튼 표시 → 통계 카드 + 대사 테이블

**어드민 계정 등록 방법**
1. 앱에서 어드민으로 쓸 이메일로 회원가입
2. Supabase 대시보드 → Authentication → Users → 해당 이메일의 UUID 복사
3. Railway 환경변수에 `ADMIN_USER_ID=<복사한-UUID>` 추가 후 재배포

---

### 배포

**백엔드 — Render**
- Root Directory: `backend/`
- Runtime: Python 3
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- URL: `https://scenemate.onrender.com`
- Free 인스턴스 (15분 비활성 시 슬립 → 첫 요청 30~50초 대기)

**프론트엔드 — Vercel**
- 설정 파일: `frontend/vercel.json` (SPA 리라이트 규칙)
- Root Directory: `frontend/`
- 빌드: `npm run build` / 출력: `dist/`

---

### v3 — 대사 분석 기능

아카이브의 기존 대사를 선택해 7개 레이어를 직접 작성하고, AI 분석과 나란히 비교하는 학습 기능.

**백엔드**
- `backend/analyze.py`: Gemini 기반 레이어별 힌트·전체 분석 생성
- `POST /scripts/{id}/analyze` — 특정 레이어 힌트 반환 (저장 없음)
- `GET /scripts/{id}/analyze/full` — 저장된 분석 조회
- `POST /scripts/{id}/analyze/full` — 사용자 7개 레이어 저장 + AI 전체 분석 생성 (upsert)
- DB: `analysis` 테이블 추가 (`migrate_create_analysis.py`)

**7개 분석 레이어**

| 키 | 레이블 |
|----|--------|
| `subtext` | 서브텍스트 |
| `action_verb` | 행동 동사 |
| `emotion_arc` | 감정선 흐름 |
| `context` | 상황·전사 |
| `character_bg` | 인물 배경 |
| `relationship` | 관계 분석 |
| `real_goal` | 진짜 목표 |

**프론트엔드**
- 아카이브 각 대사 하단 "분석하기" 버튼 → `AnalysisScreen`
- `AnalysisScreen`: 7개 레이어 textarea + 레이어별 "힌트" 버튼 → "분석 완료" 제출
- `CompareScreen`: 내 분석 | AI 분석 2열 그리드 비교 (모바일 세로 스택)

**Railway 마이그레이션**: `python migrate_create_analysis.py`를 Railway Console에서 실행해야 `analysis` 테이블이 생성됨.

---

## API 레퍼런스

모든 엔드포인트(헬스체크 제외)는 `Authorization: Bearer <supabase-jwt>` 헤더 필요.

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/` | 서비스 상태 |
| GET | `/health` | 헬스체크 |
| GET | `/health/db` | DB 연결 확인 |
| POST | `/generate` | 텍스트 입력 → 대사 2개 |
| POST | `/generate-from-photo` | 사진 + 자기소개 → 대사 2개 |
| POST | `/scripts` | 대사 저장 |
| GET | `/scripts` | 내 대사 목록 |
| GET | `/scripts/{id}` | 대사 단건 조회 |
| PATCH | `/scripts/{id}/feedback` | 오디션 피드백 추가 |
| POST | `/scripts/{id}/analyze` | 레이어별 힌트 반환 |
| GET | `/scripts/{id}/analyze/full` | 저장된 분석 조회 |
| POST | `/scripts/{id}/analyze/full` | 사용자 분석 저장 + AI 분석 생성 |
| GET | `/admin/check` | 어드민 여부 확인 |
| GET | `/admin/stats` | 전체 사용 통계 |
| GET | `/admin/scripts` | 전체 대사 목록 (어드민 전용) |

### POST /generate

```json
// 요청
{
  "appearance_keywords": "단발, 검정 터틀넥, 차분한 인상",
  "self_intro": "겉은 조용한데 속에 불이 있어요.",
  "save": false
}

// 응답
{
  "track_A_appearance": {
    "title": "...", "situation": "...", "objective": "...", "script": "..."
  },
  "track_B_personality": {
    "title": "...", "situation": "...", "objective": "...", "script": "..."
  },
  "appearance_keywords": "단발, 검정 터틀넥, 차분한 인상",
  "saved_ids": null
}
```

### POST /generate-from-photo

`multipart/form-data` 전송:
- `photo`: 이미지 파일
- `self_intro`: 자기소개 텍스트
- `save`: `true` / `false`

---

## 환경변수

### 백엔드 (Railway)

| 변수 | 설명 |
|------|------|
| `SUPABASE_DATABASE_URL` | Supabase Session Pooler URL (`postgresql://postgres.<ref>:<pw>@aws-X-<region>.pooler.supabase.com:5432/postgres`) |
| `SUPABASE_URL` | Supabase 프로젝트 URL (`https://<ref>.supabase.co`) — JWKS 공개키 조회에 사용 |
| `GOOGLE_API_KEY` | Google AI Studio API 키 |
| `ADMIN_USER_ID` | 어드민 계정 UUID (Supabase Auth → Users에서 확인) |

> **주의**: `DATABASE_URL`은 Railway 내부 PostgreSQL 서비스가 있을 경우 자동 주입되어 덮어써짐. 반드시 `SUPABASE_DATABASE_URL` 사용.
> `SUPABASE_JWT_SECRET`은 사용하지 않음 — ES256+JWKS 방식으로 공개키를 직접 조회하므로 불필요.

### 프론트엔드 (Vercel)

| 변수 | 설명 |
|------|------|
| `VITE_API_URL` | Railway 백엔드 URL |
| `VITE_SUPABASE_URL` | Supabase 프로젝트 URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon key |

---

## 향후 로드맵

| 버전 | 기능 | 상태 |
|------|------|------|
| v2 | 임베딩 유사도 기반 대사 추천 (Supabase pgvector) | 미착수 |
| v3 | 대사 분석 학습 기능 (7레이어 작성 + AI 비교) | 완료 |

**v2 진입 전 필수**: Gemini 유료 플랜 전환 (실사용자 생체정보 수집 전).
