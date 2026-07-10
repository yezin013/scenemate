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

### 남은 작업

- 실사용자 받기 전: Gemini 유료 플랜 전환 (무료 티어는 입력 데이터 학습에 사용될 수 있음)

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
