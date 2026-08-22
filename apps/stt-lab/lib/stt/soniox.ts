/** Soniox 실시간 STT — WebSocket 직결. 첫 메시지에 config(JSON), 이후 오디오 바이너리 프레임.
 *
 * 근거: soniox-python SDK `types/realtime.py` RealtimeSTTConfig 필드
 *   model · audio_format · num_channels · sample_rate · language_hints · language_hints_strict
 *   context · enable_speaker_diarization · enable_language_identification · enable_endpoint_detection
 * 임시 API 키: POST /auth/temporary-api-key (usage_type="transcribe_websocket"). 랩에서는 키 직접 입력.
 *
 * [확인] WebSocket 경로와 audio_format — soniox-python SDK 소스에서 직접 확인 (08/22):
 *   src/soniox/client.py:39  _DEFAULT_WEBSOCKET_BASE_URL = "wss://stt-rt.soniox.com/transcribe-websocket"
 *   src/soniox/types/*.py    audio_format 리터럴에 "pcm_s16le" 존재
 */
import type { SttEvents, SttOptions, SttProvider, SttSession } from "./types";

const DEFAULT_ENDPOINT = "wss://stt-rt.soniox.com/transcribe-websocket";
const AUDIO_FORMAT = "pcm_s16le";

type SonioxToken = {
  text?: string;
  is_final?: boolean;
  speaker?: number | string | null;
};

export const soniox: SttProvider = {
  id: "soniox",
  label: "Soniox",
  defaultEndpoint: DEFAULT_ENDPOINT,
  models: [{ value: "stt-rt-v5", label: "stt-rt-v5", note: "실시간 STT" }],
  notes: [
    "SDK 확인: WS 경로 · pcm_s16le · enable_speaker_diarization · language_hints · context.terms · 임시 API 키",
    "리전에 일본 있음 (한국에서 지연 유리)",
  ],

  async connect(opts: SttOptions, ev: SttEvents): Promise<SttSession> {
    const ws = new WebSocket(opts.endpoint || DEFAULT_ENDPOINT);
    ws.binaryType = "arraybuffer";

    const finalBySpeaker: string[] = [];

    ws.onopen = () => {
      ws.send(
        JSON.stringify({
          api_key: opts.apiKey,
          model: opts.model,
          audio_format: AUDIO_FORMAT,
          num_channels: 1,
          sample_rate: opts.sampleRate,
          language_hints: opts.languages,
          enable_speaker_diarization: opts.diarize,
          enable_language_identification: opts.languages.length > 1,
          // context.general 은 [{key,value}] 목록이 규격 — SDK가 dict 입력을 이 형태로
          // 변환해 보낸다(types/api.py _coerce_general). dict 그대로 보내면 서버가
          // "Start request is malformed" 로 거부한다 (08/22 실측).
          ...(opts.boostTerms.length
            ? { context: { terms: opts.boostTerms, general: [{ key: "domain", value: "Healthcare" }] } }
            : {}),
        }),
      );
      ev.onOpen?.();
    };

    ws.onmessage = (e) => {
      if (typeof e.data !== "string") return;
      let msg: Record<string, unknown>;
      try {
        msg = JSON.parse(e.data);
      } catch {
        return;
      }
      ev.onRaw(msg);

      if (msg.error_message || msg.error_type) {
        ev.onError(new Error(String(msg.error_message ?? msg.error_type)));
        return;
      }

      const tokens = (msg.tokens as SonioxToken[] | undefined) ?? [];
      // 같은 화자의 연속 토큰을 한 세그먼트로 합친다
      let curSpeaker = "";
      let curText = "";
      let curFinal = true;
      const flush = () => {
        if (!curText) return;
        if (curFinal) finalBySpeaker.push(curText);
        ev.onSegment({ speaker: curSpeaker || "0", text: curText, isFinal: curFinal });
        curText = "";
      };
      for (const t of tokens) {
        const sp = t.speaker == null ? "0" : String(t.speaker);
        const fin = t.is_final !== false;
        if (sp !== curSpeaker || fin !== curFinal) {
          flush();
          curSpeaker = sp;
          curFinal = fin;
        }
        curText += t.text ?? "";
      }
      flush();
    };

    ws.onerror = () => ev.onError(new Error("Soniox WebSocket 오류 — 엔드포인트·API 키를 확인하세요"));
    ws.onclose = (e) => {
      ev.onRaw({ _close: { code: e.code, reason: e.reason || "(없음)", wasClean: e.wasClean } });
      ev.onClose?.();
    };

    await new Promise<void>((resolve, reject) => {
      const t = setTimeout(() => reject(new Error("Soniox 연결 시간 초과")), 10000);
      ws.addEventListener("open", () => { clearTimeout(t); resolve(); }, { once: true });
      ws.addEventListener("error", () => { clearTimeout(t); reject(new Error("Soniox 연결 실패")); }, { once: true });
    });

    return {
      send: (pcm) => { if (ws.readyState === WebSocket.OPEN) ws.send(pcm.buffer as ArrayBuffer); },
      // 빈 문자열 메시지가 Soniox의 입력 종료 신호다
      finish: () => { if (ws.readyState === WebSocket.OPEN) ws.send(""); },
      close: () => ws.close(),
    };
  },
};
