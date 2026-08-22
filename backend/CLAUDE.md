# DELPHi Backend 규칙 [오너: 인혁 — 엔진 층]

- 실행: `uv run uvicorn app.main:app --reload` (포트 8000). API 계약은 `docs/04_API_SPEC.md` — 응답 모양을 바꾸면 **같은 커밋에서 문서부터** 고친다.
- 모든 claim·집계 조회는 `app/access.py` 단일 게이트 경유 (docs/02 §9). 권한 밖은 `403 PURPOSE_SCOPE_VIOLATION` — 빈 배열 반환 금지.
- LLM 호출은 `app/llm.py` 단일 래퍼만 (모델·프롬프트 버전·스키마·parser·외부시점을 `llm_runs`에 기록 — docs/01 §7). 프롬프트는 `app/prompts/*.md` [도메인 오너: 건태 — 수정 시 `[cross]` 태그].
- 수치는 SQL만 계산(절대 규칙 #1), **ANSI SQL만** 사용(Snowflake 이관 대비 — docs/01 §2), 집계는 APPROVED만(#3), AE는 safety 경로 분리(#6).
- 상태 머신·자동 생성 임계값·Action Item 흐름은 `docs/01 §3`. Contract는 `app/contract/*.yaml` — 실행 후 변경은 SCP 경로만(#4).
- 지금 상태는 스캐폴딩 stub — 교체 순서는 `docs/00 §3` 주차별 일정, 오늘 칸부터.
