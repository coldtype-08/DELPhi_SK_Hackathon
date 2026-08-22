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

`POST /documents/{id}/extract` — **Sense 추출 실행 (08/22 구현).** 원석 1건을 의료진 블록별로 읽어 claim 후보를 만든다. `?force=true`면 기존 claim을 지우고 다시 돌린다(기본은 이미 추출된 문서를 건너뛴다).

```json
// 응답 — 숫자는 전부 서버가 센 것이다 (절대 규칙 #1)
{ "data": { "documentId": "DOC-20250406-180", "skipped": false,
            "blocks": 10, "claims": 7, "safety": 1, "safetyRerouted": 0,
            "rejectedNoEvidence": 2, "unmapped": 1,
            "byGrade": { "HIGH": 5, "MEDIUM": 1, "LOW": 1 } } }
```
- `rejectedNoEvidence`: 인용문이 **그 의료진 블록의 원문과 문자 단위로 일치하지 않아 저장을 거부한** 건수 (절대 규칙 #2). 버린 사실은 `blocked_log`에 `VERBATIM_NOT_FOUND`로 남는다. **이 숫자가 0이 아닌 것이 정상이고, 화면에 보여준다** — 막고 있다는 증거이기 때문이다.
- `safetyRerouted`: LLM이 이상사례를 claim으로 냈지만 서버가 safety 경로로 되돌린 건수 (절대 규칙 #6).
- 생성된 claim은 전부 `status: "CANDIDATE"` — 이 엔드포인트에는 승인 권한이 없다 (절대 규칙 #3).
- 권한: 원문을 읽는 작업이므로 `MEDICAL_AFFAIRS`·`CLINICAL_STRATEGY`만. 그 외는 `403 PURPOSE_SCOPE_VIOLATION`.
- `503 LLM_UNAVAILABLE`: 캐시에도 없고 API 키도 없을 때. **조용히 빈 결과를 주지 않는다.**

## 2. Claims (검토·승인)

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/claims?status=CANDIDATE&documentId=` | 검토 목록 |
| GET | `/claims?queue=review&hypothesisId=HYP-003` | **묶음 검토 큐** — 가설 1건이 딛고 선 근거만 (docs/02 §5.5) |
| PATCH | `/claims/{id}` | body: `{ "action": "approve" \| "reject" \| "amend", "amendments": {…}, "reviewedBy": "건태" }` |
| POST | `/claims/batch` | **일괄 승인 (08/22 신설)** — 아래 참조 |

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

각 행에는 **검토등급의 근거**도 함께 온다 — 등급 문자만으로는 방향(H가 안전, L이 위험)이 읽히지 않는다 (docs/02 §5.5).
```json
{ "reviewGrade": "MEDIUM", "defaultChecked": false,
  "gradeReasonKo": "② 용어 매핑 실패 — 'refractory GTC'가 스키마 값에 없어 UNSPECIFIED로 낙착",
  "failedChecks": ["TERM_MAPPING"], "scpCandidate": true }
```
- `failedChecks` 허용값: `TERM_MAPPING`(②) · `DERIVED_RULE`(③). **`VERBATIM_MATCH`(①)는 나올 수 없다** — 원문 불일치는 저장 단계에서 거부되므로 큐에 존재하지 않는다(절대 규칙 #2).
- `defaultChecked`: 3종 통과(=`HIGH`) = `true`, 하나라도 실패(`MEDIUM`·`LOW`) = `false`. **프론트가 판단하지 않는다.**
- 등급 대응: ② 실패 → `MEDIUM` · ③ 실패 → `LOW` · 둘 다 실패 → `LOW`. 큐 정렬은 `LOW → MEDIUM → HIGH`.
- `scpCandidate: true`면 그 행에서 SCP 제안 생성으로 바로 연결한다 (docs/02 §7).

### 2.5 `POST /claims/batch` — 일괄 승인 (08/22 신설)

묶음 검토 화면이 UI만 묶음이고 백엔드를 34번 부르면 의미가 없다. **한 번의 클릭 = 한 번의 호출**이어야 한다.

```json
// 요청
{ "action": "approve", "reviewedBy": "건태", "role": "CLINICAL_STRATEGY",
  "hypothesisId": "HYP-003",
  "claimIds": ["CLM-0418", "CLM-0433", "CLM-0447"] }

// 응답
{ "data": { "approved": 3, "skipped": 0, "failed": [],
            "reviewedAt": "2026-08-30T14:32:11+09:00",
            "aggregatesChanged": [
              { "patientSegment": "GENERALIZED_PGTC", "signalType": "UNMET_NEED",
                "officialBefore": 21, "officialAfter": 24, "provisional": 34 } ] } }
```
- **원자적이다** — 하나라도 실패하면 전부 롤백하고 `failed`에 사유를 담아 4xx. 부분 승인 상태를 만들지 않는다.
- `claimIds` 상한 **200건**. 넘으면 `400 BATCH_TOO_LARGE`.
- 감사 로그는 **건별로** 남긴다 (`audit_log` N행). 묶음은 UI·전송의 단위이지 책임의 단위가 아니다 — "누가 이 claim을 승인했나"는 건별로 답할 수 있어야 한다.
- `aggregatesChanged`로 **바뀐 공식 수치를 같은 응답에** 돌려준다. 프론트가 승인 직후 집계를 다시 조회하지 않아도 되고, 무엇보다 **"승인 → 숫자가 움직였다"를 한 화면에서** 보여줄 수 있다.
- 이미 APPROVED인 건은 오류가 아니라 `skipped`로 센다 (재클릭 안전).
- `action: "reject"`도 같은 형태로 지원. **체크 해제는 이 API를 부르지 않는다** — 해제는 CANDIDATE 유지일 뿐 반려가 아니다.

## 3. Aggregates (전부 SQL 계산)

`GET /aggregates/signals?groupBy=patient_segment` →
```json
{ "data": { "computedBy": "SQL", "asOf": "2026-08-30T21:04:00+09:00", "rows": [
  { "patientSegment": "ELDERLY_65_PLUS", "signalType": "TREATMENT_BARRIER",
    "claimCount": 41, "distinctHcp": 27, "distinctRegions": 4,
    "monthly": [ { "month": "2026-05", "count": 3 }, { "month": "2026-06", "count": 5 } ] }
] } }
```
`GET /aggregates/kpis` → 홈 KPI 스트립용 `{ approvedClaims, distinctHcp, openHypotheses, pendingReviews }`.

`GET /aggregates/pipeline` — **처리 라인 스트립 (08/22 신설)**. 원석 → 분석된 기록 → 신호 → 가설을 한 줄로 보여주는 응답. Console 전 화면 상단에 고정한다.
```json
{ "data": { "computedBy": "SQL", "asOf": "2026-08-30T21:04:00+09:00",
  "rawDocuments": 320,
  "analyzedRecords": 1118,
  "signals": { "provisional": 34, "official": 21, "labelKo": "잠정 / 공식" },
  "hypotheses": { "draft": 4, "nearThreshold": 1 } } }
```
- **`signals`는 두 숫자를 반드시 함께 반환한다.** 하나만 주면 화면이 어느 쪽인지 고르게 되고, 그때 절대 규칙 #3이 흐려진다. 잠정은 CANDIDATE 포함, 공식은 APPROVED만 — 계산식이 다르다는 사실을 응답 구조가 드러낸다.
- 화면 표기: 두 수를 **나란히**, 잠정에는 "승인 전 잠정 수치 — 공식 집계 아님" 라벨(docs/02 §5.6). **한 카드에 합산 금지**는 그대로다 — 나란히 놓는 것과 더하는 것은 다르다.
- `analyzedRecords`는 status와 무관한 **저장된 구조화 기록 수**다(용어: docs/02 §5.5 — 'DB에 들어와 셀 수 있게 된 기록'). 집계 수치가 아니므로 잠정/공식 구분이 없다.
- `COMMERCIAL` 롤: `signals.provisional`을 제거하고 `official`만 반환한다 (승인 전 데이터 비노출, docs/02 §5.6).

- 모든 집계 응답은 `computedBy: "SQL"`과 `asOf`를 반드시 포함한다 (절대 규칙 #1을 응답 구조로 증명).
- 집계 대상은 `status = APPROVED`만. CANDIDATE·REJECTED는 어떤 숫자에도 들어가지 않는다 (절대 규칙 #3).
- `COMMERCIAL` 롤: `hcpRef` 없음 + `distinctHcp ≥ 3` 그룹만 반환 (docs/02 §9). 억제된 행 수는 `suppressedRowCount`로 알려준다 — 숨겼다는 사실 자체는 숨기지 않는다.

`GET /aggregates/radar` — **후보 레이더** (docs/02 §5.6 · 08/20). `MEDICAL_AFFAIRS`·`CLINICAL_STRATEGY` 전용, 그 외 롤은 `403 PURPOSE_SCOPE_VIOLATION`.
```json
{ "data": { "computedBy": "SQL", "provisional": true,
  "labelKo": "승인 전 잠정 수치 — 공식 집계 아님", "asOf": "2026-08-24T21:00:00+09:00",
  "rows": [
    { "patientSegment": "PEDIATRIC_TRANSITION", "signalType": "UNMET_NEED",
      "candidateCount": 52, "approvedCount": 12, "distinctHcpProvisional": 34,
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
  "statisticalPatterns": [ { "statementKo": "34인의 독립 HCP가 4개 권역에서 52회 언급", "computedBy": "SQL" } ],
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

## 4.5 Market & External Refs (08/21)

| 메서드 | 경로 | 설명 |
|---|---|---|
| GET | `/market/refs?refType=LABEL_AGE` | 시장·경쟁 화면(`/market`)의 공개 참조 데이터. `external_refs` 테이블만 읽는다 — **가설과 연결되지 않으므로 `COMMERCIAL` 롤에도 열린다** (docs/02 §9.5) |

```json
{ "data": { "asOf": "2026-08-26", "refType": "LABEL_AGE", "rows": [
  { "subject": "cenobamate", "source": "OPENFDA", "minAge": 18, "indication": "partial-onset seizures",
    "sourceUrl": "https://api.fda.gov/drug/label.json?...",
    "caveatKo": "표기 시점의 허가사항이며, 최신 개정 여부는 원문 라벨에서 확인해야 합니다." } ] } }
```

- `asOf`·`caveatKo`는 **필수**. 스냅샷을 못 받은 항목은 행을 만들지 않는다 — 화면은 "스냅샷 대기" 트랙으로 렌더하고 **추정값을 채우지 않는다** (DECISIONS 08/21).
- `screen_findings`와 달리 `hypothesisId` 필드가 존재하지 않는다. 이 구조적 분리가 COMMERCIAL 개방의 근거다.

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

`POST /system/reset` — **초기 상태로 되돌리기 (08/22 신설).** `reset_demo.sh`의 서버판. 심사위원 여러 명이 같은 배포본을 순서대로 만지므로, 앞사람의 승인 상태를 다음 사람이 그대로 받지 않게 한다.
```json
// 요청  (헤더: X-Reset-Token — Railway 환경변수 RESET_TOKEN 과 대조)
{ "scope": "demo" }

// 응답
{ "data": { "ok": true, "resetAt": "2026-09-02T10:14:00+09:00",
            "restored": { "claims": 1118, "approvedClaims": 168,
                          "hypotheses": 4, "contractVersion": "0.1",
                          "actionItems": 0, "scpPending": 1 } } }
```
- **되돌리는 것**: claim status·승인 이력, 가설 상태와 Board 결과, `action_items`, SCP 승인, 활성 Contract 버전(v0.2 → v0.1).
- **건드리지 않는 것**: 원문 문서·`llm_runs`·외부 API 캐시. 원문은 불변이고(절대 규칙 #2), 캐시를 지우면 오프라인 시연이 깨진다.
- 토큰이 없거나 틀리면 `403 RESET_TOKEN_INVALID`. **토큰은 코드에 넣지 않는다** — 환경변수로만 (`docs/07`).
- 소요 5초 내외. 진행 중에는 `503 RESET_IN_PROGRESS`로 동시 요청을 막는다.
- 자정(KST) 자동 리셋과 같은 코드 경로를 쓴다 (`submission/2_결과물/README.md` 문제 해결 표).

## 9. Fixtures (계약 고정 장치)

- 위치: `docs/fixtures/*.json` — 이 문서의 모든 응답 예시를 파일로 저장 (파일명 = `GET_documents_id.json` 식).
- 프론트: 백엔드 미완성 구간은 fixtures를 그대로 import해서 개발. 필드명이 다르면 fixtures가 재판관.
- 백엔드: 라우터 완성 시 fixtures와 실제 응답을 비교하는 스모크 테스트 1개씩 (`backend/tests/test_contract_shapes.py`).
