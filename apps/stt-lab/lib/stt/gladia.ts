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
 * [실측 완료 08/22] diarization 을 보내면 400 "Invalid parameter(s)" — SDK 타입
 * (LiveV2InitRequest, gladiaio-sdk 1.0.5)에도 그 필드가 없다.
 * → **Gladia 실시간 화자분리 미지원 확정.**
 * 화자 분리를 켜고 실행하면 ① diarization 포함으로 1차 시도(증거를 원시 응답에 남김)
 * ② 거부되면 diarization 없이 재시도 — 전사 비교 자체는 계속 진행되게 한다.
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
    "실측 완료(08/22): 화자분리 파라미터가 400 으로 거부됨 — 실시간 화자분리 미지원 확정",
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
    const initOnce = async (b: Record<string, unknown>) => {
      const res = await fetch(opts.endpoint || DEFAULT_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json", "x-gladia-key": opts.apiKey },
        body: JSON.stringify(b),
      });
      const json = await res.json().catch(() => null);
      ev.onRaw({ _initRequest: b, _initStatus: res.status, _initResponse: json });
      return { res, json };
    };

    // 화자 분리 요청 시: 스펙에 없는 diarization 을 1차로 보내 증거를 남기고(400/422 = 미지원),
    // 거부되면 빼고 재시도해 전사 비교는 계속 진행한다.
    let { res, json: init } = opts.diarize
      ? await initOnce({ ...body, diarization: true })
      : await initOnce(body);
    if (!res.ok && opts.diarize && (res.status === 400 || res.status === 422)) {
      ev.onRaw({ _note: "diarization 거부됨 → 실시간 화자분리 미지원 확정. diarization 없이 재시도" });
      ({ res, json: init } = await initOnce(body));
    }
    if (!res.ok) {
      const detail = init?.validation_errors ? ` · ${JSON.stringify(init.validation_errors)}` : "";
      throw new Error(`Gladia 세션 생성 실패 (${res.status}) — ${init?.message ?? "응답 본문 없음"}${detail}`);
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
