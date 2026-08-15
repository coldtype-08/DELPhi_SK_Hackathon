import Link from "next/link";
import { api } from "@/lib/api";

type Briefing = { checklist: { labelKo: string; origin: string }[] };
type FormConfig = { contractVersion: string; fields: { key: string }[] };

export const dynamic = "force-dynamic";

export default async function TodayPage() {
  let briefing: Briefing | null = null;
  let form: FormConfig | null = null;
  let error: string | null = null;
  try {
    [briefing, form] = await Promise.all([
      api<Briefing>("/field/briefing", { role: "MEDICAL_AFFAIRS" }),
      api<FormConfig>("/field/form-config", { role: "MEDICAL_AFFAIRS" }),
    ]);
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <div className="space-y-4">
      <div>
        <p className="text-[10px] font-bold tracking-widest text-orange-deep">FIELD · 오늘의 면담</p>
        <h1 className="mt-0.5 text-xl font-extrabold tracking-tight text-navy">방문 전 체크리스트</h1>
      </div>

      {error && <div className="rounded-lg bg-rust-soft px-3 py-2 text-xs text-rust">{error}</div>}

      {form && (
        <div className="rounded-2xl border border-line bg-card p-4 text-xs text-muted">
          이 앱의 입력 폼은 <b className="text-navy">Data Contract v{form.contractVersion}</b>에서
          실시간 생성된다 — 하드코딩 없음. Steward가 v0.2를 승인하는 순간 폼이 바뀐다 (데모 ⑥).
        </div>
      )}

      <div className="rounded-2xl border border-line bg-card p-4">
        <h2 className="text-sm font-bold text-navy">Board 승인 후속 질문</h2>
        {briefing && briefing.checklist.length === 0 ? (
          <p className="mt-2 text-xs leading-relaxed text-muted">
            아직 없음 — Board에서 가설이 승인되고 후속 질문이 내려오면 여기 나타난다 (루프가 닫히는
            지점, 데모 ⑦번 체크). 지금은 <Link href="/capture" className="font-bold text-orange-deep">면담 기록</Link>부터.
          </p>
        ) : (
          <ul className="mt-2 space-y-2">
            {briefing?.checklist.map((c, i) => (
              <li key={i} className="flex items-start gap-2 text-xs">
                <span className="mt-0.5 size-3.5 shrink-0 rounded border border-line" />
                <span>
                  {c.labelKo}
                  <span className="ml-1 rounded bg-orange-soft px-1 text-[9px] font-bold text-orange-deep">
                    {c.origin === "BOARD_FOLLOW_UP" ? "Board 승인" : c.origin}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      <p className="text-[10px] leading-relaxed text-muted">
        방문 예정 목록·HCP별 브리핑은 8/24~ [오너: 소정]. 이 셸은 스캐폴딩 — 화면 맵은 docs/01 §5.
      </p>
    </div>
  );
}
