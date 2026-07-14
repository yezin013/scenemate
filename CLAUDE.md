# SceneMate — Claude 작업 지침

## 세션 시작 시 필수

대화를 시작할 때 **항상 먼저** 아래를 실행해 로컬을 원격과 맞춰라.

```
git fetch origin
git status
```

원격에 새 커밋이 있으면(`origin/main`이 앞서 있으면) `git pull`을 실행하고 변경 파일 목록을 한 줄로 알려라. 이미 최신이면 "최신 상태입니다"라고만 짧게 말하고 넘어가라.

---

## Claude 행동 규칙

세션 종료 전 또는 주요 작업 완료 시 **반드시** 이 파일(CLAUDE.md)을 업데이트하라.
업데이트 항목:
- 완료된 작업 → "완료된 것" 목록에 추가
- 새로 알게 된 환경변수/설정 → "환경변수 주의사항"에 추가
- 남은 작업 변경 시 → "남은 작업" 업데이트
- 배포 URL 변경 시 → "배포 정보" 업데이트

**절대 로그처럼 쌓지 말 것. 항상 현재 상태로 덮어쓸 것. 파일은 100줄 이내로 유지.**

---

## 프로젝트 현황

### 완료된 것

- STEP 0: 프롬프트 설계·검증 (judge/fixer 파이프라인, 2트랙 출력 스키마)
- MVP Phase 1: FastAPI + Supabase Postgres + scripts 테이블 + 아카이브 CRUD API
- MVP Phase 2: 대사 생성 엔드포인트 2종(`/generate`, `/generate-from-photo`) + 프론트 연결
- 아카이브 기능: 저장/조회 UI
- 오디션 피드백 기능: `PATCH /scripts/{id}/feedback`, 프론트 폼
- Supabase Auth: 로그인/회원가입/로그아웃, user_id별 데이터 분리, ES256+JWKS JWT 검증
- 어드민 패널: `/admin/check`, `/admin/stats`, `/admin/scripts`
- 배포: Render(백엔드) + Vercel(프론트) — 비용 0원
- v3 대사 분석 기능: `analysis` 테이블 + 7개 레이어 입력/힌트/AI 비교 화면
- v2: 임베딩 유사도 기반 대사 추천 (Gemini text-embedding-004 + Supabase pgvector 코사인 유사도, `GET /scripts/{id}/similar`)
- 안정화: judge/fixer 백그라운드 처리·타임아웃 대응, CORS/503 오류 수정, Gemini rate limit 크래시 방지
- 프론트 리팩토링: `App.jsx`(747줄→라우팅만) → `api.js` + `screens/{Login,GenerateScreen,ArchiveScreen,AnalysisScreen,CompareScreen,AdminPanel}.jsx` 분리, 컴포넌트별 커밋 8개

### 남은 작업 (순서 확정 — 2026-07-14, 1번 완료로 재번호)

1. 시뮬레이터 2-a. 프롬프트 검증 — 단일 "면접관" 페르소나(장르별 3분할 안 함) + 난이도 3단계. `prompt_test/`의 `GENAI_CACHE` 캐시 재사용(무료 쿼터 절약).
2. 시뮬레이터 DB 스키마 설계 + 테이블 생성 — `scripts`는 독백용 스키마라 시뮬레이터(대화 히스토리·난이도·오디션 결과)엔 안 맞음. 새 테이블(예: `simulations`, 대화 히스토리는 JSONB) 필요. `init_db.py`(없는 테이블만 생성, 컬럼 변경 불가)로는 안 됨 — `migrate_create_analysis.py`와 같은 방식으로 `migrate_create_simulations.py` 작성해 raw SQL 직접 실행.
3. 시뮬레이터 2-b. HTTP 멀티턴 구현 (대화 히스토리 + 아카이브 자동저장) — 핵심 가치는 여기서 완성.
4. Recharts 성장 그래프 — 2-b에서 이미 데이터가 쌓이기 시작하므로 2-c(WebSocket) 완료를 기다릴 필요 없음.
5. 시뮬레이터 2-c. WebSocket 스트리밍 전환 — **조건부**. Render 무료 인스턴스는 15분 유휴 슬립인데, WebSocket은 연결 유지형 프로토콜이라 슬립 복귀 중 연결 실패·재연결 로직이 필요해 "전송 방식만 교체"보다 일이 큼. 2-b로 핵심가치는 이미 완성이므로, 2-b 완료 후 "HTTP로 충분하다" 판단되면 스킵/보류 가능. Redis pub/sub은 스킵(서버 1대라 불필요).
6. Redis 캐싱 + Gemini 유료 전환 — 실사용자(사진) 받기 직전에 함께. Redis는 API 비용 절감용이라 유료 전환 전엔 절감할 비용이 없음. Gemini는 무료 티어가 입력 데이터를 학습에 쓸 수 있어 실사진 받기 전 필수.
7. Whisper STT — 드랍 후보 (2026-06-12에 생성 입력에서 이미 한 번 뺀 전례 있음).

---

## 배포 정보

| 서비스 | 플랫폼 | URL |
|--------|--------|-----|
| 백엔드 | Render (무료, 슬립 있음) | https://scenemate.onrender.com |
| 프론트 | Vercel (무료) | Vercel 대시보드 확인 |
| DB | Supabase Postgres | ref: yttsqbvlhuolcqbsgjky (ap-southeast-2) |

---

## 환경변수 주의사항

### 백엔드 (Render)

| 변수 | 설명 |
|------|------|
| `SUPABASE_DATABASE_URL` | Supabase Session Pooler URL. `DATABASE_URL` 사용 금지 — Render 등 일부 플랫폼이 자동 주입해 덮어씀 |
| `SUPABASE_URL` | Supabase 프로젝트 URL (`https://<ref>.supabase.co`) — JWKS 공개키 조회에 사용 |
| `GOOGLE_API_KEY` | Google AI Studio API 키 |
| `ADMIN_USER_ID` | 어드민 계정 UUID |

### 프론트 (Vercel)

| 변수 | 설명 |
|------|------|
| `VITE_API_URL` | Render 백엔드 URL |
| `VITE_SUPABASE_URL` | Supabase 프로젝트 URL |
| `VITE_SUPABASE_ANON_KEY` | Supabase anon key |

### 주의

- `SUPABASE_JWT_SECRET` 사용 안 함 — Supabase는 ES256 알고리즘 사용. `PyJWKClient`로 JWKS에서 공개키 직접 조회.
- `backend/.env`와 `prompt_test/.env`는 .gitignore 처리됨. 커밋 전 항상 확인.
