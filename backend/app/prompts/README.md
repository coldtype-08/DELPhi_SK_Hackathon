# 프롬프트 저장소 [오너: 건태 — 도메인 층 (08/18 개편)]

LLM 프롬프트는 코드에 하드코딩하지 않고 이 폴더의 `*.md`로 관리한다 (CLAUDE.md 코딩 컨벤션).

## 규약

- 파일 상단에 버전 헤더 주석 필수:
  ```
  <!-- version: sense-extract@1 | date: 2026-08-21 | change: 최초 작성 -->
  ```
- 프롬프트 수정 = 커밋 필수 (재현성 추적 대상 — docs/06 §3 특칙). `llm_runs.prompt_version`에 이 버전이 기록된다.
- 같은 입력 3회 실행해 결과가 흔들리면: temperature 0 확인 → few-shot 추가 → enum 정의를 더 좁게.

## 파일 (docs/00 일정 기준)

| 파일 | 용도 | 상태 |
|---|---|---|
| `sense_extract.md` | 원석 → claim 후보 구조화 | **08/22 작성 (v1)** |
| `screen_field_signal.md` `screen_evidence.md` `screen_safety.md` `screen_critic.md` | Screen 4종 | 8/28 |
| `board_deliberate.md` `board_ceo.md` | Board 심의 + CEO 권고 | 8/29 |

## sense_extract.md 를 고칠 때

- **`{{CONTRACT_VERSION}}`·`{{ENUMS}}`·`{{HCP_REF}}`·`{{SPECIALTY}}` 네 자리표시자는 지우지 마라.** 허용값 표는
  활성 Contract에서 자동으로 채워진다(`app/sense.py::_enum_table`) — 프롬프트에 enum을 손으로 적으면 v0.2 승인 후
  프롬프트만 구버전으로 남는다. 치환되지 않은 자리표시자가 있으면 `render()`가 실패시킨다.
- **버전 주석을 올리면 캐시가 통째로 무효가 된다** (`llm_cache` 키에 prompt_version이 들어간다).
  1,118블록을 다시 부르게 되므로, 문구 다듬기는 모아서 한 번에 올린다.
- 프롬프트가 인용문을 원문과 다르게 내면 `sense.py`가 **저장을 거부**한다 — 조용히 통과하지 않으니
  `rejectedNoEvidence` 카운트로 프롬프트 품질을 볼 수 있다. 이 숫자가 튀면 프롬프트를 의심한다.
