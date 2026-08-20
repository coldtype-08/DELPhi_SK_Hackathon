import { api } from "@/lib/api";
import ContractTabs from "./tabs";

type Contract = {
  version: string;
  product: string;
  fields: Record<
    string,
    {
      labelKo: string;
      required: boolean;
      values: { value: string; labelKo: string; labelScope?: string; isNew?: boolean }[];
    }
  >;
};

export const dynamic = "force-dynamic";

export default async function ContractPage() {
  let contract: Contract | null = null;
  let error: string | null = null;
  try {
    contract = await api<Contract>("/contract/active");
  } catch (e) {
    error = e instanceof Error ? e.message : String(e);
  }

  return (
    <div className="mx-auto max-w-4xl">
      <p className="text-xs font-bold tracking-widest text-orange-deep">DATA CONTRACT</p>
      <h1 className="mt-1 text-2xl font-extrabold tracking-tight text-navy">
        활성 스키마 {contract && <span className="text-orange-deep">v{contract.version}</span>}
      </h1>
      <p className="mt-1 text-sm text-muted">
        추출·검증·DB·Field 폼·필터·에이전트 여섯 곳이 이 정의 하나를 공유한다. AI는 이걸 바꿀 수 없고,
        변경은 SCP → Steward 승인으로만 (절대 규칙 #4).
      </p>
      <ContractTabs active="schema" />
      {error && <div className="mt-4 rounded-lg bg-rust-soft px-4 py-2 text-sm text-rust">{error}</div>}

      {contract && (
        <div className="mt-6 space-y-4">
          {Object.entries(contract.fields).map(([key, f]) => (
            <div key={key} className="rounded-2xl border border-line bg-card p-5">
              <div className="flex items-baseline gap-2">
                <code className="text-sm font-bold text-navy">{key}</code>
                <span className="text-xs text-muted">{f.labelKo}</span>
                {f.required && (
                  <span className="rounded-full bg-orange-soft px-2 py-0.5 text-[10px] font-bold text-orange-deep">
                    필수
                  </span>
                )}
              </div>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {f.values.map((v) => (
                  <span
                    key={v.value}
                    className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${
                      v.labelScope === "OUT_OF_LABEL"
                        ? "border-rust-soft bg-rust-soft text-rust"
                        : "border-line bg-paper text-ink"
                    }`}
                    title={v.labelKo}
                  >
                    {v.value}
                    {v.labelScope === "OUT_OF_LABEL" && " · 허가 밖"}
                    {v.isNew && " · NEW"}
                  </span>
                ))}
              </div>
            </div>
          ))}
          <div className="rounded-2xl border border-dashed border-line bg-card p-5 text-sm text-muted">
            <b className="text-navy">Schema Change Proposal</b> — 지금은 비어 있다.{" "}
            <code className="text-xs">patient_segment</code>에 POST_STROKE가 <b>일부러 없고</b>, 코퍼스에
            반복 등장한다 → 추출이 돌기 시작하면 SCP가 여기 쌓이고, 승인하면 v0.2가 발행되어 Field 폼이
            바뀐다 (데모 ⑥). SCP 목록·승인 UI는 8/31 [오너: 건태], 승인→발행 로직 8/30 [인혁].
          </div>
        </div>
      )}
    </div>
  );
}
