import type { Metadata } from "next";
import ContractTabs from "../tabs";
import ProvenanceView from "./provenance-view";

export const metadata: Metadata = {
  title: "Contract 유래 — DELPHi Console",
  description: "Data Contract v0.1의 모든 필드가 어느 원문에서 왔고, 누가 왜 채택·제외·보류했는지의 기록",
};

export default function ProvenancePage() {
  return (
    <div className="mx-auto max-w-6xl">
      <p className="text-xs font-bold tracking-widest text-orange-deep">DATA CONTRACT · PROVENANCE</p>
      <h1 className="mt-1 text-2xl font-extrabold tracking-tight text-navy">이 스키마는 어디서 왔는가</h1>
      <p className="mt-1 max-w-3xl text-sm text-muted">
        claim만이 아니라 스키마의 필드·허용값에도 원문 근거가 있다. v0.1을 모르는 격리 AI가 코퍼스 표본만 읽고
        구조를 제안했고, 사람이 원문과 대조해 판정했으며, 채택뿐 아니라 제외와 보류의 사유까지 기록되어 있다. 이
        화면은 그 기록을 그대로 렌더링한다.
      </p>
      <ContractTabs active="provenance" />
      <div className="mt-5">
        <ProvenanceView />
      </div>
    </div>
  );
}
