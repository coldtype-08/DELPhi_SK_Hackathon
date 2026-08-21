# 04. API 스펙 (FE ↔ BE 계약)

> 규칙: 이 문서와 실제 응답이 다르면 **버그**다. 형태를 바꾸는 사람이 이 문서를 같은 커밋에서 고친다.
> 프론트는 백엔드가 준비되기 전 `fixtures/`(아래 §9)로 개발을 시작한다. Base URL: `http://localhost:8000/api`
> 공통: 성공 `{ "data": ... }`, 실패 `{ "error": { "code": string, "message_ko": string } }`. 날짜는 ISO 8601.

## 0. 공통 헤더 — 롤과 목적 권한 (docs/02 §9)

모든 요청에 `X-Delphi-Role` 헤더를 붙인다. 값: `ADMIN`(시연·운영, 열람 전용 — 08/20) `MEDICAL_AFFAIRS` `CLINICAL_STRATEGY` `SAFETY` `COMMERCIAL` `DATA_STEWARD`. 미지정 시 `CLINICAL_STRATEGY`로 간주(MVP 편의). 시연 로그인 화면은 페르소나 선택 = 헤더 값 결정 장치이며 실제 인증은 파일럿(SSO) 몫이다.

- 서버는 롤에 허용된 `purpose_domain`으로만 조회한다. 권한 밖 리소스는 **`403` + `{"error":{"code":"PURPOSE_SCOPE_VIOLATION"}}`** — 빈 배열로 감추지 않는다.
- `COMMERCIAL` 롤 응답에서는 `rawText`·`verbatimQuote`·`hcpRef`가 **필드 자체로 존재하지 않고**, 집계는 `distinctHcp ≥ 3` 그룹만 반환된다.
- 프론트는 롤을 화면에서 필터링하지 않는다 (권한은 서버의 책임). Console 우상단 롤 스위처는 시연용 헤더 전환 장치일 뿐이다.

## 1. Documents & Sense

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/documents` | 문서 목록 (+ 추출 상태 요약) |
| GET | `/documents/{id}` | 원문 + 메타 (원문 하이라이트용) |
| POST | `/documents/{id}/extract` | Sense 추출 실행 → claim 후보 생성 |

`GET /documents/{id}` 응답 예 (08/14 개정: 1문서=N인터랙션 — `HIGHLIGHT_DOC` 대응):
```json
{ "data": {
  "id": "DOC-20251201-001", "sourceType": "HIGHLIGHT_DOC", "sourceFormat": "DOCX",
  "language": "EN", "occurredOn": "2025-12-01",
  "rawText": "…문서 전문(마스킹 후)…",
  "interactions": [
    { "interactionId": "INT-20251201-001", "hcpRef": "HCP-003", "region": "MIDWEST",
      "specialty": "NEUROLOGY", "setting": "COMMUNITY", "blockIndex": 1,
      "docCharStart": 120, "docCharEnd": 940 }
  ],
  "claimCounts": { "candidate": 4, "approved": 2, "rejected": 0 }
} }
```
- 1문서=1면담 유형(MEETING_NOTE 등)이면 `interactions`가 1개이고 `blockIndex`·`docCharStart/End`는 null.
- 원문 하이라이트는 항상 `rawText`(문서 전문) 위에 claim의 evidence 오프셋으로 그린다 — 하이라이트형에서는 블록 경계도 함께 표시해 "AI가 HCP별로 분리했다"를 보여준다.

## 2. Claims (검토·승인)

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/claims?status=CANDIDATE&documentId=` | 검토 목록 |
| PATCH | `/claims/{id}` | body: `{ "action": "approve" \| "reject" \| "amend", "amendments": {…}, "reviewedBy": "건태" }` |

