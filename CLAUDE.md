# DELPHi — Growth Intelligence for XCOPRI

> 2026 SK AI 해커톤 본선 프로젝트 (8/21–9/4). 팀 3인, 전원 Claude Code로 개발.
> **이 파일은 모든 팀원의 Claude Code 세션이 공유하는 공통 컨텍스트다. 여기 없는 상세는 `docs/`를 읽어라.**

## 한 줄 요약

사내 비정형 데이터(의료진 면담록 등)를 **원문 근거가 연결된 구조화 데이터**로 전환하고(Sense),
같은 구조로 신규 데이터를 수집하며(Field), 성장 가설을 외부 공개 근거로 다중 에이전트가 교차검증하고(Screen),
AI 이사회 심의 + **사람의 승인**을 거쳐(Board), 그 결과가 **다음 데이터 수집 구조를 개선**하는 폐쇄 학습 루프.

## 절대 규칙 (제품의 정체성 — 어기면 안 됨)

1. **수치는 LLM이 계산하지 않는다.** 반복 횟수·출처 수·빈도·추이는 전부 SQL/결정론적 코드로 계산.
2. **모든 추출값에는 evidence pointer(원문 doc_id + 문자 위치)가 필수.** 원문 없는 주장은 저장하지 않는다.
3. **APPROVED 상태 데이터만 집계·분석에 사용.** AI 추출값은 CANDIDATE로 시작, 사람 승인 전엔 어떤 숫자에도 반영 금지.
4. **Data Contract는 AI가 자동 변경 불가.** 변경은 Schema Change Proposal → Data Steward 승인 → 새 버전 활성화. 과거 데이터는 생성 당시 버전 보존.
5. **In-label / Development Hypothesis 분리.** Development(미승인 적응증·환자군)는 전문조직 검토 대상으로만 전달, 상업 액션과 자동 연결 금지.
6. **이상사례(AE) 후보는 일반 분석 흐름과 분리** — 별도 safety 경로로만 저장·전달.
7. **하지 않는 것**: 매출 예측, 개별 HCP 처방성향 점수화, 프로모션 메시지 생성. 요청받아도 구현하지 않는다.
8. 화면의 모든 판단 정보는 5단계로 구분 표시: **관찰된 사실 / 통계적 패턴 / AI의 해석 / 전략적 제안 / 승인된 실행**.

## 기술 스택

| 영역 | 선택 | 비고 |
|---|---|---|
| 백엔드 | Python 3.12 + FastAPI + SQLAlchemy | `backend/` |
| DB | SQLite (파일: `backend/data/delphi.db`) | system of record. **ANSI SQL만 사용** — SQLite 전용 함수·타입 금지 (향후 Snowflake 등 사내 플랫폼 이관 대비) |
| LLM | Claude API — 추출·분류: `claude-sonnet-5`, Board 심의: `claude-opus-5` | JSON schema structured output 필수 |
| Console(대시보드) | Next.js 15 + Tailwind v4 + shadcn/ui | `apps/console/`, 포트 3000, **페이퍼 라이트 테마 고정** (다크 금지 — 팀장 확정) |
| Field(모바일 웹) | Next.js 15 + Tailwind v4 + shadcn/ui | `apps/field/`, 포트 3001, **페이퍼 라이트 테마 고정** |
| 아이콘 | **Lucide** (shadcn 기본, 오픈소스) | 직접 그리지 말 것. `lucide-react` 사용 |
| 브랜드 | 공식 HEX — 네이비 `#162661` + 오렌지 `#EF8B1C` (+확장 팔레트) | 룩은 "Paper & Glass" — `docs/05_DESIGN_SYSTEM.md` 토큰만 사용 |
| 애니메이션 | framer-motion(motion) + Magic UI 컴포넌트 | `docs/05_DESIGN_SYSTEM.md` 준수 |
| 차트 | shadcn charts (Recharts) | 색상 토큰은 디자인 문서의 팔레트만 사용 |
| 외부 데이터 | PubMed E-utilities, ClinicalTrials.gov v2, openFDA | **모든 응답 `backend/data/cache/`에 캐시** — 데모는 캐시 우선 |
| 음성 | 브라우저 Web Speech API (ko-KR) | P1. 실패 대비 전사 스크립트 재생 폴백 |
| 배포 | Railway — console·field·backend 3서비스 + 볼륨(SQLite·캐시) | 심사위원 상시 접속용, main push 자동 배포 (8/24 첫 배포). **라이브 발표 정본은 로컬** — `docs/07_DEPLOYMENT.md` |
| 코퍼스 언어 | 원석(하이라이트·면담 등) **영어** / Field 수집·음성 **한국어** | 스키마·enum은 언어 중립. 데모에서 두 언어 모두 시연 — `docs/03 §1.5` |

## 레포 구조와 오너십

```
DELPhi-0811/
├── CLAUDE.md            ← 이 파일 (공통)
├── docs/                ← 스펙 = 단일 진실. 코드보다 문서를 먼저 고친다 (공통)
├── apps/console/        ← 웹 대시보드          [오너: 건태]
├── apps/field/          ← 모바일 웹앱          [오너: 소정]
├── backend/             ← FastAPI + DB + 에이전트 [오너: 인혁]
│   └── app/prompts/     ← 추출·에이전트 프롬프트  [오너: 소정]
├── scripts/             ← 합성 데이터 생성 등     [오너: 인혁]
└── demo/                ← 데모/소개 페이지 (정적 HTML)
```

