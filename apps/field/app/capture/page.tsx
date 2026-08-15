"use client";

/**
 * 면담 기록 — 동의 확인 → (녹음/텍스트) → 구조화 후보 → 승인 (docs/01 §5)
 * [스캐폴딩] 입력 폼은 form-config에서 실시간 렌더 (하드코딩 금지 — v0.2 전환 데모가 여기서 터진다).
 * 수집 파이프라인(전사·AE 분기·마스킹·추출)은 stub — 8/25 [오너: 소정·인혁].
 */

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";

type Option = { value: string; labelKo: string; labelScope?: string; isNew?: boolean };
type Field =
  | { key: string; labelKo: string; type: "select"; required: boolean; options: Option[] }
  | { key: "checklist"; type: "checklist"; items: { labelKo: string }[] };

type FormConfig = { contractVersion: string; fields: Field[] };

export default function CapturePage() {
  const [form, setForm] = useState<FormConfig | null>(null);
  const [consent, setConsent] = useState(false);
  const [text, setText] = useState("");
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    api<FormConfig>("/field/form-config", { role: "MEDICAL_AFFAIRS" })
      .then(setForm)
      .catch((e) => setNotice(e.message));
  }, []);

  async function submit() {
    setNotice(null);
    try {
      await api("/field/interactions", {
        method: "POST",
        role: "MEDICAL_AFFAIRS",
        body: JSON.stringify({ rawText: text, consentConfirmed: consent }),
      });
    } catch (e) {
      if (e instanceof ApiError && e.code === "NOT_IMPLEMENTED") {
        setNotice(`배선은 연결됨 — ${e.message}`);
      } else {
        setNotice(e instanceof Error ? e.message : String(e));
      }
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <p className="text-[10px] font-bold tracking-widest text-orange-deep">FIELD · CAPTURE</p>
        <h1 className="mt-0.5 text-xl font-extrabold tracking-tight text-navy">면담 기록</h1>
      </div>

      {/* ① 동의 확인 — VOICE는 동의 없이 저장 거부 (docs/02 §1) */}
      <label className="flex items-start gap-2 rounded-2xl border border-line bg-card p-4 text-xs">
        <input
          type="checkbox"
          checked={consent}
          onChange={(e) => setConsent(e.target.checked)}
          className="mt-0.5 accent-[#EF8B1C]"
        />
        <span>
          <b className="text-navy">기록 동의를 확인했습니다.</b>
          <br />
          <span className="text-muted">녹음·전사는 동의가 전제 — 동의 없으면 저장이 거부된다.</span>
        </span>
      </label>

      {/* ② 입력 — 음성 전사(Web Speech ko-KR)는 P1, 지금은 텍스트만 */}
      <div className="rounded-2xl border border-line bg-card p-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold text-navy">면담 내용</h2>
          <button
            disabled
            className="rounded-full bg-paper px-3 py-1 text-[10px] font-bold text-muted"
            title="음성 전사는 P1 — 8/30 [오너: 소정]"
          >
            🎙 음성 전사 (8/30)
          </button>
        </div>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={5}
          placeholder="면담 메모를 입력하면 AI가 구조화 후보 카드를 만든다 (한국어 OK — 영문 원석과 같은 집계로 합산)"
          className="mt-2 w-full rounded-lg border border-line bg-paper p-3 text-sm outline-none focus:border-orange"
        />
      </div>

      {/* ③ 구조화 항목 미리보기 — form-config가 만든 동적 폼 */}
      {form && (
        <div className="rounded-2xl border border-line bg-card p-4">
          <h2 className="text-sm font-bold text-navy">
            구조화 항목 <span className="text-[10px] font-semibold text-muted">Contract v{form.contractVersion} 실시간 생성</span>
          </h2>
          <div className="mt-2 space-y-2">
            {form.fields
              .filter((f): f is Extract<Field, { type: "select" }> => f.type === "select")
              .map((f) => (
                <div key={f.key}>
                  <label className="text-[11px] font-bold text-muted">
                    {f.labelKo}
                    {f.required && <span className="text-orange-deep"> *</span>}
                  </label>
                  <select className="mt-0.5 w-full rounded-lg border border-line bg-paper px-2 py-1.5 text-xs">
                    <option value="">선택…</option>
                    {f.options.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.labelKo}
                        {o.labelScope === "OUT_OF_LABEL" ? " (허가 범위 밖)" : ""}
                        {o.isNew ? " · NEW" : ""}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
          </div>
        </div>
      )}

      <button
        onClick={submit}
        disabled={!consent || text.length < 5}
        className="w-full rounded-xl bg-navy py-3 text-sm font-bold text-white disabled:opacity-40"
      >
        구조화 후보 만들기
      </button>
      {notice && (
        <p className="rounded-lg bg-orange-soft px-3 py-2 text-[11px] leading-relaxed text-orange-deep">
          {notice}
        </p>
      )}
    </div>
  );
}
