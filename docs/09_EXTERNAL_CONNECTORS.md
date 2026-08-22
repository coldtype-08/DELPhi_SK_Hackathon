# 09. 외부 공개 데이터 커넥터 4종 — 질의 명세

> 08/22 신설 [작성: 소정]. WBS 4.1 · 킥오프 액션아이템(8/26)의 선행 문서.
> **이 문서의 모든 필드명·응답 예시는 2026-08-22에 실제 호출해서 확인한 값이다.** 추측으로 적은 항목은 없다.
> 원칙: 외부 데이터는 **공개 출처만 · 개인 식별 0건 · 예측선 없음**. 수치 계산은 전부 SQL(절대 규칙 #1).
> 저장 위치: `external_refs` 테이블 (docs/02 §4) — 가설에 연결되지 않으므로 COMMERCIAL 롤에도 열린다.

## 0. 왜 이 문서가 먼저인가

`draft.html` 시장·경쟁 탭이 **"경쟁 약물의 허가 연령은 추정하지 않았습니다"** 라고 선언하고 각 행을 `스냅샷 대기`로 비워 두었다.
그 빈칸을 채우는 것이 이 커넥터다. **틀린 값 하나가 시장 판단을 오염시키므로, 무엇을 어디서 어떤 필드로 가져오는지를 코드보다 먼저 고정한다.**

## 1. 실측 검증 결과 (2026-08-22)

4종 전부 **인증 없이** 응답을 받았다. 아래는 실제 호출 결과다.

| # | API | 엔드포인트 | 상태 | 인증 |
|---|---|---|---|---|
| 1 | **openFDA 제품 라벨** | `api.fda.gov/drug/label.json` | ✅ 200 | 불필요 (키 있으면 rate↑) |
| 2 | **ClinicalTrials.gov v2** | `clinicaltrials.gov/api/v2/studies` | ✅ 200 | 불필요 |
| 3 | **PubMed E-utilities** | `eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi` | ✅ 200 | 불필요 (키 있으면 3→10 req/s) |
| 4 | **Drugs@FDA** | `api.fda.gov/drug/drugsfda.json` | ✅ 200 | 불필요 |

### 1.1 이번 호출에서 확인된 사실 (데모 서사에 직결)

| 발견 | 출처 | 왜 중요한가 |
|---|---|---|
| XCOPRI 라벨 `pediatric_use` = **"Safety and effectiveness in pediatric patients have not been established"** · 라벨 개정일 **2025-09-25** | openFDA label · NDA212839 | **12–17세 공백이 라벨 원문으로 확정된다.** 화면의 "우리 라벨 연령 하한 18세+"의 1차 근거 |
| **NCT03961568** — SK Life Science, 연령 **12세~**, 2019-08-13 시작, COMPLETED | CT.gov | 회사가 이미 청소년 방향으로 움직인 **공개 증거**. HYP-001 "검증 축"(정답을 아는 문제)의 실물 근거 |
| **NCT07594158** — Ono Pharmaceutical, 연령 **2~17세**, 2026-05-30 시작, RECRUITING | CT.gov | 경쟁사가 소아 구간을 파고 있다 → 우리 공백이 "미개척"인지 "뒤처짐"인지 판정하는 데이터 |
| cenobamate + adolescent[MeSH] **55건** · 2024년 cenobamate 전체 **68건** | PubMed | 추이 탭 오버레이의 실제 모수 |
| NDA212839 제출 이력 8건 (최신 SUPPL 13 승인 **2025-08-18**) | Drugs@FDA | 라벨 개정 시점 추적 — caveat "표기 시점의 허가사항"의 근거 |

> **주의**: 위 값들은 공개 데이터이며 사내 정보가 아니다. 사내 면담 데이터는 전량 합성(docs/03)이고, 이 둘은 화면에서 출처 배지로 구분한다.

## 2. 커넥터별 질의 명세

### 2.1 openFDA 제품 라벨 → `ref_type: LABEL_AGE`

```
GET https://api.fda.gov/drug/label.json
  ?search=openfda.generic_name:"<약물>"
  &limit=1
```

| 쓰는 필드 | 예시값 | 화면 반영 |
|---|---|---|
| `openfda.brand_name` | `["Xcopri", "Xcopri Titration Pack"]` | 행 라벨 |
| `openfda.generic_name` | `["CENOBAMATE"]` | 조인 키 |
| `openfda.application_number` | `["NDA212839"]` | Drugs@FDA 조인 키 |
| `effective_time` | `20250925` | **`source_as_of`** (라벨 개정일) |
| `pediatric_use` | `"8.4 Pediatric Use Safety and effectiveness in pediatric patients have not been established…"` | 허가 연령 지도 · **원문 보존** |
| `indications_and_usage` | (장문) | 원문 보존 — 요약하지 않는다 |

- **연령 파싱 규칙**: `pediatric_use` 원문을 저장하고, 연령 숫자는 **정규식으로 뽑되 원문을 함께 보관**한다. 파싱 실패 시 화면은 `판정 불가`로 두고 **추정하지 않는다.**
- caveat: `"표기 시점의 허가사항이며, 최신 개정 여부는 원문 라벨에서 확인해야 합니다."`

### 2.2 ClinicalTrials.gov v2 → `ref_type: TRIAL_REG`

```
GET https://clinicaltrials.gov/api/v2/studies
  ?query.intr=<약물>
  &fields=NCTId,BriefTitle,OverallStatus,StartDate,MinimumAge,MaximumAge,LeadSponsorName
  &countTotal=true&pageSize=50
```

| 쓰는 필드 (응답 경로) | 예시값 |
|---|---|
| `protocolSection.identificationModule.nctId` | `NCT03961568` |
| `protocolSection.statusModule.overallStatus` | `COMPLETED` |
| `protocolSection.statusModule.startDateStruct.date` | `2019-08-13` |
| `protocolSection.eligibilityModule.minimumAge` / `maximumAge` | `12 Years` / `null` |
| `protocolSection.sponsorCollaboratorsModule.leadSponsor.name` | `SK Life Science, Inc.` |

- `maximumAge`가 `null`인 경우가 정상이다(상한 없음) — 빈 값을 0으로 바꾸지 않는다.
- caveat: `"임상시험 등록 사실이며, 효과가 입증되었음을 의미하지 않습니다."`

### 2.3 PubMed E-utilities → `ref_type: LIT_COUNT`

```
GET .../esearch.fcgi?db=pubmed&term=<약물>&mindate=<YYYY>&maxdate=<YYYY>
    &datetype=pdat&retmode=json&retmax=0     # 연도별 건수
GET .../esearch.fcgi?db=pubmed&term=<약물>+AND+adolescent[MeSH]&retmode=json   # 주제 필터
```

- 쓰는 필드: `esearchresult.count`(문자열 → int 캐스팅), `esearchresult.idlist`
- **연도별 집계는 API가 아니라 연도마다 1회 호출**해서 count를 받아 저장하고, **추이 계산은 SQL**로 한다(절대 규칙 #1).
- rate limit: 키 없이 **3 req/s**. 약물 5종 × 6년 = 30회이므로 **호출 간 350ms 슬립**을 넣는다.
- caveat: `"초록 기준 요약입니다. 연구 설계·표본 규모는 원문에서 확인해야 합니다."`

### 2.4 Drugs@FDA → `ref_type: LABEL_AGE` (승인 이력 보강)

```
GET https://api.fda.gov/drug/drugsfda.json?search=openfda.generic_name:"<약물>"&limit=1
```

- 쓰는 필드: `application_number`, `sponsor_name`, `submissions[].{submission_type, submission_number, submission_status, submission_status_date}`
- 용도: **라벨이 언제 개정됐는지**를 승인 이력으로 교차 확인 → `source_as_of` 신뢰도 보강
- caveat: 2.1과 동일

## 3. 캐시 — 심사 중 외부 API가 죽어도 화면은 선다

`DEMO_OFFLINE=1`이면 외부 호출 0회, 캐시만 읽는다 (docs/00 §5.2, docs/07).

- 위치: `backend/data/cache/` (`.gitignore` 확인 필요 — **스냅샷 fixtures는 커밋**, 원시 캐시는 제외)
- 파일명: `{source}_{query-slug}_{YYYYMMDD}.json` — 소스·질의·스냅샷 일시가 파일명에 들어간다 (docs/03 §7)
- 모든 커넥터는 `cache.py`를 경유한다. **커넥터가 직접 `requests`를 부르지 않는다.**
- `GET /api/health`의 `cacheSnapshotAsOf`가 채워지는 것이 이 작업의 완료 신호 (현재 `null`)

## 4. 하지 않는 것 (경계)

| 금지 | 이유 |
|---|---|
| 개인 단위 지불·처방 결합 | 절대 규칙 #7. 집계 축은 **제조사**이지 개인이 아니다 |
| 예측선·추세 외삽 | 공개 데이터로 미래를 그리면 근거가 아니라 주장이 된다 |
| FAERS 발생률 비교 | 자발적 보고는 분모가 없다. 약물 간 "어느 쪽이 더 위험한가" 판단 불가 |
| 라벨 연령 추정 | 파싱 실패 시 `판정 불가`. 빈칸이 틀린 값보다 낫다 |
| 외부 값으로 KPI 계산 | KPI는 승인된 사내 데이터만(절대 규칙 #3). 외부는 `external_refs`에만 |

## 5. 미결 — 확정 후 이 표를 지운다

| 항목 | 선택지 | 결정 |
|---|---|---|
| **추적 대상 경쟁 약물** | `draft.html`은 brivaracetam · lacosamide · perampanel · cannabidiol · fenfluramine 5종. **levetiracetam(Keppra)이 빠져 있다** — 1차 치료제이자 최대 전환 풀인데 제외가 의도인지 | ⟨소정·건태⟩ |
| **FAERS(`drug/event`) 포함 여부** | docs/02 §10에 caveat이 이미 정의돼 있으나, 4종 명단에는 라벨/승인이 들어와 있다. 안전성 신호를 시장 탭에 넣을지 | ⟨소정·PV 관점⟩ |
| **문헌 추이 연도 범위** | 2021~2026(코퍼스와 동일) vs 2019~2026(XCOPRI 승인 이후 전 구간) | ⟨소정⟩ |
| **커넥터 구현 오너** | WBS 4.1은 인혁(8/26), 킥오프 액션아이템은 소정(8/26). **중복 배정** | ⟨아침 싱크⟩ |

## 6. 구현 순서 (제안)

1. `backend/app/connectors/cache.py` — 캐시 계층 먼저. 이후 전부 여기를 경유
2. `openfda_label.py` → `ctgov.py` → `pubmed.py` → `drugsfda.py`
3. `external_refs` 적재 스크립트 + 스냅샷 fixtures 커밋
4. `GET /api/market/refs` (docs/04에 추가) → `/market` 화면 연결

> `backend/`는 인혁 오너십이므로 구현 커밋은 **`[cross]` 태그 + 아침 싱크 공유**로 진행한다 (CLAUDE.md).
