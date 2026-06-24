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
| 인증 | Supabase Auth + PyJWT | JWT 검증만 백엔드에서 직접 처리 |
| 배포 | Railway (백엔드) + Vercel (프론트) | 무료/저비용 PaaS |

### 기술 결정 주의사항

- **Gemini 무료 티어**: 입력 데이터를 학습에 사용할 수 있음. 개발·테스트는 가짜/스톡/본인 사진으로만 진행. 실사용자의 사진·자기소개를 받는 서비스를 운영할 시점에 유료 플랜으로 전환 필수.
- **supabase-py 미사용**: 클라이언트 라이브러리 대신 SQLAlchemy로 Session Pooler에 직접 연결. JSONB 비정형 데이터를 자유롭게 다룰 수 있고 의존성이 단순.
- **목소리(Whisper) 입력 제거** (2026-06-12): 구현 복잡도 대비 핵심 차별점이 아니라고 판단. 외모/성격 두 기준만 유지.

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
  /admin/*              → require_admin 미들웨어
    ↓ SQLAlchemy (Session Pooler)
[Supabase Postgres]
  scripts 테이블 (JSONB inputs / feedback)

[Supabase Auth]
  JWT 발급 → 브라우저 보관 → API 헤더로 전달 → PyJWT 검증
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

- `backend/auth.py`: Supabase JWT를 PyJWT로 직접 검증 → `user_id` (UUID) 반환
- 모든 API 엔드포인트에 `Depends(get_current_user)` 적용
- `scripts.user_id` 컬럼 추가 (`migrate_add_user_id.py`) — 사용자별 데이터 분리
- 프론트 `frontend/src/supabase.js`: `@supabase/supabase-js` 클라이언트
- 로그인/회원가입/로그아웃 UI (`Login` 컴포넌트)

**환경변수 (백엔드)**
- `SUPABASE_JWT_SECRET`: Supabase 대시보드 → Settings → API → JWT Secret

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

**백엔드 — Railway**
- 설정 파일: `backend/railway.toml`
- Root Directory: `backend/`
- 시작 명령: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- 헬스체크: `/health`

**프론트엔드 — Vercel**
- 설정 파일: `frontend/vercel.json` (SPA 리라이트 규칙)
- Root Directory: `frontend/`
- 빌드: `npm run build` / 출력: `dist/`

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
| `DATABASE_URL` | Supabase Session Pooler URL |
| `GOOGLE_API_KEY` | Google AI Studio API 키 |
| `SUPABASE_JWT_SECRET` | Supabase JWT Secret (Settings → API) |
| `ADMIN_USER_ID` | 어드민 계정 UUID (Supabase Auth → Users에서 확인) |

### 프론트엔드 (Vercel)

| 변수 | 설명 |
|------|------|
| `VITE_API_URL` | Railway 백엔드 URL |
| `VITE_SUPABASE_URL` | Supabase 프로젝트 URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon key |

---

## 향후 로드맵

| 버전 | 기능 |
|------|------|
| v2 | 임베딩 유사도 기반 대사 추천 (Supabase pgvector) |
| v3 | 오디션 시뮬레이터 · 대사 분석 학습 기능 |

**v2 진입 전 필수**: Gemini 유료 플랜 전환 (실사용자 생체정보 수집 전).
