/** STT provider 공통 인터페이스 — 이 폴더가 이식 대상이다 (비교 끝나면 apps/field/lib/stt/ 로 복사). */

export type ProviderId = "soniox" | "gladia" | "deepgram";

/** 화자 라벨은 벤더 원시값("0"/"1")을 그대로 보존한다. MSL/HCP 매핑은 수집 화면의 책임. */
export type Segment = {
  speaker: string;
  text: string;
  isFinal: boolean;
};

export type SttOptions = {
  apiKey: string;
  model: string;
  /** ISO 639-1. ["ko"] · ["en"] · ["ko","en"](혼용) */
  languages: string[];
  /** keyword boosting 용어 — vocab_terms의 surface_form을 쓴다 (docs/02 §3) */
  boostTerms: string[];
  diarize: boolean;
  /** 16000 고정 — 벤더 3종 모두 허용값 (Gladia 스펙 기본값) */
  sampleRate: number;
  /** 문서에서 확정 못 한 엔드포인트를 화면에서 교정할 수 있게 열어둔다 */
  endpoint?: string;
};

export type SttEvents = {
  onSegment: (s: Segment) => void;
  onRaw: (json: unknown) => void;
  onError: (e: Error) => void;
  onOpen?: () => void;
  onClose?: () => void;
};

export type SttSession = {
  /** 16kHz mono PCM16 청크 */
  send: (pcm: Int16Array) => void;
  /** 입력 종료 신호 (벤더별 메시지) */
  finish: () => void;
  close: () => void;
};

export type SttProvider = {
  id: ProviderId;
  label: string;
  /** 기본 엔드포인트 — 화면에서 덮어쓸 수 있다 */
  defaultEndpoint: string;
  models: { value: string; label: string; note?: string }[];
  /** 화면에 그대로 표시하는 확인 상태 메모 */
  notes: string[];
  connect: (opts: SttOptions, ev: SttEvents) => Promise<SttSession>;
};
