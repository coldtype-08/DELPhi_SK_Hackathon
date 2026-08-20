/** Gladia 실시간 STT — 2단계: POST /v2/live 로 세션 생성 → 반환된 ws URL 에 접속.
 *
 * 근거 (docs.gladia.io OpenAPI POST /v2/live + asyncapi.yaml):
 *   - model 은 solaria-1 하나
 *   - language_config: { languages: ["ko"], code_switching: bool }
 *     code_switching 설명은 "발화(utterance) 단위 언어 자동 감지"이고, languages 를 하나만
 *     지정하면 무시된다 → 문장 중간 혼용은 이 파라미터의 목적이 아니다
 *   - realtime_processing: custom_vocabulary + custom_vocabulary_config.vocabulary
 *   - 오디오는 바이너리 프레임 가능, 종료는 {"type":"stop_recording"}
 *   - 응답: {"type":"transcript", data:{ is_final, utterance:{ text, speaker? } }}
 *   - init 응답의 url 에 임시 토큰이 박혀 온다 (키를 클라이언트에 노출하지 않는 설계)
 *
 * [실측 대상] 정본 스펙 두 곳(요청 OpenAPI · 응답 asyncapi Utterance)에 화자분리가 없다.
 * 반면 live-stt/recommended-parameters 산문과 SDK 응답 타입에는 speaker 가 등장한다.
 * 그래서 diarize=true 일 때 diarization 을 실제로 보내본다 — 422 면 미지원 확정,
 * 201 이면 지원. 결과는 화면의 "원시 응답"에 그대로 뜬다.
 */
import type { SttEvents, SttOptions, SttProvider, SttSession } from "./types";

const DEFAULT_ENDPOINT = "https://api.gladia.io/v2/live";

export const gladia: SttProvider = {
  id: "gladia",
  label: "Gladia",
  defaultEndpoint: DEFAULT_ENDPOINT,
  models: [{ value: "solaria-1", label: "solaria-1", note: "스펙 enum에 이 모델 하나" }],
  notes: [
    "스펙 확인: custom_vocabulary · code_switching · 임시 토큰이 박힌 ws URL",
    "실측 대상: 실시간 화자분리 — 정본 스펙에 없음. diarization 을 보내서 422/201 로 판정",
    "리전 us-west · eu-west 뿐 (아시아 없음 → 한국에서 지연 불리)",
  ],

  async connect(opts: SttOptions, ev: SttEvents): Promise<SttSession> {
    const body: Record<string, unknown> = {
      encoding: "wav/pcm",
      bit_depth: 16,
      sample_rate: opts.sampleRate,
      channels: 1,
      model: opts.model,
      language_config: {
        languages: opts.languages,
        code_switching: opts.languages.length > 1,
      },
      messages_config: {
        receive_partial_transcripts: true,
        receive_final_transcripts: true,
      },
    };
    if (opts.boostTerms.length) {
      body.realtime_processing = {
        custom_vocabulary: true,
        custom_vocabulary_config: { vocabulary: opts.boostTerms, default_intensity: 0.5 },
      };
    }
    // 정본 스펙에 없는 파라미터를 일부러 보낸다 (지원 여부 실측)
    if (opts.diarize) body.diarization = true;

    const res = await fetch(opts.endpoint || DEFAULT_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-gladia-key": opts.apiKey },
      body: JSON.stringify(body),
    });
    const init = await res.json().catch(() => null);
    ev.onRaw({ _initRequest: body, _initStatus: res.status, _initResponse: init });
    if (!res.ok) {
      throw new Error(
        `Gladia 세션 생성 실패 (${res.status}) — ${init?.message ?? "응답 본문 없음"}` +
          (res.status === 422 && opts.diarize
            ? " · diarization 파라미터가 거부됐다면 실시간 화자분리 미지원이 확정됩니다"
            : ""),
      );
    }

    const ws = new WebSocket(init.url as string);
    ws.binaryType = "arraybuffer";

    ws.onmessage = (e) => {
      if (typeof e.data !== "string") return;
      let msg: Record<string, unknown>;
      try {
        msg = JSON.parse(e.data);
      } catch {
        return;
      }
      ev.onRaw(msg);
      if (msg.type !== "transcript") return;
      const data = msg.data as { is_final?: boolean; utterance?: { text?: string; speaker?: number } };
      const u = data?.utterance;
      if (!u?.text) return;
      ev.onSegment({
        speaker: u.speaker == null ? "0" : String(u.speaker),
        text: u.text,
        isFinal: data.is_final === true,
      });
    };

    ws.onerror = () => ev.onError(new Error("Gladia WebSocket 오류"));
    ws.onclose = () => ev.onClose?.();

    await new Promise<void>((resolve, reject) => {
      const t = setTimeout(() => reject(new Error("Gladia 연결 시간 초과")), 10000);
      ws.addEventListener("open", () => { clearTimeout(t); resolve(); }, { once: true });
      ws.addEventListener("error", () => { clearTimeout(t); reject(new Error("Gladia 연결 실패")); }, { once: true });
    });
    ev.onOpen?.();

    return {
      send: (pcm) => { if (ws.readyState === WebSocket.OPEN) ws.send(pcm.buffer as ArrayBuffer); },
      finish: () => { if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "stop_recording" })); },
      close: () => ws.close(),
    };
  },
};
