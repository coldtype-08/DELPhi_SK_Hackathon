/** Gemini TTS 프록시 — 대본을 화자 2명 음성(WAV)으로 만든다. (오너: 인혁)
 *
 * 왜 브라우저에서 직접 부르지 않고 이 라우트를 두는가:
 *   1) CORS — generativelanguage.googleapis.com 의 브라우저 허용 여부가 확실하지 않다
 *   2) Gemini TTS 응답은 **헤더 없는 raw PCM**(mimeType 예: audio/L16;codec=pcm;rate=24000)이라
 *      WAV 헤더를 붙여야 재생·업로드가 된다. 그 변환을 서버에서 한 번에 끝낸다
 * 키는 요청 본문으로 받아 그 요청에만 쓰고 저장하지 않는다 (localhost 안에서만 이동).
 *
 * 근거: google-genai SDK types — SpeechConfig.multi_speaker_voice_config →
 *   MultiSpeakerVoiceConfig.speaker_voice_configs[] → SpeakerVoiceConfig{speaker, voice_config}
 *   → VoiceConfig.prebuilt_voice_config → PrebuiltVoiceConfig.voice_name
 * REST 는 같은 필드의 camelCase 표기를 쓴다.
 */
import { NextResponse } from "next/server";

const BASE = "https://generativelanguage.googleapis.com/v1beta";

type Speaker = { name: string; voice: string };

/** raw PCM16 → WAV. rate 는 응답 mimeType 에서 읽은 값을 쓴다 (하드코딩하지 않는다). */
function pcm16ToWav(pcm: Uint8Array, sampleRate: number, channels = 1): Uint8Array {
  const header = new ArrayBuffer(44);
  const v = new DataView(header);
  const put = (off: number, s: string) => {
    for (let i = 0; i < s.length; i++) v.setUint8(off + i, s.charCodeAt(i));
  };
  const byteRate = sampleRate * channels * 2;
  put(0, "RIFF");
  v.setUint32(4, 36 + pcm.length, true);
  put(8, "WAVE");
  put(12, "fmt ");
  v.setUint32(16, 16, true);
  v.setUint16(20, 1, true);            // PCM
  v.setUint16(22, channels, true);
  v.setUint32(24, sampleRate, true);
  v.setUint32(28, byteRate, true);
  v.setUint16(32, channels * 2, true);
  v.setUint16(34, 16, true);
  put(36, "data");
  v.setUint32(40, pcm.length, true);

  const out = new Uint8Array(44 + pcm.length);
  out.set(new Uint8Array(header), 0);
  out.set(pcm, 44);
  return out;
}

/** "audio/L16;codec=pcm;rate=24000" → 24000. 없으면 24000 가정하되 헤더로 알려준다. */
function rateFromMime(mime: string | undefined): { rate: number; known: boolean } {
  const m = /rate=(\d+)/.exec(mime ?? "");
  return m ? { rate: Number(m[1]), known: true } : { rate: 24000, known: false };
}

export async function POST(req: Request) {
  let body: {
    action?: "models" | "synthesize";
    apiKey?: string;
    model?: string;
    script?: string;
    speakers?: Speaker[];
    stylePrompt?: string;
  };
  try {
    body = await req.json();
  } catch {
    return NextResponse.json({ error: "본문이 JSON 이 아닙니다" }, { status: 400 });
  }

  const apiKey = body.apiKey?.trim();
  if (!apiKey) return NextResponse.json({ error: "Gemini API 키를 입력하세요" }, { status: 400 });

  // 모델 목록 — TTS 가능한 모델 이름을 벤더에서 직접 받아온다 (이름을 추측하지 않기 위해)
  if (body.action === "models") {
    const r = await fetch(`${BASE}/models?pageSize=200&key=${encodeURIComponent(apiKey)}`);
    const j = await r.json().catch(() => null);
    if (!r.ok) {
      return NextResponse.json({ error: `모델 목록 실패 (${r.status})`, raw: j }, { status: r.status });
    }
    type M = { name?: string; supportedGenerationMethods?: string[] };
    const all: M[] = Array.isArray(j?.models) ? j.models : [];
    const names = all
      .map((m) => (m.name ?? "").replace(/^models\//, ""))
      .filter(Boolean);
    return NextResponse.json({ tts: names.filter((n) => n.includes("tts")), all: names });
  }

  const model = body.model?.trim();
  const script = body.script?.trim();
  const speakers = (body.speakers ?? []).filter((s) => s.name?.trim() && s.voice?.trim());
  if (!model) return NextResponse.json({ error: "모델을 지정하세요" }, { status: 400 });
  if (!script) return NextResponse.json({ error: "대본이 비어 있습니다" }, { status: 400 });
  if (speakers.length < 1 || speakers.length > 2) {
    // multiSpeakerVoiceConfig 는 화자 2명까지다. 우리 대본은 MSL/HCP 정확히 2명.
    return NextResponse.json({ error: "화자는 1~2명이어야 합니다" }, { status: 400 });
  }

  const prompt = `${body.stylePrompt?.trim() || "다음 대화를 자연스럽게 읽어라."}\n\n${script}`;

  const payload = {
    contents: [{ parts: [{ text: prompt }] }],
    generationConfig: {
      responseModalities: ["AUDIO"],
      speechConfig: {
        multiSpeakerVoiceConfig: {
          speakerVoiceConfigs: speakers.map((s) => ({
            speaker: s.name.trim(),
            voiceConfig: { prebuiltVoiceConfig: { voiceName: s.voice.trim() } },
          })),
        },
      },
    },
  };

  const r = await fetch(
    `${BASE}/models/${encodeURIComponent(model)}:generateContent?key=${encodeURIComponent(apiKey)}`,
    { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) },
  );
  const j = await r.json().catch(() => null);
  if (!r.ok) {
    // 벤더 오류를 가공하지 않고 그대로 넘긴다 — 모델명·목소리명 오타를 화면에서 바로 읽게
    return NextResponse.json({ error: `Gemini 오류 (${r.status})`, raw: j }, { status: r.status });
  }

  type Part = { inlineData?: { data?: string; mimeType?: string } };
  const parts: Part[] = j?.candidates?.[0]?.content?.parts ?? [];
  const audio = parts.find((p) => p.inlineData?.data)?.inlineData;
  if (!audio?.data) {
    return NextResponse.json({ error: "응답에 오디오가 없습니다", raw: j }, { status: 502 });
  }

  const pcm = Buffer.from(audio.data, "base64");
  const { rate, known } = rateFromMime(audio.mimeType);
  const wav = pcm16ToWav(new Uint8Array(pcm), rate);

  return new NextResponse(new Uint8Array(wav), {
    headers: {
      "Content-Type": "audio/wav",
      "Content-Length": String(wav.length),
      "X-Sample-Rate": String(rate),
      "X-Rate-From-Mime": known ? "1" : "0",
      "X-Source-Mime": audio.mimeType ?? "",
    },
  });
}
