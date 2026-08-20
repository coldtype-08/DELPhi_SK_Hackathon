# 02. Data Contract v0.1 (Seed Schema)

> 이 문서가 곧 제품이다. 여섯 곳(추출 출력·서버 검증·DB·Field 폼·대시보드 필터·에이전트 입력)이 이 하나의 정의를 공유한다.
> 코드화: `backend/app/contract/contract_v0_1.yaml`로 그대로 옮기고, 이 문서와 항상 동기화한다.
> **v0.1에는 의도적으로 `POST_STROKE`(뇌졸중 후 뇌전증)가 없다** — 코퍼스에 반복 등장시켜 SCP → v0.2 승격을 시연하기 위함.
> **08/19 부트스트랩 반영**: 격리 AI 초안(`docs/assets/bootstrap-ai-draft.md`) × 36컬럼 원안 × v0.1 3자 대조로 신규 9항목 채택(§2·§6),
> 용량 수치 5종·AI 사족 컬럼은 사유와 함께 제외, 직함·msl_response 등은 SCP 보류 (DECISIONS 08/19).

## 1. Interaction (면담 레코드)

| 필드 | 타입 | 필수 | 허용값/규칙 |
|---|---|---|---|
| interaction_id | string | ✓ | `INT-{YYYYMMDD}-{seq}` |
| occurred_on | date | ✓ | |
| hcp_ref | string | ✓ | 가명 코드 `HCP-###` (실명 저장 금지 — PII 마스킹 대상) |
| hcp_specialty | enum | ✓ | `NEUROLOGY` `EPILEPTOLOGY` `PSYCHIATRY` `GENERAL` |
| region | enum | ✓ | `NORTHEAST` `SOUTH` `MIDWEST` `WEST` (미국 4권역) |
| setting | enum | ✓ | `ACADEMIC` `COMMUNITY` `PRIVATE_PRACTICE` |
| source_type | enum | ✓ | `MEETING_NOTE` `CALL_NOTE` `EMAIL_SUMMARY` `VOICE_TRANSCRIPT` `HIGHLIGHT_DOC`(여러 HCP 인사이트를 한 문서에 묶은 실물 원석 형식 — 08/14) `CONGRESS_REPORT`(학회 참관 보고서, PDF 원석 — 08/14) |
| market | enum | ✓ | `US` (MVP 고정). 기획서의 "국가별 정책·시장별 조건"이 붙을 자리 — 값을 늘리려면 동의 규칙도 함께 정의해야 하므로 v0.1은 단일 값 |
| consent_confirmed | bool | ✓ | VOICE_TRANSCRIPT면 반드시 true (아니면 저장 거부) |
| raw_text | text | ✓ | 원문. **PII 마스킹 후** 저장, 이후 불변 (마스킹 전 원본은 저장하지 않는다) |
| masked_spans | json | | `[{char_start, char_end, kind: NAME\|PHONE\|EMAIL}]` — 무엇을 가렸는지의 기록. 값 자체는 남기지 않는다 |
| language | enum | ✓ | `EN` `KO` — 원석(기존 축적분 성격)은 EN, Field 신규 수집·음성 전사는 KO. **스키마·enum 코드는 언어 중립**, raw_text·verbatim은 원언어 보존 (08/14) |
| block_index | int | | 다중 HCP 문서(`HIGHLIGHT_DOC`·`CONGRESS_REPORT`) 전용: 문서 내 블록 순번 (그 외 null) |
| doc_char_start / doc_char_end | int | | 다중 HCP 문서 전용: 문서 전문(documents.raw_text) 내 이 블록의 범위 (1문서=1면담이면 null = 문서 전체) |

