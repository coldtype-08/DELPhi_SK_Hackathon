# 01. 시스템 아키텍처

> 원칙: 2주 안에 비개발자 3인이 Claude Code로 완성할 수 있는 **가장 단순한 구조**.
> Graph DB, 메시지 큐, 마이크로서비스 없음. FastAPI 하나 + SQLite 하나 + Next.js 둘.

## 1. 전체 구성

```
┌─────────────────┐         ┌─────────────────┐
│  apps/field      │         │  apps/console    │
│  모바일 웹 (3001) │         │  대시보드 (3000)  │
│  현장 수집·승인   │         │  검토·가설·심의    │
└────────┬────────┘         └────────┬────────┘
         │      REST (JSON)          │
         └──────────┬────────────────┘
                    ▼
        ┌───────────────────────┐        ┌──────────────────┐
        │  backend (FastAPI)     │──────▶│  Claude API       │
        │  :8000                 │        │  (structured out) │
        │  sense/screen/board    │        └──────────────────┘
        │  contract/connectors   │        ┌──────────────────┐
        └──────────┬────────────┘──────▶│  PubMed·CT.gov·   │
                   ▼                     │  openFDA·Drugs@FDA│
                                         │  (+캐시)           │
        ┌───────────────────────┐        └──────────────────┘
        │  SQLite (delphi.db)    │
        │  + corpus/ + cache/    │
        └───────────────────────┘
```

## 2. 데이터 3계층 (기획서 4-3 그대로)

| 계층 | 테이블/저장소 | 내용 |
|---|---|---|
| **Source Layer** | `documents`, `interactions`, `backend/data/corpus/*.txt` | 원본 문서·면담 원문. 절대 수정하지 않는다 |
| **Evidence & Structured** | `claims`, `evidence_pointers`, `vocab_terms`, `safety_candidates` | AI 추출 후보 + 원문 위치 + 검토 상태 |
| **Analytics & Decision** | `signal_aggregates`(SQL 뷰), `hypotheses`, `screen_findings`, `board_minutes`, `decisions` | 승인 데이터 기반 집계와 가설·심의·결정 |

**목적 영역 분리 (기획서 4-3·차별점 ②) — 문서상의 원칙이 아니라 조회 단계의 제약**: 모든 Evidence & Structured 레코드는 `purpose_domain`(`MEDICAL`·`COMMERCIAL`·`SAFETY`·`PUBLIC_EVIDENCE`)을 갖고, 데이터 접근은 라우터가 아니라 **단일 조회 게이트(`backend/app/access.py`)**를 통과해야 한다. 롤별 허용 범위는 docs/02 §9의 매트릭스가 유일한 정의이며, 위반 쿼리는 코드에서 예외를 던진다(빈 결과 반환 금지 — 조용한 누락이 더 위험하다). *기획서가 "일반 요약 도구와 구분되는 기술적 근거"로 명시한 지점이므로 시연에서 쿼리 레벨로 보여준다.*

**이관 대비 규칙 (기획서 4-3 반영)**: 데이터 계층은 **ANSI SQL 범위**로만 구현한다 — SQLite 전용 함수(`strftime` 등), 동적 타입 의존, 벤더 확장 문법 금지. 날짜는 ISO 8601 문자열 + 명시적 캐스팅, 집계는 표준 `GROUP BY`/윈도우 함수로 작성. 이유: 파일럿 단계에서 같은 스키마·같은 질의를 사내 데이터 플랫폼(Snowflake 등)으로 그대로 옮기기 위함. 새 쿼리를 짤 때 "이 문법이 Snowflake에도 있나"를 확인한다.

## 3. 핵심 상태 머신

### 루프는 두 개다 (08/21 — 프레이밍 정정)

"폐쇄 루프"라고 할 때 닫히는 경로가 두 개이고, 무게가 다르다. 초기 문서는 구조 루프에 기울어 있었는데, **매일 도는 것은 실행 루프다** — 스키마 변경은 드물게 일어나는 게 정상이고(자주 돌면 오히려 거버넌스 실패), 레이턴시 단축 주장(docs/00 §1)의 본체도 실행 루프다.

