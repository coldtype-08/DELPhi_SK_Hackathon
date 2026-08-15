# 프롬프트 저장소 [오너: 소정]

LLM 프롬프트는 코드에 하드코딩하지 않고 이 폴더의 `*.md`로 관리한다 (CLAUDE.md 코딩 컨벤션).

## 규약

- 파일 상단에 버전 헤더 주석 필수:
  ```
  <!-- version: sense-extract@1 | date: 2026-08-21 | change: 최초 작성 -->
  ```
- 프롬프트 수정 = 커밋 필수 (재현성 추적 대상 — docs/06 §3 특칙). `llm_runs.prompt_version`에 이 버전이 기록된다.
- 같은 입력 3회 실행해 결과가 흔들리면: temperature 0 확인 → few-shot 추가 → enum 정의를 더 좁게.

## 만들어질 파일 (docs/00 일정 기준)

| 파일 | 용도 | 일정 |
|---|---|---|
| `sense_extract.md` | 원석 → claim 후보 구조화 (HCP 블록 분리 포함) | 8/22 |
| `screen_field_signal.md` `screen_evidence.md` `screen_safety.md` `screen_critic.md` | Screen 4종 | 8/28 |
| `board_deliberate.md` `board_ceo.md` | Board 심의 + CEO 권고 | 8/29 |
