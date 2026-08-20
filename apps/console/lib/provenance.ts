/**
 * Contract 유래(Provenance) 데이터 — 결정론적 기록의 렌더링용 (LLM 호출 없음).
 *
 * 출처(단일 진실):
 *  - 판정: docs/DECISIONS.md 08/19 (채택 9 · 제외 사유 · 보류→SCP 5묶음)
 *  - AI 격리 초안 무편집 원문: docs/assets/bootstrap-ai-draft.md (인용문·문서 ID는 여기서 그대로 옮김)
 *  - 스키마 조각: backend/app/contract/contract_v0_1.yaml
 *  - DB 컬럼: backend/app/models.py
 * 기록이 바뀌면 이 파일도 같은 커밋에서 고친다.
 */

export type Verdict = "verify" | "adopt" | "override" | "exclude" | "hold" | "seed";

export type DocRef = {
  id: string; // 축약 표기 — 001 = DOC-20250915-001 형식 (초안의 인용 축약 그대로)
  type: "H" | "N" | "C" | "E" | "P" | "V";
};

export const DOC_TYPE_KO: Record<DocRef["type"], string> = {
  H: "하이라이트 묶음",
  N: "면담 기록",
  C: "전화 메모",
  E: "이메일 요약",
  P: "학회 보고서(PDF)",
  V: "음성 전사(한국어)",
};

/** 격리 초안이 열람한 표본 15건 (bootstrap-ai-draft §2.1의 doc_type 근거 그대로) */
export const SAMPLE_DOCS: DocRef[] = [
  { id: "001", type: "H" },
  { id: "002", type: "N" },
  { id: "003", type: "N" },
  { id: "004", type: "N" },
  { id: "005", type: "H" },
  { id: "006", type: "E" },
  { id: "007", type: "C" },
  { id: "008", type: "N" },
  { id: "009", type: "N" },
  { id: "010", type: "H" },
  { id: "012", type: "N" },
  { id: "013", type: "C" },
  { id: "015", type: "P" },
  { id: "037", type: "P" },
  { id: "061", type: "V" },
];

export type Quote = { doc: string; text: string; ko?: boolean };

export type Consumer = {
  label: string;
  on: boolean;
  note?: string;
};

export type Concept = {
  key: string;
  name: string;
  fieldLine: string;
  docs: string[];
  stat: string;
  verdict: Verdict;
  chip: string;
  quotes: Quote[];
  aiProposal: string;
  humanVerdict: string;
  schemaSummary: string;
  /** contract_v0_1.yaml 실제 조각 (채택·검증 개념만) */
  yaml?: string;
  /** 이 판정이 만들어 낸 DB 컬럼 */
  columns?: { table: string; column: string; note?: string }[];
  /** 하나의 정의를 공유하는 여섯 소비처 (docs/02 머리말) */
  consumers?: Consumer[];
  /** 스키마 반영이 없는 판정(제외·보류·씨앗)의 행선지 설명 */
  none?: string;
};

const SIX = (form: Consumer, filter?: Consumer, agent?: Consumer): Consumer[] => [
  { label: "추출 출력", on: true },
  { label: "서버 검증", on: true },
  { label: "DB 컬럼", on: true },
  form,
  filter ?? { label: "대시보드 필터", on: true },
  agent ?? { label: "에이전트 입력", on: true },
];