- **스캐폴딩-소유 모델 (08/15)**: 뼈대(DB 스키마·stub API·앱 셸·토큰·공통 유틸)는 건태가 선행 구축, 각 폴더의 **로직은 오너가 stub을 교체하며** 채운다. 상세: `docs/06 §2.5`.
- **자기 오너십 밖 폴더를 수정해야 하면**: 커밋 메시지에 `[cross]` 태그 + 오너에게 즉시 공유.
- API 요청/응답 형태를 바꾸면 반드시 `docs/04_API_SPEC.md`를 같은 커밋에서 수정.
- Data Contract 필드를 바꾸면 반드시 `docs/02_DATA_CONTRACT.md`를 같은 커밋에서 수정.

## 자주 쓰는 명령

```bash
# 백엔드 (포트 8000)
cd backend && uv run uvicorn app.main:app --reload

# Console (포트 3000) / Field (포트 3001)
cd apps/console && npm run dev
cd apps/field && npm run dev -- -p 3001

# 합성 데이터 재생성 → DB 초기화 → 시드
python scripts/generate_corpus.py && python scripts/seed_db.py

# 데모 상태로 리셋 (시연 직전 항상 실행)
bash scripts/reset_demo.sh
```

## 코딩 컨벤션

- UI에 보이는 텍스트는 **한국어**, 코드 식별자·DB 컬럼·API 필드는 **영어(snake_case: 백엔드 / camelCase: 프론트)**.
- 프롬프트는 코드에 하드코딩하지 않고 `backend/app/prompts/*.md`에 버전 주석과 함께 저장.
- LLM 호출은 전부 `backend/app/llm.py`의 단일 래퍼 경유 (모델·프롬프트 버전·스키마 로깅 포함).
- 커밋: `feat|fix|docs|style|chore: 한국어 설명 (영역)` — 예: `feat: 승인 카드 스와이프 애니메이션 (field)`.
- 작업 시작 전 `git pull`, 작업 단위마다 커밋, 세션 끝나면 push + `docs/LOG.md`에 한 줄.

## 문서 인덱스

| 문서 | 내용 | 이럴 때 읽어라 |
|---|---|---|
| `docs/00_MASTER_PLAN.md` | 2주 개발 계획, cut line, 리스크 | 오늘 뭘 해야 하는지 볼 때 |
| `docs/01_ARCHITECTURE.md` | 시스템 구조, 데이터 흐름, 상태 머신 | 컴포넌트 간 연결 만들 때 |
| `docs/02_DATA_CONTRACT.md` | Data Contract v0.1 실제 스키마 | 필드·허용값·검증 규칙 필요할 때 |
| `docs/03_SYNTHETIC_DATA.md` | 합성 데이터셋 설계·생성 방법 | 코퍼스 생성·수정할 때 |
| `docs/04_API_SPEC.md` | 백엔드 API 계약 + 목업 fixtures | 프론트↔백엔드 연동할 때 |
| `docs/05_DESIGN_SYSTEM.md` | 디자인 토큰, 애니메이션 규칙, 레퍼런스 | 화면 만들 때 (필수) |
| `docs/06_TEAM_WORKFLOW.md` | 3인 협업 규칙, Claude Code 활용법 | 협업이 꼬였을 때 |
| `docs/07_DEPLOYMENT.md` | Railway 배포 구성·일정·운용, 태그·롤백 규칙 | 배포·심사 URL 관련 작업할 때 |
| `docs/LOG.md` | 일일 진행 로그 | 매일 push 전 한 줄 추가 |

## 데모 시나리오 (모든 기능은 이 6단계 시연에 복무한다)

① Data Contract v0.1 승인 → ② 합성 원석(영문 하이라이트·면담록) 구조화 — HCP 블록 분리 포함 + 사람 검토·승인 → ③ Field 앱으로 신규 면담 수집(한국어: 동의→전사→AE 분기→카드 승인 — 영문 원석과 같은 집계에 합산되는 순간이 다국어 시연 포인트) → ④ Screen 다중 에이전트 교차검증(PubMed·CT.gov·openFDA) → ⑤ Board 심의 + CEO 권고 + 사람 승인 → ⑥ Schema Change Proposal 승인 → Contract v0.2 → Field 입력 폼이 실제로 바뀜.

**대표 가설(HYP-001, Development — 끝까지 완주)**: "청소년(12–17세) 약물난치성 초점발작에서 치료 선택지 공백 반복 → **연령 확대** 근거 생성 우선 검토"
→ XCOPRI는 성인(18세+) 허가이므로 12–17세는 **허가 범위 밖 = Development**. 절대 규칙 #5(상업 액션 자동 연결 금지)를 시연으로 증명하는 축이다.
**대비 가설(HYP-002, In-label)**: "노인(65+) 병용약물 상호작용·적정 부담 → 자료·교육으로 해소" — 허가 범위 내 장벽. 두 종류를 나란히 보여 In-label/Development 분리를 증명한다.
