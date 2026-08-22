/** 대본 → 음성 (Gemini TTS). 실제 호출은 /api/tts 라우트가 한다 — 이유는 그 파일 주석 참조. */

export type TtsSpeaker = { name: string; voice: string };

export type TtsResult = {
  blob: Blob;
  sampleRate: number;
  /** rate 를 응답 mimeType 에서 실제로 읽었는가 (false면 24000 가정값) */
  rateKnown: boolean;
  sourceMime: string;
  seconds: number;
};

/** 기본 대본 3종 — scripts/stt_eval/TEST_SCRIPTS.md 와 문장이 같아야 한다. */
export const TTS_PRESETS: Record<string, string> = {
  D1: [
    "MSL: 안녕하세요 선생님, 지난 학회는 잘 다녀오셨어요?",
    "HCP: 네, 다녀오고 나니 외래가 밀려서 정신이 없네요.",
    "MSL: 요즘 약물난치성 환자분들은 좀 어떠세요?",
    "HCP: 2제 실패한 17세 환자가 있는데, 성인 허가라 손을 쓸 수가 없어요. 18세까지 기다리는 수밖에요.",
    "HCP: 아, 그리고 성인 환자 한 분은 복용 시작하고 어지러움하고 졸림이 꽤 있다고 하셨어요.",
    "HCP: 혹시 청소년 용량이나 안전성 자료가 있으면 보내주실 수 있어요?",
    "MSL: 확인해서 다음 방문 때 정리해 드리겠습니다.",
  ].join("\n"),
  T1: [
    "MSL: 안녕하세요 선생님, 지난 학회는 잘 다녀오셨어요?",
    "HCP: 네, 다녀오고 나니 외래가 밀려서 정신이 없네요.",
    "MSL: 요즘 약물난치성 환자분들은 좀 어떠세요?",
    "HCP: 2제 실패한 17세 환자가 있는데, XCOPRI는 성인 허가라 손을 쓸 수가 없어요. 18세까지 기다리는 수밖에요.",
    "HCP: 고령 환자분들은 lamotrigine 같은 병용약이 많아서 DDI부터 걱정하시고, titration 스케줄도 부담스럽다고 하세요.",
    "HCP: 아, 그리고 성인 환자 한 분은 복용 시작하고 어지러움하고 졸림이 꽤 있다고 하셨어요.",
    "HCP: 혹시 청소년 용량이나 안전성 자료가 있으면 보내주실 수 있어요? 제 번호 010-4132-7789로 주셔도 되고요.",
    "MSL: 확인해서 다음 방문 때 정리해 드리겠습니다.",
  ].join("\n"),
  P1: [
    "MSL: 안녕하세요 선생님, 외래 끝나고 잠시 괜찮으세요?",
    "HCP: 네, 오늘은 좀 일찍 끝났어요. 앉으세요.",
    "MSL: 요즘 난치성 환자분들 중에 특히 손 쓰기 어려운 케이스가 있으세요?",
    "HCP: 전신 강직-간대발작 환자분들이 그래요. XCOPRI가 초점발작에는 잘 듣는 걸 아는데, 전신발작은 허가 범위가 아니라서 아예 선택지가 없어요. 세 번째 약까지 실패한 분이 지금 두 분 계신데 드릴 게 없으니 답답하죠.",
    "HCP: 아, 그리고 지난달에 시작한 성인 환자 한 분은 초기에 어지러움하고 졸림이 좀 있다고 하셨어요.",
    "HCP: 그, 전신발작 환자군 관련해서 나온 문헌이나 ClinicalTrials에 등록된 연구가 있으면 좀 보내주실 수 있을까요? 제 번호 010-4132-7789로 주셔도 되고요.",
    "MSL: 확인해서 있는 범위 내에서 다음 방문 때 정리해 드리겠습니다. 말씀 주신 이상반응은 절차대로 안전성 검토 경로로 전달하겠습니다.",
  ].join("\n"),
};

/** 한국인 의사 면담이라는 조건을 음성에 반영시키는 지시문 — 영어 용어를 한국식으로 읽게 하는 것이 핵심 */
export const DEFAULT_STYLE_PROMPT =
  "한국 병원에서 제약회사 MSL과 신경과 의사가 나누는 실제 면담이다. " +
  "또박또박 읽지 말고 평소 말하는 속도로, 진료실에서 대화하듯 자연스럽게 읽어라. " +
  "XCOPRI, lamotrigine, DDI, titration, ClinicalTrials 같은 영어 단어는 " +
  "영어권 발음이 아니라 한국인이 한국어 문장 안에서 말할 때의 발음으로 읽어라. " +
  "전화번호는 숫자를 하나씩 또렷하게 읽어라.";

/** 모델 이름을 추측하지 않는다 — 벤더에서 목록을 받아온다. */
export async function listTtsModels(apiKey: string): Promise<{ tts: string[]; all: string[] }> {
  const r = await fetch("/api/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "models", apiKey }),
  });
  const j = await r.json();
  if (!r.ok) throw new Error(j?.error ? `${j.error} ${JSON.stringify(j.raw ?? "")}` : `실패 (${r.status})`);
  return j;
}

export async function synthesize(args: {
  apiKey: string;
  model: string;
  script: string;
  speakers: TtsSpeaker[];
  stylePrompt: string;
}): Promise<TtsResult> {
  const r = await fetch("/api/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "synthesize", ...args }),
  });
  if (!r.ok) {
    const j = await r.json().catch(() => null);
    throw new Error(j?.error ? `${j.error}\n${JSON.stringify(j.raw ?? {}, null, 1)}` : `실패 (${r.status})`);
  }
  const blob = await r.blob();
  const sampleRate = Number(r.headers.get("X-Sample-Rate") ?? 24000);
  const bytes = blob.size - 44;
  return {
    blob,
    sampleRate,
    rateKnown: r.headers.get("X-Rate-From-Mime") === "1",
    sourceMime: r.headers.get("X-Source-Mime") ?? "",
    seconds: bytes > 0 ? bytes / 2 / sampleRate : 0,
  };
}

/** 대본에서 화자 이름을 뽑는다 ("MSL: ..." → MSL). multiSpeaker 는 2명까지. */
export function speakersInScript(script: string): string[] {
  const seen: string[] = [];
  for (const line of script.split("\n")) {
    const m = /^\s*([^\s:]{1,16})\s*:/.exec(line);
    if (m && !seen.includes(m[1])) seen.push(m[1]);
  }
  return seen;
}