Claim 객체 (공통 형태 — Field·Console 동일):
```json
{ "id": "CLM-0042", "interactionId": "INT-20250912-001",
  "signalType": "TREATMENT_BARRIER", "patientSegment": "ELDERLY_65_PLUS",
  "journeyStage": "TITRATION", "barrierType": "DDI_CONCERN",
  "solicitation": "UNSOLICITED", "sentiment": null,
  "indicationMention": null, "concomitantDrugs": null, "administrationNote": null,
  "summaryKo": "고령 병용환자에서 상호작용 걱정으로 시작을 주저함",
  "verbatimQuote": "어르신들은 약이 워낙 많아서 상호작용부터 걱정된다고 하셨다",
  "evidence": { "docId": "DOC-20250912-001", "charStart": 412, "charEnd": 448 },
  "purposeDomain": "MEDICAL", "labelScope": "IN_LABEL",
  "reviewGrade": "HIGH", "status": "CANDIDATE", "contractVersion": "0.1" }
```

`GET /claims?queue=review` — docs/02 §5.5의 **위험 기반 검토 큐**를 서버가 정렬해서 반환한다 (① 가설 후보가 참조하는 claim → ② 반복 수 상위 → ③ 저등급 우선). 프론트가 정렬하지 않는다. 각 행에 `queueReasonKo`("HYP-001 근거로 사용됨" 등)를 포함해 왜 위에 있는지 화면에 보여준다.

## 3. Aggregates (전부 SQL 계산)

`GET /aggregates/signals?groupBy=patient_segment` →
```json
{ "data": { "computedBy": "SQL", "asOf": "2026-08-30T21:04:00+09:00", "rows": [
  { "patientSegment": "ELDERLY_65_PLUS", "signalType": "TREATMENT_BARRIER",
    "claimCount": 14, "distinctHcp": 9, "distinctRegions": 3,
    "monthly": [ { "month": "2026-05", "count": 3 }, { "month": "2026-06", "count": 5 } ] }
] } }
```
`GET /aggregates/kpis` → 홈 KPI 스트립용 `{ approvedClaims, distinctHcp, openHypotheses, pendingReviews }`.

