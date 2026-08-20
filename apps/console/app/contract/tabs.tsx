import Link from "next/link";

/** /contract 하위 화면 공용 탭 — 활성 스키마 ↔ 유래(Provenance) */
export default function ContractTabs({ active }: { active: "schema" | "provenance" }) {
  const base = "rounded-full px-4 py-1.5 text-[13px] font-bold transition-colors";
  const on = "bg-navy text-white";
  const off = "text-muted hover:bg-sky-soft hover:text-navy";
  return (
    <div className="mt-4 inline-flex gap-1 rounded-full border border-line bg-card p-1">
      <Link href="/contract" className={`${base} ${active === "schema" ? on : off}`}>
        활성 스키마
      </Link>
      <Link href="/contract/provenance" className={`${base} ${active === "provenance" ? on : off}`}>
        유래 — 어디서 왔는가
      </Link>
    </div>
  );
}
