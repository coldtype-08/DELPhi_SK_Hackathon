import { api } from "@/lib/api";

type Cand = { id: string; interactionId: string; verbatimQuote: string; routedAt: string; status: string };

export const dynamic = "force-dynamic";

export default async function SafetyPage() {
  let cands: Cand[] = [];
  let error: string | null = null;
  try {
    // 이 화면만 SAFETY 롤로 조회 — 다른 롤은 서버가 403으로 막는 것이 정상 동작 (절대 규칙 #6)
    cands = await api<Cand[]>("/safety/candidates", { role: "SAFETY" });
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <div className="mx-auto max-w-4xl">
      <p className="text-xs font-bold tracking-widest text-orange-deep">SAFETY · 분리 경로</p>
      <h1 className="mt-1 text-2xl font-extrabold tracking-tight text-navy">안전성·차단 로그</h1>
      <p className="mt-1 text-sm text-muted">
        AE 후보는 일반 분석 흐름과 분리 — 집계·가설·Screen은 이 데이터를 읽지 않는다 (절대 규칙 #6).
        이 화면은 SAFETY 롤 헤더로만 조회한다.
      </p>
      {error && <div className="mt-4 rounded-lg bg-rust-soft px-4 py-2 text-sm text-rust">{error}</div>}

      <div className="mt-6 space-y-3">
        {cands.length === 0 && !error && (
          <div className="rounded-2xl border border-dashed border-line bg-card p-5 text-sm text-muted">
            분리된 AE 후보가 아직 없다 — 추출 파이프라인이 SAFETY_CANDIDATE를 이 경로로 보내기 시작하면
            (8/21~ [오너: 인혁]) 여기 쌓인다. 코퍼스에는 S2 신호 5건이 심어져 있다.
          </div>
        )}
        {cands.map((c) => (
          <div key={c.id} className="rounded-2xl border border-line bg-card p-4 text-sm">
            <div className="flex items-center gap-2 text-[10px] font-bold">
              <span className="font-mono text-muted">{c.id}</span>
              <span className="rounded-full bg-rust-soft px-2 py-0.5 text-rust">{c.status}</span>
            </div>
            <p className="mt-2 text-xs text-muted">“{c.verbatimQuote}”</p>
          </div>
        ))}
        <div className="rounded-2xl border border-dashed border-line bg-card p-5 text-sm text-muted">
          <b className="text-navy">Critic 차단 이력</b>(<code className="text-xs">/logs/blocked</code>) —
          코퍼스에 차단용 문장 2건(X1·X2)이 심어져 있고, Critic이 막는 장면 자체가 데모 포인트다. 화면은
          8/29~ [오너: 건태].
        </div>
      </div>
    </div>
  );
}
