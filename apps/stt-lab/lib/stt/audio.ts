/** 오디오 입력 — 마이크와 WAV 파일 두 경로 모두 16kHz mono PCM16으로 정규화한다. */

export const TARGET_SAMPLE_RATE = 16000;

function floatToPcm16(f32: Float32Array): Int16Array {
  const out = new Int16Array(f32.length);
  for (let i = 0; i < f32.length; i++) {
    const s = Math.max(-1, Math.min(1, f32[i]));
    out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
  }
  return out;
}

/** AudioWorklet 모듈을 별도 public 파일 없이 Blob URL로 싣는다. */
const WORKLET_SRC = `
class PcmTap extends AudioWorkletProcessor {
  process(inputs) {
    const ch = inputs[0][0];
    if (ch) this.port.postMessage(new Float32Array(ch));
    return true;
  }
}
registerProcessor('pcm-tap', PcmTap);
`;

export type MicHandle = { stop: () => void };

/** 마이크 → PCM16 청크. AudioContext가 16kHz로 리샘플한다.
 *  브라우저 전처리(에코 제거·잡음 억제·자동 게인)는 **항상 끈다** —
 *  화상통화용 기능이라 STT에는 원음이 낫고, 켜두면 스피커로 재생한 소리를
 *  에코로 판정해 지워버린다. 그래서 사람 발화든 스피커 재생이든 구분이 필요 없다. */
export async function startMic(onPcm: (pcm: Int16Array) => void): Promise<MicHandle> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: false,
      noiseSuppression: false,
      autoGainControl: false,
    },
  });
  const ctx = new AudioContext({ sampleRate: TARGET_SAMPLE_RATE });
  const url = URL.createObjectURL(new Blob([WORKLET_SRC], { type: "application/javascript" }));
  await ctx.audioWorklet.addModule(url);
  URL.revokeObjectURL(url);

  const src = ctx.createMediaStreamSource(stream);
  const node = new AudioWorkletNode(ctx, "pcm-tap");
  node.port.onmessage = (e) => onPcm(floatToPcm16(e.data as Float32Array));
  src.connect(node);
  // 스피커로 내보내지 않으려면 gain 0으로 destination에 연결해 그래프를 살려둔다
  const mute = ctx.createGain();
  mute.gain.value = 0;
  node.connect(mute).connect(ctx.destination);

  return {
    stop: () => {
      node.port.onmessage = null;
      src.disconnect();
      node.disconnect();
      stream.getTracks().forEach((t) => t.stop());
      void ctx.close();
    },
  };
}

/** WAV(또는 브라우저가 디코딩하는 모든 오디오) 파일 → 16kHz mono PCM16 전체 버퍼. */
export async function fileToPcm16(file: File): Promise<Int16Array> {
  const bytes = await file.arrayBuffer();
  const decodeCtx = new AudioContext();
  const decoded = await decodeCtx.decodeAudioData(bytes);
  void decodeCtx.close();

  // 모노 다운믹스 + 16kHz 리샘플을 OfflineAudioContext에 맡긴다
  const frames = Math.ceil((decoded.duration * TARGET_SAMPLE_RATE));
  const off = new OfflineAudioContext(1, frames, TARGET_SAMPLE_RATE);
  const src = off.createBufferSource();
  src.buffer = decoded;
  src.connect(off.destination);
  src.start();
  const rendered = await off.startRendering();
  return floatToPcm16(rendered.getChannelData(0));
}

/** 전체 PCM을 실시간 속도로 흘려보낸다 (chunkMs 단위). 파일로 3개 provider를 같은 음성으로 비교하기 위한 경로. */
export async function streamPcmRealtime(
  pcm: Int16Array,
  onChunk: (c: Int16Array) => void,
  opts: { chunkMs?: number; shouldStop?: () => boolean } = {},
): Promise<void> {
  const chunkMs = opts.chunkMs ?? 100;
  const per = Math.floor((TARGET_SAMPLE_RATE * chunkMs) / 1000);
  for (let i = 0; i < pcm.length; i += per) {
    if (opts.shouldStop?.()) return;
    onChunk(pcm.subarray(i, Math.min(i + per, pcm.length)));
    await new Promise((r) => setTimeout(r, chunkMs));
  }
}