- 모든 집계 응답은 `computedBy: "SQL"`과 `asOf`를 반드시 포함한다 (절대 규칙 #1을 응답 구조로 증명).
- 집계 대상은 `status = APPROVED`만. CANDIDATE·REJECTED는 어떤 숫자에도 들어가지 않는다 (절대 규칙 #3).
- `COMMERCIAL` 롤: `hcpRef` 없음 + `distinctHcp ≥ 3` 그룹만 반환 (docs/02 §9). 억제된 행 수는 `suppressedRowCount`로 알려준다 — 숨겼다는 사실 자체는 숨기지 않는다.

`GET /aggregates/radar` — **후보 레이더** (docs/02 §5.6 · 08/20). `MEDICAL_AFFAIRS`·`CLINICAL_STRATEGY` 전용, 그 외 롤은 `403 PURPOSE_SCOPE_VIOLATION`.
```json
{ "data": { "computedBy": "SQL", "provisional": true,
  "labelKo": "승인 전 잠정 수치 — 공식 집계 아님", "asOf": "2026-08-24T21:00:00+09:00",
  "rows": [
    { "patientSegment": "PEDIATRIC_TRANSITION", "signalType": "UNMET_NEED",
      "candidateCount": 11, "approvedCount": 3, "distinctHcpProvisional": 7,
      "thresholdMet": true, "hypothesisId": "HYP-001" }
] } }
```
- `provisional: true`와 `labelKo`는 **필수** — 프론트는 이 라벨 없이 렌더하지 않는다 (docs/02 §5.6 화면 표기 규칙).
- `thresholdMet`·`hypothesisId`로 "이 잠정 신호가 어느 가설을 낳았는지"를 홈 카드에서 가설 상세로 바로 연결한다. 임계 미달 행은 `thresholdMet: false`, `hypothesisId: null`.
- 이 응답만 예외적으로 CANDIDATE를 센다. 용도는 docs/02 §5.6의 두 가지뿐이며, `/aggregates/signals`·`/aggregates/kpis`는 변함없이 APPROVED만 계산한다.

## 4. Hypotheses & Screen & Board

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/hypotheses` / `/hypotheses/{id}` | 목록 / 상세(아래 카드 객체) |
| POST | `/hypotheses/{id}/screen` | 에이전트 조사 실행 (SSE로 진행 상황 스트림: `agent_started` / `finding` / `agent_done`) |
| POST | `/hypotheses/{id}/board` | Board 심의 실행 (SSE: `minute` 이벤트 = 발언 1개) |
| POST | `/hypotheses/{id}/decision` | 사람의 결정 — body 아래. **승인이 실행 루프를 여는 지점** (08/21: `followUp` 단수 객체 → `actionItems` 배열로 개정) |
| GET | `/actions?hypothesisId=&status=` | Action Item 추적 (Console) — 행마다 `collectedClaimCount`(`computedBy: "SQL"`) 포함. `ADMIN`·`MEDICAL_AFFAIRS`·`CLINICAL_STRATEGY` 조회 가능 |

`POST /hypotheses/{id}/decision` body:
```json
{ "decision": "APPROVED", "decidedBy": "건태", "rationaleKo": "근거 생성 우선 검토 타당",
  "actionItems": [
    { "directiveKo": "청소년 환자 사례 시 이전 실패 약물 수 확인", "target": "FIELD_CHECKLIST", "ownerRole": "MEDICAL_AFFAIRS" },
    { "directiveKo": "연령 확대 가설 패키지 전문조직 검토 전달", "target": "SPECIALIST_REVIEW", "ownerRole": "CLINICAL_STRATEGY" } ] }
```
- Board·CEO의 제안(`board_minutes.action_item_json`)은 화면에 **PROPOSED 초안**으로 보여주고, 사람이 여기 채택해 보낸 것만 `ACTIVE`로 저장된다 (docs/01 §3 상태 머신).
- `HOLD`·`REJECTED`면 그 가설의 열린 액션은 서버가 `CLOSED` 처리. 응답은 저장된 actionItems(id 포함).

가설 카드 객체 (5단계 구분이 응답 구조에 그대로 반영):
```json
{ "id": "HYP-001", "titleKo": "청소년(12–17세) 약물난치성 초점발작 — 연령 확대 근거 생성 우선 검토",
  "kind": "DEVELOPMENT", "labelScope": "OUT_OF_LABEL", "commercialActionBlocked": true,
  "status": "BOARD_READY", "patientSegment": "PEDIATRIC_TRANSITION",
  "observedFacts":   [ { "statementKo": "…", "claimId": "CLM-0042" } ],
  "statisticalPatterns": [ { "statementKo": "9인의 독립 HCP가 3개 권역에서 14회 언급", "computedBy": "SQL" } ],
  "aiInterpretations":   [ { "statementKo": "…", "llmRunId": 812 } ],
  "strategicProposals":  [ { "statementKo": "후향적 RWE 검토 우선", "source": "CEO_AGENT" } ],
  "approvedActions":     [],
  "screenFindings": [ { "agent": "EVIDENCE", "findingType": "SUPPORT",
      "statementKo": "청소년 약물난치성 초점발작의 치료 선택지 제한 보고 (2024 코호트)",
      "sourceUrl": "https://pubmed.ncbi.nlm.nih.gov/…", "sourceLocator": "PMID:…",
      "sourceAsOf": "2026-08-26",
      "caveatKo": "초록 기준 요약입니다. 연구 설계·표본 규모는 원문에서 확인해야 합니다." } ],
  "boardMinutes": [ { "role": "MEDICAL", "positionKo": "…", "seq": 1 } ],
  "notBoardReadyReason": null }
```

- `caveatKo`·`sourceAsOf`는 외부 출처 finding에서 **필수**다 (docs/02 §10). 값이 없으면 프론트는 카드를 렌더하지 말고 개발 오류로 취급한다.
- `status: "NOT_BOARD_READY"`인 가설은 `notBoardReadyReason`에 사유 코드(`NO_APPROVED_BASIS` `SINGLE_SOURCE` `NO_EXTERNAL_EVIDENCE` `CRITIC_BLOCKED`, docs/01 §3)를 담고 **순위 필드를 내보내지 않는다.**
- `kind: "DEVELOPMENT"`면 `commercialActionBlocked: true`가 항상 동반되고, `COMMERCIAL` 롤에서는 이 가설이 목록·상세 모두에서 조회되지 않는다 (`403`).
- `approvedActions`는 결정 후 채워진다: `{ "actionItemId": "ACT-001", "directiveKo", "target", "status", "deliveredAt", "collectedClaimCount": 1, "computedBy": "SQL" }`. `collectedClaimCount`는 이 액션을 참조해(`checklistRefs`) 수집·**승인**된 claim 수 — 이 숫자의 +1이 실행 루프 닫힘의 화면 증거다 (docs/00 §1.5 #7).

## 5. Contract & SCP

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/contract/active` | 활성 버전 전체 스키마 (Field 폼·Console 필터가 이걸 신뢰) |
| GET | `/contract/proposals` | SCP 목록 (원문 사례 링크·반복/출처 수·영향 분석 포함) |
| POST | `/contract/proposals/{id}/decision` | `{ "decision": "APPROVED"\|"REJECTED", "decidedBy" }` — 승인 시 서버가 새 버전 ACTIVE화 |

## 6. Field 전용

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/field/form-config` | **활성 contract 기반 입력 폼 정의** — v0.2 승인 직후 이 응답이 바뀌는 게 데모 클라이맥스 |
| GET | `/field/briefing?hcpRef=` | 방문 전 체크리스트 — 미해결 질문 + **ACTIVE action_items** (각 항목에 `actionItemId`·`hypothesisId`·`origin` 포함). 첫 노출 시 서버가 `delivered_at` 기록 |
| POST | `/field/interactions` | 신규 면담 제출 `{ meta…, rawText, consentConfirmed, checklistRefs: ["ACT-001"] }` — `checklistRefs`(선택)는 이 면담이 참조한 체크리스트 항목. → 응답: claim 후보 배열 + safetyRouted 배열(분기 알림용) + maskedSpans(마스킹 위치) |
| PATCH | `/field/claims/{id}` | §2와 동일 (승인/수정/제외) |

`form-config` 응답 예:
```json
{ "data": { "contractVersion": "0.2", "fields": [
  { "key": "patientSegment", "labelKo": "환자군", "type": "select", "required": true,
    "options": [ { "value": "PEDIATRIC_TRANSITION", "labelKo": "청소년(12–17세) 전환기", "labelScope": "OUT_OF_LABEL" },
                 { "value": "ELDERLY_65_PLUS", "labelKo": "노인(65+)" },
                 { "value": "POST_STROKE", "labelKo": "뇌졸중 후 뇌전증", "isNew": true } ] },
  { "key": "checklist", "type": "checklist",
    "items": [ { "actionItemId": "ACT-001", "labelKo": "청소년 환자 사례 시 이전 실패 약물 수 확인", "origin": "BOARD_FOLLOW_UP" } ] } ] } }
```

- `checklist` 항목은 Contract가 아니라 **action_items에서 실시간으로** 합류한다 — Contract 버전이 안 바뀌어도 Board 결정 다음 날 체크리스트는 바뀐다. 실행 루프(액션)와 구조 루프(스키마)가 독립임이 이 응답 하나에서 보인다 (docs/01 §3 · 02 §8).

## 7. Safety & 로그 & 추적

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/safety/candidates` | **`SAFETY` 롤 전용** (다른 롤은 403). 목록·내용 모두 |
| PATCH | `/safety/candidates/{id}` | `ACKNOWLEDGED` 처리 |
| GET | `/logs/blocked` | Critic 차단 이력 (reason_code, detail, 원문 payload) |
| GET | `/llm-runs/{id}` | **생성 조건 조회** → `{ model, promptFile, promptVersion, schemaName, parserVersion, externalDataAsOf, latencyMs, createdAt }` (docs/01 §7). 화면의 "생성 조건 보기" 링크가 이걸 호출 |

## 8. 시스템

`GET /health` → `{ ok, demoOffline, activeContractVersion, dbSeededAt, cacheSnapshotAsOf }` — 시연 직전 육안 확인용.

## 9. Fixtures (계약 고정 장치)

- 위치: `docs/fixtures/*.json` — 이 문서의 모든 응답 예시를 파일로 저장 (파일명 = `GET_documents_id.json` 식).
- 프론트: 백엔드 미완성 구간은 fixtures를 그대로 import해서 개발. 필드명이 다르면 fixtures가 재판관.
- 백엔드: 라우터 완성 시 fixtures와 실제 응답을 비교하는 스모크 테스트 1개씩 (`backend/tests/test_contract_shapes.py`).