export const CONCEPTS: Concept[] = [
  {
    key: "adolescent",
    name: "청소년 치료 공백",
    fieldLine: "patient_segment · label_scope",
    docs: ["001", "004", "005", "010", "015", "061"],
    stat: "6건 · 5인",
    verdict: "verify",
    chip: "검증 · 유지",
    quotes: [
      {
        doc: "005",
        text: "“my hardest clinic days are telling parents of a seventeen-year-old…” — 성인 전용 허가의 한계를 부모에게 설명하는 날들",
      },
      { doc: "001", text: "“15- and 16-year-olds” — 우회 요청이 아니라 허가 한계의 기록으로 서술" },
      { doc: "061", text: "“2제 실패한 17세 환자인데 성인 허가라 손을 쓸 수 없다” — 한국어 전사에서 같은 군집", ko: true },
    ],
    aiProposal:
      "v0.1을 모르는 격리 초안이 같은 군집(ADOLESCENT_DRE_GAP)을 최다 반복 신호로 검출하고, 같은 게이트(OFF_LABEL_DEVELOPMENT → 의료 검토 전용 라우팅)까지 독립적으로 설계했다.",
    humanVerdict:
      "36컬럼 원안 · 격리 초안 · v0.1 세 갈래가 같은 지점에 수렴 — 기존 정의를 유지 확정했다. 대표 가설 HYP-001의 축.",
    schemaSummary: "유지: patient_segment=PEDIATRIC_TRANSITION → label_scope 자동판정 (절대 규칙 #5)",
    yaml: `patient_segment:
  label_ko: 환자군
  required: true
  field_form: true
  values:
    - { value: PEDIATRIC_TRANSITION, label_ko: 청소년(12–17세) 전환기,
        label_scope: OUT_OF_LABEL }   # 허가 범위 밖 → 참조 가설은 자동 DEVELOPMENT
    …`,
    columns: [
      { table: "claims", column: "patient_segment" },
      { table: "claims", column: "label_scope", note: "서버 자동판정 — derivations 규칙" },
      { table: "hypotheses", column: "kind", note: "OUT_OF_LABEL 참조 시 DEVELOPMENT 강제" },
    ],
    consumers: SIX({ label: "Field 폼", on: true }),
  },
  {
    key: "solicitation",
    name: "발언 경위 — 자발인가 유도인가",
    fieldLine: "solicitation (신규)",
    docs: ["001", "004", "005", "010", "037", "061"],
    stat: "6건",
    verdict: "adopt",
    chip: "신규 채택",
    quotes: [
      { doc: "001", text: "“without any prompting” — HCP가 먼저 꺼낸 오프라벨 주제" },
      { doc: "010", text: "“before I had asked anything”" },
      { doc: "061", text: "MSL이 먼저 화제를 제기 — 같은 주제라도 SOLICITED로 갈리는 사례", ko: true },
    ],
    aiProposal:
      "원문들이 발언 경위를 일관되게 명시하고 있음을 발견했다. 같은 오프라벨 언급이라도 자발이냐 유도냐에 따라 컴플라이언스 의미가 갈린다는 제안 — v0.1 원안에는 없던 축이다.",
    humanVerdict: "채택. 원문이 이미 기록하고 있던 정보를 스키마가 받지 못하고 있었다 — AI 초안의 발견.",
    schemaSummary: "신규: solicitation = UNSOLICITED | SOLICITED_BY_MSL | UNCLEAR",
    yaml: `solicitation:
  label_ko: 발언 경위
  required: false
  field_form: false   # 추출 산출 — 오프라벨 언급의 컴플라이언스
  values:             #   의미가 갈리는 축 (AI 초안의 발견)
    - { value: UNSOLICITED,      label_ko: 자발적 언급 }
    - { value: SOLICITED_BY_MSL, label_ko: MSL 질문에 답변 }
    - { value: UNCLEAR,          label_ko: 불명확 }`,
    columns: [{ table: "claims", column: "solicitation", note: "08/19 부트스트랩 추가" }],
    consumers: SIX({ label: "Field 폼", on: false, note: "field_form: false — 추출 산출" }),
  },
  {
    key: "ae",
    name: "이상사례의 문맥",
    fieldLine: "event_terms · severity_note · product_named (신규)",
    docs: ["061"],
    stat: "1건 · KO",
    verdict: "adopt",
    chip: "신규 채택",
    quotes: [
      {
        doc: "061",
        text: "“복용 시작하고 나서 어지러움하고 졸림이 꽤 있다고 하셨어요” — 대화 중간, 제품명은 미언급",
        ko: true,
      },
    ],
    aiProposal:
      "코퍼스의 유일한 AE가 ‘한국어 · 대화 중간 · 제품 미명명’이라는 가장 놓치기 쉬운 형태였다. 보고 용어와 심각성 표현은 원문 그대로, 제품 실명 여부는 불리언으로 제안 — 등급·인과판정 필드는 PV 시스템 관할이라며 스스로 배제했다.",
    humanVerdict:
      "3필드 채택. product_named=false면 PV 인계 전 사람 확인을 강제한다 — 분리 경로(절대 규칙 #6)가 필드 수준으로 구체화됐다.",
    schemaSummary: "신규(safety 전용): event_terms · severity_note(원문 표현 그대로) · product_named",
    columns: [
      { table: "safety_candidates", column: "event_terms" },
      { table: "safety_candidates", column: "severity_note", note: "원문 표현 그대로 — 등급 판정은 PV 관할" },
      { table: "safety_candidates", column: "product_named", note: "false면 인계 전 사람 확인 필수" },
    ],
    consumers: [
      { label: "추출 출력", on: true },
      { label: "서버 검증", on: true },
      { label: "DB (safety 전용 테이블)", on: true },
      { label: "Field 폼", on: false, note: "「분기됨」 배지만 표시" },
      { label: "대시보드 필터", on: false, note: "SAFETY 롤 전용 조회" },
      { label: "에이전트 입력", on: false, note: "Safety Agent만 읽음" },
    ],
  },
  {
    key: "elderly",
    name: "노인 병용·상호작용 부담",
    fieldLine: "ELDERLY_65_PLUS · DDI_CONCERN",
    docs: ["001", "005", "009"],
    stat: "3건",
    verdict: "verify",
    chip: "검증 · 유지",
    quotes: [
      { doc: "001", text: "고령 병용환자의 상호작용 우려 — 허가 범위 안의 장벽 사례" },
      { doc: "009", text: "“skewing older” — 환자 패널의 고령화 흐름" },
    ],
    aiProposal: "ELDERLY_DDI_POLYPHARMACY를 독립 토픽으로 검출 — In-label 장벽 축이 데이터에 실재함을 확인했다.",
    humanVerdict:
      "유지. 대비 가설 HYP-002(In-label)의 근거 축으로, Development(청소년)와 나란히 놓아 절대 규칙 #5의 분리를 시연한다.",
    schemaSummary: "유지: patient_segment=ELDERLY_65_PLUS · barrier_type=DDI_CONCERN",
    yaml: `barrier_type:
  required_if: { field: signal_type, equals: TREATMENT_BARRIER }
  values:
    - { value: DDI_CONCERN, label_ko: 약물 상호작용 우려 }
    …`,
    columns: [
      { table: "claims", column: "patient_segment" },
      { table: "claims", column: "barrier_type", note: "TREATMENT_BARRIER일 때 필수 — 조건부 검증" },
    ],
    consumers: SIX({ label: "Field 폼", on: true }),
  },
  {
    key: "mentions",
    name: "적응증·병용약·투여 관찰",
    fieldLine: "indication_mention · concomitant_drugs · …",
    docs: ["005", "010", "015"],
    stat: "3건",
    verdict: "adopt",
    chip: "신규 채택",
    quotes: [
      { doc: "010", text: "실패한 선행 약물들이 인용문 안에만 존재 — “named solely as failed prior therapies inside quotes”" },
      { doc: "005", text: "미허가 적응증에 대한 관심 언급 → REPURPOSING_SIGNAL의 원형" },
    ],
    aiProposal:
      "약물명·적응증 언급이 인용문 속에 갇혀 집계할 수 없음을 지적했다. 단, enum이 아니라 텍스트 필드로 — 정규화는 vocab 계층의 일이라는 단서를 달았다.",
    humanVerdict:
      "3필드 채택 + signal_type에 REPURPOSING_SIGNAL 추가(자동 OUT_OF_LABEL). ‘특정 약물 병용 언급 N회’ 같은 집계가 비로소 가능해진다.",
    schemaSummary: "신규: indication_mention · concomitant_drugs · administration_note (text) + REPURPOSING_SIGNAL",
    yaml: `indication_mention:
  label_ko: 언급된 적응증(원문)
  type: text        # enum 아님 — POST_STROKE의 SCP 각본과 분리 유지
concomitant_drugs:
  type: text        # 쉼표 구분. 정규화는 vocab 계층에서
administration_note:
  type: text        # 용량 수치는 의도적 제외 (규제 민감)`,
    columns: [
      { table: "claims", column: "indication_mention" },
      { table: "claims", column: "concomitant_drugs" },
      { table: "claims", column: "administration_note" },
      { table: "claims", column: "signal_type", note: "값 추가: REPURPOSING_SIGNAL → label_scope 자동 OUT_OF_LABEL" },
    ],
    consumers: SIX({ label: "Field 폼", on: false, note: "추출 산출" }),
  },
  {
    key: "sentiment",
    name: "발언 논조",
    fieldLine: "sentiment (신규 · 제약 조건부)",
    docs: ["001", "010"],
    stat: "2건",
    verdict: "override",
    chip: "채택 · 권고 번복",
    quotes: [
      { doc: "010", text: "“tone noticeably positive”" },
      { doc: "001", text: "“accepted without pushback”" },
    ],
    aiProposal: "1차 권고는 제외 — “주관적이고, 추출이 불안정하며, HCP 프로파일링에 인접한다.”",
    humanVerdict:
      "도메인 오너가 권고를 번복해 채택했다. 단 HCP 개인별 집계 금지(절대 규칙 #7), 세그먼트·토픽 단위만이라는 사용 제약을 스키마에 함께 적었다. AI 제안을 사람이 그대로 받지 않는다는 것 자체가 이 절차의 증명이다.",
    schemaSummary: "신규(제약부): sentiment = POSITIVE | NEUTRAL | NEGATIVE | MIXED — 개인 단위 집계 금지",
    yaml: `sentiment:
  label_ko: 발언 논조
  field_form: false   # 08/19 도메인 오너 판단으로 채택.
  values:             # **HCP 개인별 집계 금지** (절대규칙 #7)
    - { value: POSITIVE, label_ko: 긍정 }
    - { value: NEGATIVE, label_ko: 부정 }
    …`,
    columns: [{ table: "claims", column: "sentiment", note: "세그먼트·토픽 단위 집계만 허용" }],
    consumers: SIX(
      { label: "Field 폼", on: false, note: "추출 산출" },
      { label: "대시보드 필터", on: true, note: "세그먼트 단위만" },
    ),
  },
  {
    key: "numerics",
    name: "환자 수·대기기간 수치",
    fieldLine: "(구조화하지 않음)",
    docs: ["004", "005", "009", "010", "037"],
    stat: "5건",
    verdict: "exclude",
    chip: "제외 · 수치",
    quotes: [
      { doc: "005", text: "“two such pts this month” · “nine weeks out”" },
      { doc: "009", text: "“about a third more”" },
      { doc: "010", text: "“nobody has measured it properly” — 원문이 스스로 비정밀을 자백" },
    ],
    aiProposal:
      "검증할 수 없는 인상 수치를 정수 필드로 만들면 허위 정밀도와 일화 합산을 초대한다며 독립적으로 반대 — 절대 규칙 #1과 수렴했다.",
    humanVerdict: "제외 확정. 수치는 verbatim 안에만 남고, 모든 카운트는 APPROVED 행 위에서 SQL로만 계산한다.",
    schemaSummary: "제외: 용량·횟수 수치 5종 — 사유 기록됨 (DECISIONS 08/19)",
    none: "어느 테이블에도 컬럼이 생기지 않았다. 숫자가 필요한 곳은 signal_aggregates(SQL 뷰)가 APPROVED claim을 세는 것으로 대신한다.",
  },
  {
    key: "prescriber",
    name: "처방자 파악 정보",
    fieldLine: "(구조화하지 않음)",
    docs: ["010", "037"],
    stat: "2건",
    verdict: "exclude",
    chip: "제외 · AI 판단",
    quotes: [
      { doc: "010", text: "특정 HCP의 환자가 제품을 복용 중임이 드러나는 서술" },
      { doc: "037", text: "학회 대화 속 같은 유형의 임상 경험담" },
    ],
    aiProposal:
      "‘처방자 플래그’는 처방 성향 프로파일링으로 직결된다며 스스로 구조화를 거부 — 절대 규칙 #7(개별 HCP 점수화 금지)과 수렴했다.",
    humanVerdict: "동의. 관찰은 CLINICAL_EXPERIENCE 신호로만 남기고, HCP 단위 롤업 속성은 만들지 않는다.",
    schemaSummary: "제외: per-HCP prescriber flag — 개인 속성으로 저장하지 않음",
    none: "hcps 성격의 마스터에 행동 속성을 두지 않는 것이 규칙이다. 집계는 언제나 ‘몇 명의 독립 HCP인가’이지, ‘누가’가 아니다.",
  },
  {
    key: "meta",
    name: "직함·채널·시간 메타",
    fieldLine: "credential · channel · duration …",
    docs: ["001", "007", "012", "037", "061"],
    stat: "5건+",
    verdict: "hold",
    chip: "보류 → SCP",
    quotes: [
      { doc: "012", text: "“8:40 a.m.” — 시간 상세가 실재하지만 지금의 질문에는 불필요" },
      { doc: "037", text: "“approximately 11:40”" },
    ],
    aiProposal: "채널·소요시간·방문 형태·직함 등 원문에 실재하는 메타데이터를 폭넓게 제안했다.",
    humanVerdict:
      "보류. 지금 넣으면 스키마만 비대해진다. 필요가 반복으로 증명되면 SCP로 승격한다 — msl_response · MSL/기관 마스터도 같은 묶음이다.",
    schemaSummary: "보류 5묶음 → schema_change_proposals 후보로 대기",
    none: "지금은 어떤 컬럼도 아니다. 반복이 쌓여 근거가 생기면 schema_change_proposals 행으로 태어난다 — v0.1이 만들어진 절차와 같은 문으로 들어온다.",
  },
  {
    key: "poststroke",
    name: "뇌졸중 후 뇌전증",
    fieldLine: "POST_STROKE — v0.1에 없음",
    docs: ["005"],
    stat: "1건 · 1인",
    verdict: "seed",
    chip: "미달 → v0.2 씨앗",
    quotes: [{ doc: "005", text: "post-stroke epilepsy에 대한 관심 — 표본에서 단 1회 등장 (“appeared once, mid-corpus”)" }],
    aiProposal:
      "고정 enum 대신 ‘사람이 승인해 확장하는 governed vocabulary’를 제안하며 이 사례를 근거로 인용 — SCP 절차와 같은 구조를 독립적으로 도출했다.",
    humanVerdict:
      "v0.1 미채택. 승격 조건(반복 ≥3회 · 독립 HCP ≥2인)에 미달하기 때문이다. 전체 코퍼스에서 6회/4인이 누적되면 SCP로 자동 제안된다(데모 ⑥). 넣지 않은 이유가 기록된 항목이 스키마 진화의 출발점이 된다.",
    schemaSummary: "대기: unmapped_terms 누적 → SCP → v0.2에서 patient_segment=POST_STROKE",
    none: "추출이 이 표현을 만나면 unmapped_terms에 쌓인다. 반복 ≥3회 · 독립 HCP ≥2인이 되는 순간 schema_change_proposals가 자동 생성되고, Steward가 승인하면 v0.2가 발행되어 Field 폼에 새 항목이 나타난다.",
  },
  {
    key: "congress",
    name: "학회 세션 내용·경쟁약 상세",
    fieldLine: "(구조화하지 않음)",
    docs: ["010", "015", "037"],
    stat: "3건",
    verdict: "exclude",
    chip: "제외 · 영역 분리",
    quotes: [
      { doc: "015", text: "학회 세션 요약 — 연구 결과물은 Sense가 아니라 Screen의 영역" },
      { doc: "037", text: "타 기관 내부 워크플로우 서술" },
    ],
    aiProposal:
      "연구 결과물과 타 조직 내부는 토픽 코드가 붙은 신호로만 남기고 모델링하지 않겠다고 제안 — 제품 마스터도 단일 제품이라 보류했다.",
    humanVerdict:
      "동의. 외부 공개 근거(PubMed·CT.gov)는 Screen 에이전트의 관할이다. 사내 데이터와 공개 근거의 분리가 흐려지면 추적성이 깨진다.",
    schemaSummary: "제외: 세션 내용·타 기관 내부 — Sense/Screen 영역 분리 유지",
    none: "이 내용의 자리는 claims가 아니라 screen_findings다 — 외부 출처 · 스냅샷 일시 · 해석 한계 문구(caveat_ko)와 함께 저장되는 다른 세계의 테이블.",
  },
];

export const VERDICT_STYLE: Record<
  Verdict,
  { chipClass: string; glyph: "dot" | "x" | "ring" | "diamond" }
> = {
  verify: { chipClass: "bg-green-soft text-green", glyph: "dot" },
  adopt: { chipClass: "bg-green-soft text-green", glyph: "dot" },
  override: { chipClass: "bg-green-soft text-green", glyph: "dot" },
  exclude: { chipClass: "bg-rust-soft text-rust", glyph: "x" },
  hold: { chipClass: "bg-sky-soft text-sky", glyph: "ring" },
  seed: { chipClass: "bg-orange-soft text-orange-deep", glyph: "diamond" },
};
