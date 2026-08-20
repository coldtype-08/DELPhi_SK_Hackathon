/**
 * 전사 재생 폴백 대본 (docs/03 §6) — 라이브 마이크(Web Speech, P1) 실패 대비 고정 대본.
 * 재생 중의 구간 하이라이트·감지 칩은 데모 연출이고, 정본 추출은 제출 시 서버에서 1회 수행된다(재현성).
 * [cross] 오너: 소정 — 대본 문구·연출 타이밍은 자유롭게 교체하세요. 색 매핑은 globals.css의 mark.ev-*.
 */

export type EvCat = "segment" | "signal" | "ae" | "info" | "meta";

export const CAT_LABEL: Record<EvCat, string> = {
  segment: "환자군",
  signal: "신호",
  ae: "안전성",
  info: "자료 요청",
  meta: "경위",
};

export type Span = { q: string; cat: EvCat };
export type Catch = { label: string; cat: EvCat };
export type Line = {
  sp: "MSL" | "의사";
  t: string;
  spans?: Span[];
  catches?: Catch[];
  ae?: boolean;
  end?: boolean;
};

export const SCRIPT: Line[] = [
  { sp: "MSL", t: "안녕하세요 선생님, 지난 학회는 잘 다녀오셨어요?" },
  { sp: "의사", t: "네, 다녀오고 나니 외래가 밀려서 정신이 없네요." },
  { sp: "MSL", t: "요즘 약물난치성 환자분들은 좀 어떠세요?" },
  {
    sp: "의사",
    t: "2제 실패한 17세 환자가 있는데, 성인 허가라 손을 쓸 수가 없어요. 18세까지 기다리는 수밖에요.",
    spans: [
      { q: "2제 실패한 17세 환자", cat: "segment" },
      { q: "성인 허가라 손을 쓸 수가 없어요", cat: "signal" },
    ],
    catches: [
      { label: "환자군 · 청소년(12–17) — 허가 범위 밖", cat: "segment" },
      { label: "신호 · 미충족 수요", cat: "signal" },
      { label: "경위 · MSL 질문에 답변", cat: "meta" },
    ],
  },
  {
    sp: "의사",
    t: "아, 그리고 성인 환자 한 분은 복용 시작하고 어지러움하고 졸림이 꽤 있다고 하셨어요.",
    ae: true,
    spans: [{ q: "어지러움하고 졸림", cat: "ae" }],
    catches: [{ label: "부작용 의심 → 안전성 경로 분리 · 일반 카드 제외", cat: "ae" }],
  },
  {
    sp: "의사",
    t: "혹시 청소년 용량이나 안전성 자료가 있으면 보내주실 수 있어요?",
    spans: [{ q: "청소년 용량이나 안전성 자료", cat: "info" }],
    catches: [{ label: "자료 요청 → 체크리스트 후보", cat: "info" }],
  },
  { sp: "MSL", t: "확인해서 다음 방문 때 정리해 드리겠습니다.", end: true },
];

/** 재생 완료 시 입력란에 담기는 전사 전문 — 이 텍스트가 실제 제출(rawText)로 이어진다. */
export function fullTranscript(): string {
  return SCRIPT.map((l) => `${l.sp}: ${l.t}`).join("\n");
}
