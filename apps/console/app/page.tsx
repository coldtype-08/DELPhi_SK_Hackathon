import Link from "next/link";
import { api } from "@/lib/api";

type Kpis = {
  computedBy: string;
  asOf: string;
  approvedClaims: number;
  distinctHcp: number;
  openHypotheses: number;
  pendingReviews: number;
};

export const dynamic = "force-dynamic";

export default async function Home() {
  let kpis: Kpis | null = null;
  let error: string | null = null;
  try {
    kpis = await api<Kpis>("/aggregates/kpis");
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <div className="mx-auto max-w-5xl">
      <p className="text-xs font-bold tracking-widest text-orange-deep">DELPHI CONSOLE</p>
      <h1 className="mt-1 text-2xl font-extrabold tracking-tight text-navy">홈 대시보드</h1>
      <p className="mt-1 text-sm text-muted">
        승인된 데이터만 숫자가 된다 — 모든 수치는 SQL 계산 (절대 규칙 #1·#3).
      </p>

      {error ? (
        <div className="mt-8 rounded-xl border border-line bg-rust-soft p-5 text-sm">
          <b className="text-rust">백엔드에 연결할 수 없습니다.</b>
          <pre className="mt-2 rounded bg-card p-3 text-xs">
            cd backend && uv run uvicorn app.main:app --reload{"\n"}
            (최초 1회: uv run --project backend python scripts/seed_db.py)
          </pre>
        </div>
      ) : (
        kpis && (
          <>
            <div className="mt-8 grid grid-cols-2 gap-3 lg:grid-cols-4">
              {[
                { label: "승인 데이터", value: kpis.approvedClaims, href: "/review" },
                { label: "독립 HCP", value: kpis.distinctHcp, href: "/review" },
                { label: "열린 가설", value: kpis.openHypotheses, href: "/hypotheses" },
                { label: "검토 대기", value: kpis.pendingReviews, href: "/review" },
              ].map((k) => (
                <Link
                  key={k.label}
                  href={k.href}
                  className="rounded-2xl border border-line bg-card p-5 shadow-[0_1px_2px_rgba(22,38,97,.04)] transition-shadow hover:shadow-md"
                >
                  <div className="text-4xl font-extrabold tabular-nums tracking-tight text-navy">
                    {k.value}
                  </div>
                  <div className="mt-1 text-xs font-bold text-muted">{k.label}</div>
                </Link>
              ))}
            </div>
            <p className="mt-2 text-right text-[11px] text-muted">
              computedBy: {kpis.computedBy} · asOf {new Date(kpis.asOf).toLocaleString("ko-KR")}
            </p>
          </>
        )
      )}

      <div className="mt-8 grid gap-3 md:grid-cols-2">
        <div className="rounded-2xl border border-dashed border-line bg-card p-5 text-sm text-muted">
          <b className="text-navy">파이프라인 상태 보드</b> — RAW → CANDIDATE → APPROVED 카운트 스트립.
          <br />08/14 채택 (P1) · 자리만 잡아둠 [오너: 건태 8/24]
        </div>
        <div className="rounded-2xl border border-dashed border-line bg-card p-5 text-sm text-muted">
          <b className="text-navy">신호 추이 차트</b> — 월별 집계는 API가 이미 반환 중
          (<code className="text-xs">/aggregates/signals</code>) [오너: 건태 8/24]
        </div>
      </div>
    </div>
  );
}