| | **실행 루프 (상시)** | **구조 루프 (드묾)** |
|---|---|---|
| 닫히는 경로 | Board 권고 → 사람 승인 → **Action Item** → Field 브리핑·체크리스트 → 표적 수집 → 집계 재유입 | 반복되는 스키마 밖 개념 → SCP → Steward 승인 → v0.2 → form-config 변경 |
| 빈도 | 매 심의마다 | 코퍼스 전체에서 1건(POST_STROKE)이 되도록 설계 |
| 스키마 변경 | 없음 — Contract 버전 그대로 | 있음 (추가만, §7.5) |
| 데모 | ⑤에서 닫힘 | ⑥에서 닫힘 |
| 닫힘의 증거 | 액션별 **참조 수집 카운트**(SQL) +1 | Field 폼에 새 옵션 등장 |

### Action Item (Board 후속 — 실행 루프의 단위)
```
PROPOSED (Board·CEO가 회의록에서 제안 — board_minutes.action_item_json)
    └─ 사람이 결정에 채택 ──▶ ACTIVE ── /field/briefing 응답에 포함 ──▶ delivered_at 기록
ACTIVE ──이 액션을 참조한 수집(interactions.checklist_refs)의 claim이 APPROVED──▶ COLLECTED
ACTIVE ──가설 HOLD·REJECTED 또는 수동 종료──▶ CLOSED
```
- **Board·CEO는 제안까지만이다.** 액션이 ACTIVE가 되는 유일한 경로는 사람의 decision에 채택되는 것 (기획서 리스크 표: "Board·CEO Agent에 승인 권한 없음").
- `target`은 `FIELD_CHECKLIST` `SPECIALIST_REVIEW` `MEDINFO_RESPONSE` 셋뿐 — **상업 실행 계열 값이 enum에 없다.** Development 가설의 액션이 상업 액션으로 연결될 수 없음을 타입 수준에서 강제한다(절대 규칙 #5의 코드화).
- 전이는 전부 결정론적(API 호출·SQL 조건)이고, "참조 수집 카운트"는 APPROVED claim만 센다(절대 규칙 #3).

### Claim (추출값)
```
CANDIDATE ──승인──▶ APPROVED ──┐
    │                          ├─▶ 집계·분석에 포함 (APPROVED만!)
    ├─수정 후 승인─▶ APPROVED ──┘
    └─반려──▶ REJECTED (보존, 집계 제외)
```
- 검토등급(H/M/L)은 상태가 아니라 **참고 라벨**: `원문일치 + 용어매핑성공 + 규칙통과` 조합으로 결정론적 계산.
- H등급도 자동 승인 없음. 사람이 누른다.
- 기획서 4-3의 `Candidate → Reviewed → Approved` 3단계와의 관계: **`REVIEWED`를 별도 상태로 두지 않는다.** 검토 행위는 `reviewed_by`/`reviewed_at`으로 기록되고, 검토 결과가 `APPROVED`·`REJECTED` 전이 그 자체다(= 검토됨 ⟺ 두 필드가 채워짐). 상태를 하나 줄이는 대신 "검토했지만 판단 보류" 케이스는 `CANDIDATE` + 검토 큐 후순위로 처리한다. 기획서 문장을 바꾼 것이 아니라 같은 절차를 2전이로 구현한 것이며, 발표에서도 이 대응관계로 설명한다.

### Hypothesis (성장 가설)
```
DRAFT(Sense 생성) → SCREENING(에이전트 조사 중) → BOARD_READY → IN_REVIEW(사람)
                          └─ 근거 부족 → NOT_BOARD_READY (순위 없음, 사유 표시)
IN_REVIEW → APPROVED / HOLD / REJECTED   (+ In-label vs Development 라벨 필수)
```

**DRAFT 생성은 사람이 아니라 임계값이 한다 (08/20 — "신호-우선" 재배열).** 사람이 전수 검토를 마쳐야 가설이 나오는 것이 아니다. `sense/aggregate.py`가 추출 완료 시·claim 상태 변경 시마다 **잠정 신호(CANDIDATE 포함 — docs/02 §5.6 후보 레이더)**를 재계산하고, 아래 조건을 모두 만족하는 (patient_segment × signal_type) 조합에 열린 가설이 없으면 DRAFT를 자동 생성한다. 멱등: 같은 조합의 가설이 이미 있으면 새로 만들지 않고 잠정 수치만 갱신한다.

| 생성 조건 | 기본값 (`backend/app/config.py` 상수 — 결정론, LLM 관여 없음) |
|---|---|
| 대상 signal_type | `UNMET_NEED` `TREATMENT_BARRIER` — 성장 가설 후보군. `INFO_REQUEST`는 Field 체크리스트로, `SAFETY_CANDIDATE`는 docs/02 §6 분리 경로로, `POSITIVE_OUTCOME` 등은 대시보드 표시만 |
| 잠정 반복 수 | ≥ 5 |
| 잠정 독립 HCP | ≥ 3 |
| 대상 patient_segment | **`UNSPECIFIED` 제외** (08/21 명시) — 환자군이 특정되지 않은 신호는 가설의 주체가 될 수 없다. 스키마 밖 표현(post-stroke 등)은 `UNSPECIFIED`로 떨어지고 `unmapped_terms` 반복이 **SCP 경로**를 탄다. 이 규칙이 없으면 코퍼스의 S3 19건이 "미지정 환자군 가설"을 만든다 |

- 생성 직후 참조 claim 중 APPROVED가 0건이면 그대로 `NOT_BOARD_READY(NO_APPROVED_BASIS)` 사유를 달고 가설 보드에 노출된다 — **승인은 가설의 탄생 조건이 아니라 Board행의 관문이다.** 생성과 동시에 그 가설이 참조하는 claim들이 검토 큐 최상단으로 올라간다(docs/02 §5.5 ①).
- 잠정 수치의 용도는 DRAFT 생성 트리거와 검토 큐 정렬, 딱 두 가지다. **공식 집계·순위·KPI는 여전히 APPROVED만 계산한다(절대 규칙 #3 불변).** 가설 카드의 `statisticalPatterns`도 항상 승인 기준 SQL 재계산 값을 쓰고, 생성 당시의 잠정 스냅샷은 `created_from_aggregate_json`에 참고용으로만 보존한다.
- 검산 (08/21 코퍼스 v3 실측 — 문서 320건·단위 1,118): 이 기본값이면 정확히 **넷만** 생성된다 — HYP-001(S1 청소년: **52건/34인**, 검증 축)·HYP-002(S6 노인: **41건/27인**, In-label 대비)·HYP-003(S7 PGTC: **34건/23인**, 완주 대표)·HYP-004(S8 LGS: **21건/15인**, 두 번째 발굴). S4(INFO_REQUEST 47건)·S5(POSITIVE_OUTCOME 38건)는 대상 signal_type이 아니고, S3(post-stroke 19건)는 `UNSPECIFIED`라 위 규칙으로 제외되어 SCP 경로를 탄다. **`scripts/generate_corpus.py --dry-run`이 이 4개 집합을 문자 그대로 검증**하므로 각본을 잘못 고치면 코퍼스 생성 자체가 실패한다 (docs/03 §2).

**NOT_BOARD_READY 판정도 결정론적이다** (기획서 4-2 ③ "근거가 충분하지 않으면 순위를 부여하지 않는다"). 아래 중 하나라도 걸리면 Board로 넘기지 않고 사유 코드를 화면에 표시한다.

| 사유 코드 | 조건 |
|---|---|
| `NO_APPROVED_BASIS` | 참조 claim 중 APPROVED가 0건 |
| `SINGLE_SOURCE` | 독립 HCP < 2 또는 단일 권역 |
| `NO_EXTERNAL_EVIDENCE` | Evidence Agent의 SUPPORT·COUNTER 결과가 둘 다 0건 (조회 실패 포함) |
| `CRITIC_BLOCKED` | 재시도 2회 후에도 Critic 차단 잔존 |

- 순위(정렬)는 반복 수·독립 출처 수·권역 수의 **SQL 계산값**으로만 매긴다. LLM이 점수를 부여하지 않는다.

### Data Contract
```
v0.1 ACTIVE ──[SCP 등록: 반복 개념 + 원문 사례 + 영향 분석]──▶ Steward 승인 ──▶ v0.2 ACTIVE, v0.1 RETIRED
```
- 과거 claim은 생성 당시 contract_version을 유지. 재추출은 덮어쓰지 않고 새 레코드.

## 4. 백엔드 모듈 구조

```
backend/app/
├── main.py            # FastAPI 앱, 라우터 등록, CORS(3000·3001 허용)
├── models.py          # SQLAlchemy 테이블 전부 (docs/02 §4 그대로)
├── access.py          # 목적·권한 조회 게이트 (docs/02 §9) — 모든 claim/집계 조회가 경유
├── llm.py             # Claude 호출 단일 래퍼: 모델·프롬프트버전·스키마·parser버전·소요시간 로깅
├── prompts/           # *.md 프롬프트 (버전 헤더 필수) [오너: 소정]
├── contract/          # contract 로드·검증·버전·SCP 로직
├── sense/             # extract.py(구조화) · normalize.py(용어) · grade.py(H/M/L) · aggregate.py(SQL 집계·가설 후보)
├── screen/            # orchestrator.py + agents/{field_signal, evidence, safety, critic}.py
├── board/             # deliberate.py (Board 다중 관점 + CEO 종합)
├── connectors/        # pubmed.py · ctgov.py · openfda.py — 전부 cache.py 경유
└── routers/           # documents · claims · aggregates · hypotheses · contract · field
```

### 에이전트 실행 규칙 (기획서 반영)
- 오케스트레이션은 **결정론적 순서**: FieldSignal → Evidence → Safety → Critic. LLM이 순서를 정하지 않는다.
- 에이전트 간 메시지는 자유 대화가 아니라 **타입 있는 구조체**: `{type: SUPPORT|COUNTER|GAP|SAFETY_SIGNAL, statement, source_url, source_locator}`.
- Critic이 차단하면 해당 항목은 `blocked_log`에 남고 재추출 경로로. **재시도 한도 2회**, 초과 시 NOT_BOARD_READY.
- 수치가 필요한 곳(반복 수 등)은 에이전트가 SQL 결과를 **읽기만** 한다. 계산 금지.

## 5. 프론트 화면 맵

### Console (페이퍼 라이트, 데스크톱 우선) — 건태
| 라우트 | 화면 | 핵심 컴포넌트 |
|---|---|---|
| `/` | 홈 대시보드 | KPI 스트립(승인 데이터 수·신호 수·가설 수), 신호 추이 차트, **후보 레이더 카드(잠정 라벨 필수 — 임계 도달 시 가설 링크, docs/02 §5.6)**, 검토 대기열 위젯, 최근 활동 |
| `/review` | Data Review | **첫 화면은 검토 큐(위험 기반 정렬 + `queueReasonKo` 표시)** — 문서 리스트·원문 하이라이트 양분할은 큐에서 진입하는 상세. 승인/수정/반려 |
| `/hypotheses` | 가설 보드 | 가설 카드 그리드 (상태별), Not Board-ready 별도 표시 |
| `/hypotheses/[id]` | 가설 상세 | **5단계 구분 카드**, 지지/반대/공백 근거 리스트(원문·출처 링크), 에이전트 활동 시각화, Board 회의록, 승인·보류·기각 — **승인 시 Board 제안 중 채택할 Action Item을 확정(편집 가능)**, 이후 액션별 상태·참조 수집 카운트 표시 |
| `/contract` | Data Contract | 현재 버전 스키마 뷰, SCP 목록·승인, 버전 diff |
| `/contract/provenance` | Contract 유래 | 부트스트랩 판정 기록의 결정론적 렌더링(LLM 없음): 반복 매트릭스 → 원문 인용·판정 → 스키마·DB 반영 → 한 문장 추적. 데이터 원천: DECISIONS 08/19 + `docs/assets/bootstrap-ai-draft.md` (동기화 대상: `apps/console/lib/provenance.ts`) |
| `/market` | 시장·경쟁 | 공개 출처만 쓰는 경쟁 환경 화면: 허가 연령 지도(openFDA 라벨), 경쟁사 청소년 시험 타임라인(CT.gov), 문헌 추이(PubMed), 모수(HIRA·CMS Part D 집계). **개인 식별 0건 · 예측선 금지 · FAERS 발생률 비교 금지** (DECISIONS 08/20). `PUBLIC_EVIDENCE` 도메인이라 COMMERCIAL 롤에도 열린다 |
| `/safety` | 안전성·차단 로그 | 분기된 AE 후보, Critic 차단 이력 |

### Field (페이퍼 라이트, 모바일 우선 390px) — 소정
| 라우트 | 화면 | 핵심 컴포넌트 |
|---|---|---|
| `/` | 오늘의 면담 | 방문 예정·미해결 질문 체크리스트(Board에서 내려온 것 포함) |
| `/capture` | 면담 기록 | 동의 확인 → 녹음/텍스트 입력 → 실시간 전사 → AE 자동 분기 배지 |
| `/capture/review` | 구조화 승인 | AI가 만든 카드(환자군·신호·근거 인용) 스와이프/탭 승인·수정·제외 |
| `/history` | 내 기록 | 승인 완료 interaction 목록 |

- Field의 입력 항목은 하드코딩 금지 — 반드시 `GET /api/field/form-config`(활성 contract 버전) 기반 렌더. **v0.2 전환 데모가 여기서 터진다.**

## 6. 환경 변수 (.env)

```
ANTHROPIC_API_KEY=...
DELPHI_MODEL_EXTRACT=claude-sonnet-5
DELPHI_MODEL_BOARD=claude-opus-5
DEMO_OFFLINE=0          # 1이면 외부 API 캐시만 사용 (시연 모드)
DATABASE_URL=sqlite:///./data/delphi.db
```

## 7. 추적성 (기획서 5-1 품질 목표)

기획서가 요구하는 기록 항목은 **모델 · prompt · schema · parser · 외부 데이터 기준 시점** 다섯 가지다. 하나라도 빠지면 "결과의 생성 조건 추적" 주장이 성립하지 않는다.

`llm_runs` 테이블에 모든 호출 기록: `purpose, model, prompt_file, prompt_version, schema_name, parser_version, external_data_as_of, input_hash, output_hash, latency_ms, created_at`.
- `parser_version`: 구조화 출력 파싱·정규화 로직의 버전 문자열(`sense.extract@3` 형식). 파서를 고치면 반드시 올린다.
- `external_data_as_of`: 그 호출이 참조한 캐시 스냅샷 일시. 외부 근거를 안 쓰는 호출은 null.
- 외부 데이터는 `cache/` 파일명에 소스·쿼리·스냅샷 일시 포함(docs/03 §7), 화면의 근거 카드에도 스냅샷 일자를 표기.
- 화면의 AI 산출물에는 "생성 조건 보기" 링크(P1) → `GET /llm-runs/{id}`.

## 8. 모델 계층 교체 가능성 (기획서 4-3)

기획서에는 "프로토타입에서는 OpenAI 및 Claude API를 사용할 예정"이라고 썼다. **MVP 구현은 Claude 단일**(추출·분류 `claude-sonnet-5`, 심의 `claude-opus-5`)로 간다 — 2주 안에 두 벤더의 structured output 차이를 관리할 여유가 없고, 재현성 비교 대상이 늘어난다.

기획서와 모순이 아닌 이유이자 발표 답변: **모델 호출은 `llm.py` 한 곳만 경유하므로 벤더 교체는 이 파일의 구현체 변경**이다. 파일럿 단계의 사내 승인 LLM 환경 전환도 같은 지점에서 끝난다. 프롬프트는 `prompts/*.md`로, 스키마는 Contract에서 생성되므로 업무 로직은 그대로 남는다.

## 9. 검색 확장 순서 (기획서 4-3)

정확 일치 검색 + 구조화 항목 필터로 시작한다. **의미 기반(임베딩) 검색은 핵심 루프가 안정적으로 작동하고 원문 추적성이 유지되는 것을 확인한 뒤**에만 붙인다(P2, 기본값 안 함). 이 순서를 지키는 이유는 성능이 아니라 추적성이다 — 유사도로 찾은 근거는 원문 위치를 보장하지 않는다.
