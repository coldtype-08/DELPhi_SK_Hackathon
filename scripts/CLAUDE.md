# DELPHi Scripts 규칙 [오너: 인혁]

- `generate_corpus.py`: 각본(docs/03 §2)이 진실의 원천 — **신호 문장은 스크립트가 소유**하고 LLM은 주변 텍스트만 쓴다. 본문은 `corpus_bodies/*.json`(커밋 대상)을 우선 읽고, 규칙 위반이면 API로 조용히 넘어가지 말고 즉시 실패.
- 자가검증 필수(docs/03 §5): 신호 문장 정확히 1회 포함 · 문서 전문 기준 오프셋 계산 · 성별 대명사 금지 · docx/pdf 렌더 후 텍스트 재추출이 정본과 일치.
- 코퍼스 v3(08/21): 320문서/1,118단위, 신호 S1~S9 — 분포·검산은 docs/03 §1–2. 임계값 검산이 어긋나면 각본 dict부터 의심.
- S9(08/22, 가임기 여성)는 **임계에 1건 모자라도록** 심은 대조군이다 — 4건/3인. 이 값을 바꾸면 `assert_scenario`가 막는다.
- `seed_db.py`: manifest → documents+interactions 분리 적재. `reset_demo.sh`: 시연 초기 상태 복원 (시연 직전 항상 실행).
- `ground_truth.jsonl`은 채점 전용 — 서비스 로직이 읽으면 버그다.
