/** provider 레지스트리 — 비교가 끝나면 고른 하나만 남겨 apps/field/lib/stt/ 로 옮긴다. */
import { deepgram } from "./deepgram";
import { gladia } from "./gladia";
import { soniox } from "./soniox";
import type { ProviderId, SttProvider } from "./types";

export const PROVIDERS: SttProvider[] = [soniox, gladia, deepgram];

export function providerById(id: ProviderId): SttProvider {
  const p = PROVIDERS.find((x) => x.id === id);
  if (!p) throw new Error(`알 수 없는 provider: ${id}`);
  return p;
}

export * from "./types";
export * from "./audio";
export * from "./scoring";
