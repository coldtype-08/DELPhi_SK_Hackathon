export default function HistoryPage() {
  return (
    <div className="space-y-4">
      <div>
        <p className="text-[10px] font-bold tracking-widest text-orange-deep">FIELD · HISTORY</p>
        <h1 className="mt-0.5 text-xl font-extrabold tracking-tight text-navy">내 기록</h1>
      </div>
      <div className="rounded-2xl border border-dashed border-line bg-card p-5 text-xs leading-relaxed text-muted">
        승인 완료된 내 interaction 목록이 여기 표시된다 — 수집 파이프라인(8/25)과 함께 구현
        [오너: 소정]. 화면 맵: docs/01 §5.
      </div>
    </div>
  );
}
