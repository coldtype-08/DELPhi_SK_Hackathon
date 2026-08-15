import { api } from "@/lib/api";

type Hyp = {
  id: string;
  titleKo: string;
  kind: "IN_LABEL" | "DEVELOPMENT";
  status: string;
  patientSegment: string;
  commercialActionBlocked: boolean;
  notBoardReadyReason: string | null;
};

export const dynamic = "force-dynamic";

export default async function HypothesesPage() {
  let hyps: Hyp[] = [];
  let error: string | null = null;
  try {
    hyps = await api<Hyp[]>("/hypotheses");
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <div className="mx-auto max-w-5xl">
      <p className="text-xs font-bold tracking-widest text-orange-deep">SCREEN · BOARD</p>
      <h1 className="mt-1 text-2xl font-extrabold tracking-tight text-navy">가설 보드</h1>
      <p className="mt-1 text-sm text-muted">
        In-label과 Development를 나란히 — Development는 상업 액션과 자동 연결되지 않는다 (절대 규칙 #5).
      </p>
      {error && <div className="mt-4 rounded-lg bg-rust-soft px-4 py-2 text-sm text-rust">{error}</div>}

      <div className="mt-6 grid gap-3 md:grid-cols-2">
        {hyps.map((h) => (
          <div key={h.id} className="rounded-2xl border border-line bg-card p-5">
            <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-bold">
              <span className="font-mono text-xs text-muted">{h.id}</span>
              <span
                className={`rounded-full px-2 py-0.5 ${
                  h.kind === "DEVELOPMENT" ? "bg-rust-soft text-rust" : "bg-green-soft text-green"
                }`}
              >
                {h.kind === "DEVELOPMENT" ? "Development · 허가 범위 밖" : "In-label"}
              </span>
              <span className="rounded-full border border-line px-2 py-0.5 text-muted">{h.status}</span>
            </div>
            <h2 className="mt-2 font-bold leading-snug text-navy">{h.titleKo}</h2>
            {h.commercialActionBlocked && (
              <p className="mt-2 rounded-lg bg-rust-soft px-3 py-1.5 text-[11px] font-semibold text-rust">
                상업 액션 차단 — 전문조직 검토 대상으로만 전달 (COMMERCIAL 롤에는 보이지 않음)
              </p>
            )}
            <p className="mt-3 text-[11px] text-muted">
              상세 카드(5단계 구분·근거·에이전트 시각화·회의록)는 8/28~ [오너: 건태] · Screen 실행 8/28
              [인혁] · Board 8/29 [인혁·소정]
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
