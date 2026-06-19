# SceneMate — Claude 작업 지침

## 세션 시작 시 필수

대화를 시작할 때 **항상 먼저** 아래를 실행해 로컬을 원격과 맞춰라.

```
git fetch origin
git status
```

원격에 새 커밋이 있으면(`origin/main`이 앞서 있으면) `git pull`을 실행하고 변경 파일 목록을 한 줄로 알려라. 이미 최신이면 "최신 상태입니다"라고만 짧게 말하고 넘어가라.
