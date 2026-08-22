/** Deepgram 실시간 STT — WebSocket 직결.
 *
 * 근거 (deepgram-api-specs asyncapi.yml + Listen streaming reference):
 *   - 브라우저 인증: 커스텀 헤더를 못 쓰므로 Sec-WebSocket-Protocol 사용 → new WebSocket(url, ["token", key])
 *   - diarize 는 Deprecated → diarize_model=v1|latest (이것만 주면 diarize=true 불필요, v2는 스트리밍 미지원)
 *   - keyterm: Nova-3 전용. 파라미터 반복으로 여러 개. 가중치 미지원(붙이면 조용히 무시됨).
 *     한도 500 tokens/요청 — 문서 권고는 "중요한 20~50개"
 *   - 모델별 언어: nova-3 = ko 지원 / nova-3-medical = ko 미지원 (영어 전용으로 쓴다)
 *   - KeepAlive: {"type":"KeepAlive"} / 종료: {"type":"CloseStream"}
 */
import type { SttEvents, SttOptions, SttProvider, SttSession } from "./types";

const DEFAULT_ENDPOINT = "wss://api.deepgram.com/v1/listen";
const KEEPALIVE_MS = 8000;

type DgWord = { word?: string; punctuated_word?: string; speaker?: number };

export const deepgram: SttProvider = {
  id: "deepgram",
  label: "Deepgram",
  defaultEndpoint: DEFAULT_ENDPOINT,
  models: [
    { value: "nova-3-medical", label: "nova-3-medical", note: "의료 특화 · 영어만 (ko 미지원)" },
    { value: "nova-3", label: "nova-3", note: "한국어 지원 · 의료 특화 없음" },
  ],
  notes: [
    "스펙 확인: diarize_model=v1 · keyterm 500 tokens · Sec-WebSocket-Protocol 브라우저 인증",
    "nova-3-medical 은 한국어 미지원 — 한국어 탭에서는 nova-3 을 쓴다",
    "keyterm 은 Nova-3 계열 전용",
  ],

  async connect(opts: SttOptions, ev: SttEvents): Promise<SttSession> {
    const q = new URLSearchParams({
      model: opts.model,
      encoding: "linear16",
      sample_rate: String(opts.sampleRate),
      channels: "1",
      interim_results: "true",
      punctuate: "true",
      smart_format: "true",
      // 첫 언어만 보낸다 — Deepgram 은 문장 중간 혼용 파라미터가 없다
      language: opts.languages[0] ?? "en",
    });
    if (opts.diarize) q.set("diarize_model", "v1");
    // keyterm 은 반복 파라미터. 여러 단어 구는 공백을 그대로 두면 URLSearchParams가 인코딩한다
    for (const t of opts.boostTerms) q.append("keyterm", t);

    const url = `${opts.endpoint || DEFAULT_ENDPOINT}?${q.toString()}`;
    const ws = new WebSocket(url, ["token", opts.apiKey]);
    ws.binaryType = "arraybuffer";

    let keepalive: ReturnType<typeof setInterval> | null = null;

    ws.onmessage = (e) => {
      if (typeof e.data !== "string") return;
      let msg: Record<string, unknown>;
      try {
        msg = JSON.parse(e.data);
      } catch {
        return;
      }
      ev.onRaw(msg);
      if (msg.type !== "Results") return;

      const channel = msg.channel as { alternatives?: { transcript?: string; words?: DgWord[] }[] };
      const alt = channel?.alternatives?.[0];
      if (!alt?.transcript) return;
      const isFinal = msg.is_final === true;
      const words = alt.words ?? [];

      if (!words.length || words[0].speaker === undefined) {
        ev.onSegment({ speaker: "0", text: alt.transcript, isFinal });
        return;
      }
      // 같은 speaker 의 연속 단어를 한 세그먼트로 합친다
      let cur = String(words[0].speaker);
      let buf: string[] = [];
      const flush = () => {
        if (buf.length) ev.onSegment({ speaker: cur, text: buf.join(" "), isFinal });
        buf = [];
      };
      for (const w of words) {
        const sp = String(w.speaker ?? 0);
        if (sp !== cur) {
          flush();
          cur = sp;
        }
        buf.push(w.punctuated_word ?? w.word ?? "");
      }
      flush();
    };

    ws.onerror = () => ev.onError(new Error("Deepgram WebSocket 오류 — API 키·모델·언어 조합을 확인하세요"));
    ws.onclose = (e) => {
      // 연결 실패의 유일한 단서가 close code 다 — 1006=핸드셰이크 거부(키·네트워크), 1008/1011=서버 거부
      ev.onRaw({ _close: { code: e.code, reason: e.reason || "(없음)", wasClean: e.wasClean } });
      if (keepalive) clearInterval(keepalive);
      ev.onClose?.();
    };

    await new Promise<void>((resolve, reject) => {
      const t = setTimeout(() => reject(new Error("Deepgram 연결 시간 초과")), 10000);
      ws.addEventListener("open", () => { clearTimeout(t); resolve(); }, { once: true });
      ws.addEventListener("error", () => { clearTimeout(t); reject(new Error("Deepgram 연결 실패 — 원시 응답의 _close.code 확인 (1006이면 키 거부·네트워크 차단 가능성)")); }, { once: true });
    });
    ev.onOpen?.();
    keepalive = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "KeepAlive" }));
    }, KEEPALIVE_MS);

    return {
      send: (pcm) => { if (ws.readyState === WebSocket.OPEN) ws.send(pcm.buffer as ArrayBuffer); },
      finish: () => { if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "CloseStream" })); },
      close: () => { if (keepalive) clearInterval(keepalive); ws.close(); },
    };
  },
};