**다중 HCP 문서 규칙 (08/14 결정)**: `HIGHLIGHT_DOC`·`CONGRESS_REPORT`는 1개 문서 안에 HCP별 인사이트가 여러 개다 → **Sense 추출이 블록 단위로 분리해 interaction을 여러 건 생성**한다. 이때 raw_text는 해당 블록 텍스트, occurred_on은 문서 발행일(학회 보고서는 학회 종료일)을 쓴다. 1문서=1면담 유형은 기존과 동일하게 interaction 1건.

## 2. Claim (의미 단위 추출값) — Sense의 출력이자 검토·승인의 대상

| 필드 | 타입 | 필수 | 허용값/규칙 |
|---|---|---|---|
| claim_id | string | ✓ | `CLM-{seq}` |
| interaction_id | FK | ✓ | |
| product | enum | ✓ | `XCOPRI` (MVP 고정) |
| signal_type | enum | ✓ | `UNMET_NEED` `TREATMENT_BARRIER` `INFO_REQUEST` `POSITIVE_OUTCOME` `ACCESS_ISSUE` `REPURPOSING_SIGNAL`(미허가 적응증 언급 — 08/19, 자동 `OUT_OF_LABEL`) `SAFETY_CANDIDATE` `OTHER` |
| patient_segment | enum | ✓* | `PEDIATRIC_TRANSITION`(청소년 12–17세 전환기 — **허가 범위 밖**) `ELDERLY_65_PLUS` `DRE_2PLUS`(2제 이상 실패 약물난치성) `COMORBID_PSYCH` `FEMALE_CHILDBEARING` `NEW_ONSET_ADULT` `UNSPECIFIED` |
| label_scope | enum | 자동판정 | `IN_LABEL` `OUT_OF_LABEL` — `signal_type=REPURPOSING_SIGNAL`이거나 patient_segment가 허가 범위 밖(현재 `PEDIATRIC_TRANSITION`)이면 `OUT_OF_LABEL`로 태깅되고, 이 값을 참조하는 가설은 자동으로 `kind=DEVELOPMENT`가 되어 상업 액션 경로에서 제외된다 (절대 규칙 #5의 코드화) |
| journey_stage | enum | | `DIAGNOSIS` `INITIATION` `TITRATION` `MAINTENANCE` `SWITCH` `DISCONTINUATION` |
| barrier_type | enum | signal_type=TREATMENT_BARRIER면 ✓ | `TITRATION_COMPLEXITY` `DDI_CONCERN`(상호작용) `MONITORING_BURDEN` `REIMBURSEMENT` `AWARENESS_GAP` `FORMULATION_NEED` |
| solicitation | enum | | `UNSOLICITED` `SOLICITED_BY_MSL` `UNCLEAR` — 오프라벨 언급의 컴플라이언스 의미가 갈리는 축 (08/19, AI 부트스트랩 초안의 발견) |
| sentiment | enum | | `POSITIVE` `NEUTRAL` `NEGATIVE` `MIXED` — 발언 논조. **HCP 개인별 집계 금지**(절대 규칙 #7) — 세그먼트·토픽 단위 집계만 (08/19, 도메인 오너 판단으로 채택) |
| indication_mention | text | | 언급된 적응증·질환 원문 (autism, Lennox-Gastaut 등). **enum이 아님** — patient_segment의 SCP 각본(POST_STROKE)과 분리 유지 (08/19) |
| concomitant_drugs | text | | 병용 약물명, 쉼표 구분 (lamotrigine 등) — "특정 약물 병용 언급 N회" 집계용. 정규화는 vocab 계층 (08/19) |
| administration_note | text | | 투여법·제형 관찰 (분쇄 투여 등). **용량 수치는 의도적 제외** — 허위 정밀도·규제 민감 (08/19) |
| purpose_domain | enum | 자동판정 | `MEDICAL` `COMMERCIAL` `SAFETY` `PUBLIC_EVIDENCE` — 조회 권한의 단위 (§9). signal_type에서 결정론적으로 파생: `ACCESS_ISSUE`→`COMMERCIAL`, `SAFETY_CANDIDATE`→`SAFETY`(§6로 분리), 그 외→`MEDICAL` |
| verbatim_quote | text | ✓ | **원문에서 그대로 복사한 문장** — 원문 substring 여부를 서버가 검증 |
| summary_ko | string | ✓ | 한 줄 요약 (LLM 생성, 화면 표시용) |
| evidence | object | ✓ | `{doc_id, char_start, char_end}` — verbatim_quote 위치. **오프셋은 문서 전문(documents.raw_text) 기준**이며, 다중 HCP 문서면 해당 interaction의 블록 범위(doc_char_start~end) 안이어야 한다 |
| review_grade | enum | 자동계산 | `HIGH` `MEDIUM` `LOW` (§5 규칙) |
| status | enum | ✓ | `CANDIDATE` `APPROVED` `REJECTED` |
| contract_version | string | ✓ | 생성 당시 버전 (예: `0.1`) |
| reviewed_by / reviewed_at | | 승인 시 | |

*SAFETY_CANDIDATE는 이 테이블에 저장하지 않는다 → §6 분리 경로.

## 3. Controlled Vocabulary (동의어 정규화)

- 구조: `{surface_form, lang: EN|KO, canonical_id, canonical_label_ko, source}` — source: `MESH_REF`(임상 개념) 또는 `CUSTOM`(업무 개념).
- **다국어 정규화 원칙 (08/14)**: 영어·한국어 surface form이 **같은 canonical 코드**로 수렴한다 — "adolescent"도 "17세 환자"도 `PEDIATRIC_TRANSITION`. 시장·언어가 늘어도(향후 한국 출시 등) 스키마는 불변이고 정규화 계층만 확장한다. 영문 원석과 한국어 Field 수집이 **같은 집계에 합산**되는 것 자체가 시연 포인트다.
- 예시 (코퍼스와 세트로 관리, 최소 40쌍):
  - "17세 환자", "청소년", "성인 되기 전", "18세까지 기다" / "17-year-old", "adolescent", "can't use it until 18" → `PEDIATRIC_TRANSITION`
  - "고령", "어르신", "65세 이상", "노년층" / "elderly", "older adults", "geriatric" → `ELDERLY_65_PLUS`
  - "약을 여러 번 바꿔도", "2제 실패", "난치성", "DRE" → `DRE_2PLUS`
  - "용량 올리기 번거로움", "타이트레이션 부담", "적정 스케줄 복잡" → `TITRATION_COMPLEXITY`
  - "다른 약이랑 같이 쓸 때", "병용 시 상호작용", "DDI" → `DDI_CONCERN`
- 매핑 실패 표현은 `unmapped_terms`에 적재 → **반복되면 SCP 후보 신호**가 된다.

## 4. DB 테이블 (SQLAlchemy 기준)

```
documents(id, filename, source_format: TXT|DOCX|PDF, language, raw_text, sha256, imported_at)
                                               # id: DOC-{YYYYMMDD}-{seq}. 원본 식별자 + hash로 원문 역추적 (기획서 4-3)
                                               # raw_text = 마스킹 후 문서 전문(불변) — 모든 evidence 오프셋의 기준 (08/14)
interactions(§1 필드 전부, document_id FK nullable)
claims(§2 필드 전부)
vocab_terms(§3)
unmapped_terms(surface_form, first_seen_claim_id, occurrence_count)
safety_candidates(id, interaction_id, verbatim_quote, evidence_json,
                  event_terms, severity_note, product_named,     # 08/19 추가 — §6
                  routed_at, status: OPEN|ACKNOWLEDGED)
contract_versions(version, body_yaml, status: DRAFT|ACTIVE|RETIRED, approved_by, approved_at)
schema_change_proposals(id, kind: NEW_ENUM_VALUE|NEW_FIELD, target_field, proposed_value, rationale_ko,
                        example_claim_ids_json, occurrence_count, distinct_hcp_count, impact_note_ko,
                        status: PROPOSED|APPROVED|REJECTED, decided_by, decided_at)
hypotheses(id, title_ko, kind: IN_LABEL|DEVELOPMENT, status, segment, driver_summary_ko, created_from_aggregate_json)
screen_findings(id, hypothesis_id, agent: FIELD_SIGNAL|EVIDENCE|SAFETY|CRITIC,
                finding_type: SUPPORT|COUNTER|GAP|SAFETY_SIGNAL|BLOCK, statement_ko, source_url, source_locator, created_at)
board_minutes(id, hypothesis_id, role: MEDICAL|DEVELOPMENT|SAFETY|MARKET_ACCESS|CEO, position_ko, action_item_json, seq)
decisions(id, hypothesis_id, decision: APPROVED|HOLD|REJECTED, decided_by, rationale_ko, follow_up_json, decided_at)
blocked_log(id, source: CRITIC, reason_code, detail_ko, payload_json, created_at)
llm_runs(id, purpose, model, prompt_file, prompt_version, schema_name, parser_version,
         external_data_as_of, input_hash, output_hash, latency_ms, created_at)
```

`hypotheses`에는 `not_board_ready_reason`(docs/01 §3의 사유 코드, nullable)을, `screen_findings`에는 `source_as_of`(외부 스냅샷 일시)와 `caveat_ko`(해석 한계 문구, §10)를 함께 저장한다.

## 5. 검토등급(H/M/L) 규칙 — 결정론적 계산 (LLM 아님)

| 체크 | 내용 |
|---|---|
| A. 원문 일치 | verbatim_quote가 문서 전문(documents.raw_text)의 evidence 위치 텍스트와 일치하고, 해당 interaction 블록 범위 안에 있음 |
| B. 용어 매핑 | patient_segment·barrier_type이 vocab을 통해 canonical로 매핑됨 |
| C. 규칙 통과 | 필수 필드 존재, enum 위반 없음, barrier 조건부 규칙 충족 |

`HIGH = A∧B∧C`, `MEDIUM = A∧C (B 실패)`, `LOW = 그 외`. A 실패 시 저장 자체를 거부하고 재추출 큐로.

### 5.5 검토 큐 규칙 — "위험 기반 검토" (주관성 제거)

검토는 **전수 의무가 아니라 활용 조건**이다. 검토량은 데이터량이 아니라 **활용량**에 비례한다.
- 승인이 필요한 대상 = 집계·가설·Field Brief에 **실제 사용될 값**. 사용되지 않는 후보는 CANDIDATE로 남아도 무해(집계에서 자동 제외될 뿐).
- 검토 큐는 시스템이 결정론적으로 정렬한다: ① 가설 후보가 참조하는 claim → ② 미검토 신호 중 반복 수 상위 → ③ 같은 그룹 안에서는 저등급(L→M→H) 우선(원문 불일치 위험이 큰 것부터 검증).
- 수용률(KPI 90%+) = **검토 완료분 중 승인 비율**. AI 품질 지표이지, 전수 검토를 강제하는 장치가 아니다.
- 용어: 화면·발표에서 "필요한 부분만 검토" 같은 주관적 표현 금지 → **"위험 기반 검토(risk-based review)"**로 통일.

### 5.6 후보 레이더 (candidate radar) — 잠정 신호의 유일한 두 용도 (08/20)

status와 무관하게(CANDIDATE 포함) 세는 **잠정 집계**. 루프의 순서를 "검토-우선"이 아니라 "신호-우선"으로 만드는 장치다: 시스템이 먼저 반복을 감지해 가설 DRAFT를 만들고, 사람은 그 가설이 딛고 선 claim만 표적 검토한다.

| 규칙 | 내용 |
|---|---|
| 허용 용도 ① | 검토 큐 정렬 — §5.5 ②의 "반복 수 상위"가 이 수치다 |
| 허용 용도 ② | 가설 DRAFT 자동 생성 트리거 (임계값·대상은 docs/01 §3) |
| 금지 | 공식 집계·순위·KPI·발표 수치에 사용 금지 (절대 규칙 #3). 잠정 수치와 공식 수치를 한 카드에 합산 표기 금지 |
| 화면 표기 | 공식 KPI와 **분리된 카드**에 "승인 전 잠정 수치 — 공식 집계 아님" 라벨 필수 병기. 통계적 패턴(SQL) 색상 + 잠정 배지 (절대 규칙 #8) |
| 조회 권한 | `MEDICAL_AFFAIRS` `CLINICAL_STRATEGY`만. `COMMERCIAL` 롤에는 어떤 형태로도 노출하지 않는다 (승인 전 데이터는 §9의 집계 조건을 충족하지 못함) |
| 수렴 | `candidateCount − approvedCount` = 검토 대기량. 검토가 진행되면 잠정 수치는 공식 수치로 수렴한다 — 홈에서 이 간극 자체를 "검토 대기열" 위젯으로 보여준다 |

## 6. Safety 분리 규칙 (절대 규칙 #6)

- 추출 중 `SAFETY_CANDIDATE` 판정 문장(이상사례·제품 불만 시사)은 claims가 아닌 `safety_candidates`로만 저장.
- Field 화면에는 "안전성 검토 경로로 전달됨" 배지만 표시, 일반 카드 목록에서 제외.
- 집계·가설·Screen 에이전트는 이 테이블을 읽지 않는다 (Safety Agent만 별도 조회).
- 판정 트리거 예: 부작용 경험 서술("복용 후 어지러움"), 중단 사유가 이상반응, 제품 품질 불만.
- **08/19 추가 필드**: `event_terms`(보고된 용어 — dizziness·간수치 등), `severity_note`(**원문에 언급된 심각성 표현 그대로** — "출퇴근에 지장" 등. 등급 판정·인과관계·MedDRA 코딩은 저장하지 않는다: PV 시스템 관할), `product_named`(제품명 실명 언급 여부 — False면 PV 인계 전 사람 확인 필수).

## 7. Schema Change Proposal 승격 조건 (기획서 5-3 §4)

자동 제안 조건: `unmapped_terms.occurrence_count ≥ 3` **그리고** 독립 HCP ≥ 2.
제안서에 자동 첨부: 원문 사례 3건 링크, 반복/출처 수, 기존 enum과의 비동의어 근거, 영향받는 화면·레코드 수.
Steward 승인 시: 새 `contract_versions` 레코드 ACTIVE화 → `GET /api/field/form-config`가 즉시 새 항목 반환.

### 7.5 버전 전환 안전 규칙 (v0.1 → v0.2에서 깨지면 안 되는 것)

| 위험 | 규칙 |
|---|---|
| 의미 단절 (비교 불가) | 변경은 **추가(additive)만** 허용: 새 enum 값·새 필드 추가만. 기존 값의 개명·삭제·의미 변경 금지 — 퇴역시킬 땐 `deprecated` 표시만 하고 보존 |
| 시계열 착시 (새 항목이 "급증"처럼 보임) | 새 항목의 집계·차트에는 **"v0.2(활성일)부터 수집" 주석을 화면에 필수 표시**. 버전 경계를 넘는 추이 비교 금지 |
| 과거 데이터 공백 | 원문이 불변이므로 필요 시 재추출로 소급 가능. 단, **덮어쓰지 않는 별도 레코드**로 생성하고 다시 CANDIDATE→승인 절차를 거침 (기획서 5-3 ④). MVP에선 P2 |
| 전환 시점 혼재 | 진행 중이던 CANDIDATE는 생성 당시 버전으로 계속 검토·승인 (`contract_version` 필드가 이미 보장) |
| 동의어 미연결 | SCP 승인 시 `unmapped_terms`에 쌓인 해당 표현들을 새 canonical의 synonym으로 일괄 등록 |
| 현장 혼란 | Field 폼의 신규 항목에 `NEW` 배지 + 유래 표시 (`origin: BOARD_FOLLOW_UP` 등 — API 스펙 §6에 반영됨) |

## 8. v0.2 예정 변경 (데모 시나리오 고정)

- `patient_segment`에 `POST_STROKE` 추가 (코퍼스에 6회/HCP 4인 등장하도록 설계됨)
- Board 승인 후속 질문 → Field 체크리스트 항목: "청소년 환자 사례 시 이전 실패 약물 수 확인"

## 9. 목적·권한 분리 매트릭스 (기획서 3-1 사용자 5부류 · 차별점 ②)

`purpose_domain`은 **조회 단계에서 강제되는 제약**이다. 화면에서 숨기는 방식(프론트 필터)은 금지 — 백엔드 `access.py` 게이트가 SQL 조건으로 강제하고, 권한 밖 조회는 예외를 던진다.

| 롤 | 조회 가능 purpose_domain | 세부 제약 |
|---|---|---|
| `MEDICAL_AFFAIRS` (면담 담당) | MEDICAL, PUBLIC_EVIDENCE | 자신이 수집한 interaction의 원문 + 승인 데이터. AE는 "분기됨" 사실만 보이고 내용은 못 봄 |
| `CLINICAL_STRATEGY` (임상·Medical 전략) | MEDICAL, PUBLIC_EVIDENCE | 가설 승인·보류·기각 권한 보유. Development Hypothesis 검토 대상 |
| `SAFETY` (PV 담당) | SAFETY | `safety_candidates`의 유일한 조회자. 성장 가설 화면 접근 불필요 |
| `COMMERCIAL` (상업 전략) | COMMERCIAL | **원문(raw_text)·verbatim_quote 접근 불가.** 지역·기관 단위 집계 행만 (`distinct_hcp ≥ 3`인 그룹만 반환 — 개인 역추정 차단). Development 가설 목록 접근 불가 |
| `DATA_STEWARD` (거버넌스) | 전 영역의 **스키마·SCP·버전** | 값 자체가 아니라 구조를 다룸. SCP의 원문 사례는 열람 가능(승인 판단에 필요) |

- 절대 규칙 #7의 코드화: `COMMERCIAL` 롤에는 개별 HCP 식별자(`hcp_ref`)를 어떤 응답에서도 내보내지 않는다.
- MVP 구현: 로그인 없이 헤더 `X-Delphi-Role`로 롤을 주입(docs/04 §0). 시연은 `CLINICAL_STRATEGY`가 기본, 권한 분리 장면에서만 `COMMERCIAL`로 전환.
- 위반 시 동작: `403` + `error.code = PURPOSE_SCOPE_VIOLATION`. **빈 배열 반환 금지** — 조용한 누락은 데이터가 없는 것과 구분되지 않는다.

## 10. 외부 근거의 해석 한계 문구 (기획서 5-3 ⑤)

외부 출처에서 온 `screen_findings`에는 `caveat_ko`를 반드시 채우고, 화면에서 근거 문장과 **같은 카드 안에** 표시한다. 문구는 아래로 고정(임의 변형 금지).

| 출처 | caveat_ko |
|---|---|
| openFDA FAERS | "자발적 이상사례 보고 데이터로, 발생률·인과관계 판단에 사용할 수 없는 탐색 신호입니다." |
| ClinicalTrials.gov | "임상시험 등록 사실이며, 효과가 입증되었음을 의미하지 않습니다." |
| PubMed | "초록 기준 요약입니다. 연구 설계·표본 규모는 원문에서 확인해야 합니다." |
| Drugs@FDA / 제품 라벨 | "표기 시점의 허가사항이며, 최신 개정 여부는 원문 라벨에서 확인해야 합니다." |
