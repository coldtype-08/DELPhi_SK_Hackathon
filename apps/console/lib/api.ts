/** 백엔드 호출 단일 경유지 — 응답 모양의 계약은 docs/04. 형태가 다르면 프론트가 아니라 스펙부터 고친다. */

const BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api";

export class ApiError extends Error {
  code: string;
  constructor(code: string, messageKo: string) {
    super(messageKo);
    this.code = code;
  }
}

export async function api<T>(
  path: string,
  init?: RequestInit & { role?: string },
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      // 롤은 시연용 헤더 주입 (docs/04 §0) — 권한 강제는 서버의 책임, 프론트는 필터링하지 않는다
      "X-Delphi-Role": init?.role ?? "CLINICAL_STRATEGY",
      ...init?.headers,
    },
    cache: "no-store",
  });
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    throw new ApiError(body?.error?.code ?? "ERROR", body?.error?.message_ko ?? `API ${res.status}`);
  }
  return body.data as T;
}
