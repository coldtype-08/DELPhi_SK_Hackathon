/** 핵심 토큰 채점 — 정답지는 scripts/stt_eval/TEST_SCRIPTS.md.
 *
 * 전체 WER보다 이 토큰들이 우선이다: "하하"를 놓치는 건 무해하지만
 * "17세"를 놓치면 S1 신호가 사라진다. 전사 텍스트가 interactions.raw_text가 되고
 * 모든 evidence 오프셋의 기준이므로(docs/02 §1) 되돌릴 수 없다.
 *
 * 대본 3종:
 *   P1 — HYP-003(PGTC) 초안 7턴. TTS로 만들어 STT 3종 비교에 쓴다 (scripts/stt_eval/P1_reference.txt)
 *   D1 — apps/field/lib/capture-demo.ts 의 SCRIPT 7턴 그대로 (실제 시나리오)
 *   T1 — D1 + 영어 용어 혼용 + PII (코드스위칭·마스킹 테스트)
 */

export type ScriptId = "P1" | "D1" | "T1";

export type TokenSpec = {
  label: string;
  category: string;
  /** 하나라도 맞으면 히트 (표기 변형 허용) */
  patterns: string[];
  /** 틀리면 데모가 깨지는 항목 */
  critical?: boolean;
  /** 왜 중요한가 — 화면에 표시 */
  why: string;
};

/** D1·T1 공통 토큰 — 두 대본이 같은 시나리오를 공유한다 */
const SHARED: TokenSpec[] = [
  { label: "17세", category: "연령", critical: true, patterns: ["17세", "십칠세", "열일곱"], why: "S1 신호 — 틀리면 신호 소멸" },
  { label: "18세", category: "연령", critical: true, patterns: ["18세", "십팔세", "열여덟"], why: "허가 연령 경계" },
  { label: "2제", category: "실패 약물 수", patterns: ["2제", "이제실패", "두가지"], why: "DRE_2PLUS 판정" },
  { label: "성인 허가", category: "오프라벨 신호", critical: true, patterns: ["성인허가"], why: "label_scope=OUT_OF_LABEL 근거" },
  { label: "약물난치성", category: "도메인 용어", patterns: ["약물난치성", "난치성"], why: "canonical 정규화" },
  { label: "어지러움", category: "AE 용어", patterns: ["어지러움", "어지럼"], why: "S2 안전성 분기" },
  { label: "졸림", category: "AE 용어", patterns: ["졸림", "졸음"], why: "S2 안전성 분기" },
  { label: "청소년 용량", category: "자료 요청", patterns: ["청소년용량"], why: "S4 집계" },
  { label: "안전성 자료", category: "자료 요청", patterns: ["안전성자료"], why: "S4 집계" },
];

/** T1 전용 — 영어 용어 혼용과 PII */
const T1_ONLY: TokenSpec[] = [
  { label: "XCOPRI", category: "제품명", patterns: ["xcopri", "엑스코프리"], why: "product_named 판정" },
  { label: "lamotrigine", category: "병용 약물", patterns: ["lamotrigine", "라모트리진"], why: "concomitant_drugs" },
  { label: "DDI", category: "영어 전문용어", critical: true, patterns: ["ddi", "디디아이"], why: "한·영 혼용 난이도 — 실패 시 vocab 매핑 실패" },
  { label: "titration", category: "영어 전문용어", critical: true, patterns: ["titration", "타이트레이션"], why: "한·영 혼용 난이도" },
  { label: "병용약", category: "도메인 용어", patterns: ["병용약", "병용약물"], why: "DDI_CONCERN 매핑" },
  { label: "010-4132-7789", category: "PII", patterns: ["01041327789", "010-4132-7789"], why: "masked_spans 정규식" },
];

/** P1 전용 — HYP-003(PGTC) 초안. ★는 틀리면 HYP-003 서사가 깨지는 항목이다. */
const P1_TOKENS: TokenSpec[] = [
  { label: "전신 강직-간대발작", category: "환자군 ★", critical: true, patterns: ["전신강직-간대발작", "전신강직간대발작"], why: "GENERALIZED_PGTC — 놓치면 HYP-003 신호 소멸" },
  { label: "전신발작", category: "환자군", critical: true, patterns: ["전신발작"], why: "GENERALIZED_PGTC 재확인 (2회 등장)" },
  { label: "허가 범위", category: "오프라벨 신호", critical: true, patterns: ["허가범위"], why: "label_scope=OUT_OF_LABEL 근거" },
  { label: "초점발작", category: "대비 환자군", patterns: ["초점발작"], why: "focal-only 적응증 대비 — S7 서사의 축" },
  { label: "선택지가 없", category: "미충족 수요", critical: true, patterns: ["선택지가없", "선택지없"], why: "signal_type=UNMET_NEED 판정 근거" },
  { label: "세 번째 약", category: "실패 약물 수", patterns: ["세번째약", "3번째약", "삼번째약"], why: "약물난치성 정도 판정" },
  { label: "XCOPRI", category: "제품명", patterns: ["xcopri", "엑스코프리", "엑스코프리정"], why: "product_named 판정" },
  { label: "난치성", category: "도메인 용어", patterns: ["난치성", "약물난치성"], why: "canonical 정규화" },
  { label: "어지러움", category: "AE 용어", critical: true, patterns: ["어지러움", "어지럼"], why: "S2 안전성 분기 — 놓치면 AE가 일반 집계로 섞인다" },
  { label: "졸림", category: "AE 용어", critical: true, patterns: ["졸림", "졸음"], why: "S2 안전성 분기" },
  { label: "문헌", category: "자료 요청", patterns: ["문헌"], why: "INFO_REQUEST → Action Item → Field 체크리스트" },
  { label: "ClinicalTrials", category: "영어 고유명사", patterns: ["clinicaltrials", "클리니컬트라이얼"], why: "한·영 혼용 난이도 + Screen 근거 출처" },
  { label: "010-4132-7789", category: "PII", critical: true, patterns: ["01041327789", "010-4132-7789"], why: "masked_spans 정규식 — 발표에서 마스킹이 보여야 한다" },
];

export const KEY_TOKENS: Record<ScriptId, TokenSpec[]> = {
  P1: P1_TOKENS,
  D1: SHARED,
  T1: [...SHARED, ...T1_ONLY],
};

/** 공백 제거 + 소문자 — 한국어 띄어쓰기 변형("청소년 용량" vs "청소년용량")을 흡수한다. */
function normalize(s: string): string {
  return s.toLowerCase().replace(/\s+/g, "");
}

export type ScoreRow = { spec: TokenSpec; hit: boolean };

export function scoreTranscript(transcript: string, script: ScriptId): ScoreRow[] {
  const hay = normalize(transcript);
  return KEY_TOKENS[script].map((spec) => ({
    spec,
    hit: spec.patterns.some((p) => hay.includes(normalize(p))),
  }));
}

export function scoreSummary(rows: ScoreRow[]) {
  const total = rows.length;
  const hit = rows.filter((r) => r.hit).length;
  const criticalRows = rows.filter((r) => r.spec.critical);
  return {
    total,
    hit,
    ratio: total ? hit / total : 0,
    criticalTotal: criticalRows.length,
    criticalHit: criticalRows.filter((r) => r.hit).length,
  };
}
