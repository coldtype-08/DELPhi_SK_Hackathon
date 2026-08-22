/** 핵심 토큰 채점 — 정답지는 scripts/stt_eval/TEST_SCRIPTS.md.
 *
 * 전체 WER보다 이 토큰들이 우선이다: "하하"를 놓치는 건 무해하지만
 * "17세"를 놓치면 대표 가설 HYP-001의 근거가 사라진다. 전사 텍스트가
 * interactions.raw_text가 되고 모든 evidence 오프셋의 기준이므로(docs/02 §1) 되돌릴 수 없다.
 */

export type ScriptId = "A" | "B";

export type TokenSpec = {
  label: string;
  category: string;
  /** 하나라도 맞으면 히트로 본다 (표기 변형 허용) */
  patterns: string[];
  /** 틀리면 데모가 깨지는 항목 */
  critical?: boolean;
  /** 왜 중요한가 — 화면에 표시 */
  why: string;
};

export const KEY_TOKENS: Record<ScriptId, TokenSpec[]> = {
  A: [
    { label: "seventeen-year-old", category: "연령", critical: true, patterns: ["seventeen-year-old", "seventeenyearold", "17-year-old", "17yearold"], why: "S1 신호 — 틀리면 HYP-001 근거 붕괴" },
    { label: "eighteen", category: "연령", critical: true, patterns: ["eighteen", "18"], why: "허가 연령 경계" },
    { label: "two (medications)", category: "실패 약물 수", patterns: ["failed two", "two anti-seizure", "2 anti-seizure"], why: "DRE_2PLUS 판정" },
    { label: "cenobamate", category: "제품명", patterns: ["cenobamate"], why: "product_named 판정" },
    { label: "XCOPRI", category: "제품명", patterns: ["xcopri"], why: "product_named 판정" },
    { label: "drug-resistant focal seizures", category: "도메인 용어", patterns: ["drug-resistantfocalseizures", "drugresistantfocalseizures"], why: "canonical 정규화" },
    { label: "dizziness", category: "AE 용어", patterns: ["dizziness"], why: "S2 안전성 분기" },
    { label: "somnolence", category: "AE 용어", patterns: ["somnolence"], why: "S2 안전성 분기" },
    { label: "approved for adults", category: "오프라벨 신호", critical: true, patterns: ["approvedforadults"], why: "label_scope=OUT_OF_LABEL 근거" },
    { label: "generalized tonic-clonic", category: "PGTC (S7)", critical: true, patterns: ["generalizedtonic-clonic", "generalizedtonicclonic"], why: "완주 대표 HYP-003 근거" },
    { label: "Lennox-Gastaut", category: "LGS (S8)", patterns: ["lennox-gastaut", "lennoxgastaut"], why: "HYP-004 근거" },
    { label: "drop attacks", category: "LGS (S8)", patterns: ["dropattacks"], why: "LGS 특징 발언" },
    { label: "555 123 4567", category: "PII", patterns: ["5551234567", "555-123-4567", "555.123.4567"], why: "masked_spans 정규식" },
  ],
  B: [
    { label: "17세", category: "연령", critical: true, patterns: ["17세", "십칠세", "열일곱"], why: "S1 신호 — 틀리면 HYP-001 근거 붕괴" },
    { label: "18세", category: "연령", critical: true, patterns: ["18세", "십팔세", "열여덟"], why: "허가 연령 경계" },
    { label: "2제", category: "실패 약물 수", patterns: ["2제", "이제실패", "두가지"], why: "DRE_2PLUS 판정" },
    { label: "엑스코프리", category: "제품명", patterns: ["엑스코프리", "xcopri"], why: "product_named 판정" },
    { label: "세노바메이트", category: "제품명", patterns: ["세노바메이트", "cenobamate"], why: "product_named 판정" },
    { label: "lamotrigine", category: "병용 약물", patterns: ["lamotrigine", "라모트리진"], why: "concomitant_drugs" },
    { label: "DDI", category: "영어 전문용어", critical: true, patterns: ["ddi", "디디아이"], why: "한·영 혼용 난이도 — 코드스위칭 실패 시 vocab 매핑 실패" },
    { label: "titration", category: "영어 전문용어", critical: true, patterns: ["titration", "타이트레이션"], why: "한·영 혼용 난이도" },
    { label: "난치성 초점발작", category: "도메인 용어", patterns: ["난치성초점발작", "난치성", "초점발작"], why: "canonical 정규화" },
    { label: "병용약", category: "도메인 용어", patterns: ["병용약", "병용약물"], why: "canonical 정규화" },
    { label: "상호작용", category: "도메인 용어", patterns: ["상호작용"], why: "DDI_CONCERN 매핑" },
    { label: "어지러움", category: "AE 용어", patterns: ["어지러움", "어지럼"], why: "S2 안전성 분기" },
    { label: "졸림", category: "AE 용어", patterns: ["졸림", "졸음"], why: "S2 안전성 분기" },
    { label: "성인 허가", category: "오프라벨 신호", critical: true, patterns: ["성인허가"], why: "label_scope=OUT_OF_LABEL 근거" },
    { label: "010-4132-7789", category: "PII", patterns: ["01041327789", "010-4132-7789"], why: "masked_spans 정규식" },
    { label: "전신 강직-간대발작", category: "PGTC (S7)", critical: true, patterns: ["전신강직-간대발작", "전신강직간대발작"], why: "완주 대표 HYP-003 근거 — 08/21 재지정" },
    { label: "PGTC", category: "PGTC (S7)", critical: true, patterns: ["pgtc", "피지티씨"], why: "완주 대표 HYP-003 근거" },
    { label: "레녹스-가스토", category: "LGS (S8)", patterns: ["레녹스-가스토", "레녹스가스토", "lennox"], why: "HYP-004 근거" },
    { label: "드롭발작", category: "LGS (S8)", patterns: ["드롭발작", "드롭 발작"], why: "LGS 특징 발언" },
    { label: "김도현", category: "PII", patterns: ["김도현"], why: "masked_spans 정규식" },
  ],
};

/** 공백 제거 + 소문자 — 한국어 띄어쓰기 변형("초점 발작" vs "초점발작")을 흡수한다. */
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
