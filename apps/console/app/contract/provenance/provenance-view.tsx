"use client";

/**
 * Contract 유래(Provenance) 인터랙티브 뷰 [오너: 건태]
 * ① 반복 매트릭스 → ② 판정의 스키마·DB 반영 → ③ 한 문장 따라가기(원문→집계 파이프라인).
 * 데이터는 lib/provenance.ts — DECISIONS 08/19와 부트스트랩 초안의 결정론적 렌더링이며 LLM 호출이 없다.
 */

import { useState } from "react";
import {
  CONCEPTS,
  DOC_TYPE_KO,
  SAMPLE_DOCS,
  VERDICT_STYLE,
  type Concept,
  type Verdict,
} from "@/lib/provenance";

/* ── 판정 모양 (색 단독 표기 금지 — 색각 대응) ─────────────────────────── */
function Glyph({ v }: { v: Verdict }) {
  const g = VERDICT_STYLE[v].glyph;
  if (g === "x") return <span className="text-[13px] font-black leading-none text-rust">✕</span>;
  if (g === "ring") return <span className="inline-block h-2.5 w-2.5 rounded-full border-2 border-sky" />;
  if (g === "diamond") return <span className="inline-block h-2.5 w-2.5 rotate-45 rounded-[2px] bg-orange" />;
  return <span className="inline-block h-2.5 w-2.5 rounded-full bg-green" />;
}

function VerdictChip({ c }: { c: Concept }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2.5 py-1 text-[11px] font-bold ${VERDICT_STYLE[c.verdict].chipClass}`}
    >
      <Glyph v={c.verdict} />
      {c.chip}
    </span>
  );
}

function SectionLabel({ dotClass, children }: { dotClass: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-2 text-[11px] font-extrabold uppercase tracking-wider text-muted">
      <span className={`h-2 w-2 rounded-full ${dotClass}`} />
      {children}
    </div>
  );
}

/* ── ① 매트릭스 ───────────────────────────────────────────────────────── */
function Matrix({ selected, onSelect }: { selected: string; onSelect: (k: string) => void }) {
  return (
    <div className="rounded-2xl border border-line bg-card">
      <div className="px-5 pt-4">
        <h2 className="text-lg font-extrabold tracking-tight text-navy">반복이 필드를 만든다</h2>
        <p className="text-xs text-muted">개념 군집 × 표본 문서 15건 — 행을 누르면 근거와 판정이 열린다</p>
      </div>
      <div className="overflow-x-auto px-3 pb-2 pt-3">
        <table className="w-full min-w-[700px] border-separate border-spacing-0">
          <thead>
            <tr>
              <th className="min-w-[176px] px-2 pb-1 text-left text-[10px] font-semibold text-muted">
                개념 · 관련 필드
              </th>
              {SAMPLE_DOCS.map((d) => (
                <th key={d.id} className="w-[22px] pb-1 text-center font-mono text-[9.5px] font-semibold text-muted">
                  {d.id}
                  <div className={d.type === "V" ? "rounded bg-orange-soft text-[8.5px] font-bold text-orange-deep" : "text-[8.5px] font-bold text-line"}>
                    {d.type === "V" ? "KO" : d.type}
                  </div>
                </th>
              ))}
              <th className="pb-1 pr-1 text-right text-[10px] font-semibold text-muted">반복</th>
              <th className="pb-1 pr-2 text-right text-[10px] font-semibold text-muted">판정</th>
            </tr>
          </thead>
          <tbody>
            {CONCEPTS.map((c) => {
              const sel = c.key === selected;
              return (
                <tr
                  key={c.key}
                  tabIndex={0}
                  role="button"
                  aria-label={`${c.name} — 근거 보기`}
                  onClick={() => onSelect(c.key)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onSelect(c.key);
                    }
                  }}
                  className={`cursor-pointer transition-colors focus-visible:outline-2 focus-visible:outline-navy ${
                    sel ? "bg-sky-soft" : "hover:bg-paper"
                  }`}
                >
                  <td className="rounded-l-xl border-t border-line px-2 py-2.5">
                    <div className={`text-[13px] font-bold leading-tight ${sel ? "text-navy" : "text-ink"}`}>{c.name}</div>
                    <div className="max-w-[180px] truncate font-mono text-[10px] text-muted">{c.fieldLine}</div>
                  </td>
                  {SAMPLE_DOCS.map((d) => (
                    <td key={d.id} className="border-t border-line text-center">
                      {c.docs.includes(d.id) && (
                        <span className="inline-flex items-center justify-center" title={`DOC-…-${d.id} · ${DOC_TYPE_KO[d.type]}`}>
                          <Glyph v={c.verdict} />
                        </span>
                      )}
                    </td>
                  ))}
                  <td className="whitespace-nowrap border-t border-line pr-1 text-right text-[11px] tabular-nums text-muted">
                    {c.stat}
                  </td>
                  <td className="rounded-r-xl border-t border-line py-2 pr-2 text-right">
                    <VerdictChip c={c} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-line px-5 py-2.5 text-[11px] text-muted">
        <span className="inline-flex items-center gap-1.5"><Glyph v="adopt" /> 채택·검증</span>
        <span className="inline-flex items-center gap-1.5"><Glyph v="exclude" /> 제외</span>
        <span className="inline-flex items-center gap-1.5"><Glyph v="hold" /> 보류→SCP</span>
        <span className="inline-flex items-center gap-1.5"><Glyph v="seed" /> 미달→v0.2 씨앗</span>
        <span className="ml-auto text-[10.5px]">판정의 정본은 라벨 — 색은 보조 표기</span>
      </div>
    </div>
  );
}

/* ── ① 근거 패널 (5단계 구분 문법 재사용) ─────────────────────────────── */
function EvidencePanel({ c }: { c: Concept }) {
  return (
    <div className="rounded-2xl border border-line bg-card p-5 lg:sticky lg:top-6">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-lg font-extrabold tracking-tight text-navy">{c.name}</h2>
        <VerdictChip c={c} />
      </div>
      <p className="mt-1 text-[11px] tabular-nums text-muted">
        반복 {c.stat} · 표본 15건 기준 · <span className="font-mono">{c.fieldLine}</span>
      </p>

      <div className="mt-4 space-y-4">
        <div>
          <SectionLabel dotClass="bg-[#94A3C4]">관찰된 사실 — 원문 인용</SectionLabel>
          <div className="mt-2 space-y-2">
            {c.quotes.map((q, i) => (
              <blockquote key={i} className="rounded-xl border border-line bg-paper px-3 py-2.5">
                <div className="mb-1 flex items-center gap-1.5">
                  <span className="rounded-md bg-sky-soft px-1.5 py-0.5 font-mono text-[10px] font-bold text-sky">
                    DOC-…-{q.doc}
                  </span>
                  {q.ko && (
                    <span className="rounded-md bg-orange-soft px-1.5 py-0.5 text-[10px] font-bold text-orange-deep">
                      한국어
                    </span>
                  )}
                </div>
                <p className="text-[12.5px] leading-relaxed text-ink">{q.text}</p>
              </blockquote>
            ))}
          </div>
        </div>

        <div>
          <SectionLabel dotClass="bg-[#9F7FE8]">AI 초안의 제안</SectionLabel>
          <p className="mt-1.5 text-[13px] leading-relaxed text-ink">{c.aiProposal}</p>
        </div>

        <div>
          <SectionLabel dotClass="bg-green">사람의 판정</SectionLabel>
          <p className="mt-1.5 text-[13px] leading-relaxed text-ink">{c.humanVerdict}</p>
        </div>

        <div>
          <SectionLabel dotClass="bg-orange">스키마 반영</SectionLabel>
          <p className="mt-1.5 rounded-lg border border-orange-soft bg-paper px-3 py-2 font-mono text-[11px] leading-relaxed text-navy">
            {c.schemaSummary}
          </p>
        </div>
      </div>
      <p className="mt-4 text-[10.5px] leading-relaxed text-muted">
        기록: DECISIONS 08/19 · bootstrap-ai-draft.md — 가설 상세의 5단계 구분 표기와 같은 문법이다.
      </p>
    </div>
  );
}

/* ── ② 스키마 → DB → 여섯 소비처 ──────────────────────────────────────── */
function SchemaToDb({ c }: { c: Concept }) {
  return (
    <div className="rounded-2xl border border-line bg-card p-5">
      <h2 className="text-lg font-extrabold tracking-tight text-navy">판정이 기계가 된다</h2>
      <p className="text-xs text-muted">
        선택한 개념 <b className="text-navy">{c.name}</b>이(가) 스키마 정의 → DB 컬럼 → 여섯 소비처로 퍼지는 경로
      </p>

      {c.none ? (
        <div className="mt-4 rounded-xl border border-dashed border-line bg-paper p-4">
          <div className="text-[12px] font-bold text-muted">이 판정은 컬럼을 만들지 않았다</div>
          <p className="mt-1 text-[13px] leading-relaxed text-ink">{c.none}</p>
        </div>
      ) : (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div>
            <div className="text-[11px] font-extrabold uppercase tracking-wider text-muted">
              contract_v0_1.yaml — 실제 정의
            </div>
            <pre className="mt-2 overflow-x-auto rounded-xl border border-line bg-paper p-3 font-mono text-[11px] leading-relaxed text-navy">
              {c.yaml}
            </pre>
          </div>
          <div className="space-y-4">
            <div>
              <div className="text-[11px] font-extrabold uppercase tracking-wider text-muted">DB 컬럼 (models.py)</div>
              <div className="mt-2 space-y-1.5">
                {c.columns?.map((col) => (
                  <div key={`${col.table}.${col.column}`} className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
                    <code className="rounded-md bg-sky-soft px-2 py-0.5 font-mono text-[11px] font-bold text-sky">
                      {col.table}.{col.column}
                    </code>
                    {col.note && <span className="text-[11px] text-muted">{col.note}</span>}
                  </div>
                ))}
              </div>
            </div>
            <div>
              <div className="text-[11px] font-extrabold uppercase tracking-wider text-muted">
                하나의 정의를 공유하는 여섯 소비처
              </div>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {c.consumers?.map((s) => (
                  <span
                    key={s.label}
                    title={s.note}
                    className={`rounded-full border px-2.5 py-1 text-[11px] font-semibold ${
                      s.on ? "border-line bg-paper text-ink" : "border-dashed border-line bg-card text-muted"
                    }`}
                  >
                    <span className={s.on ? "" : "line-through decoration-1"}>{s.label}</span>
                    {s.note && <span className="ml-1 text-[10px] text-muted">· {s.note}</span>}
                  </span>
                ))}
              </div>
              <p className="mt-2 text-[11px] leading-relaxed text-muted">
                추출 출력 스키마와 Field 폼이 같은 YAML에서 생성되므로, v0.2가 승인되는 순간 두 곳이 함께 바뀐다(데모 ⑥).
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── ③ 한 문장 따라가기 ──────────────────────────────────────────────── */
const TRACE_STEPS = ["원문 기록", "구조화 추출", "CANDIDATE 저장", "사람 승인", "SQL 집계"] as const;

function RuleTag({ children }: { children: React.ReactNode }) {
  return (
    <span className="rounded-full bg-orange-soft px-2 py-0.5 text-[10px] font-bold text-orange-deep">{children}</span>
  );
}

function KV({ k, v, note }: { k: string; v: string; note?: string }) {
  return (
    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 border-t border-line py-1.5 first:border-t-0">
      <code className="w-40 shrink-0 font-mono text-[11px] text-muted">{k}</code>
      <code className="font-mono text-[11.5px] font-bold text-navy">{v}</code>
      {note && <span className="text-[10.5px] text-muted">{note}</span>}
    </div>
  );
}

function TraceStep({ step }: { step: number }) {
  if (step === 0)
    return (
      <div>
        <div className="flex flex-wrap items-center gap-1.5">
          <RuleTag>VOICE_TRANSCRIPT · ko-KR</RuleTag>
          <RuleTag>consent_confirmed=true 필수</RuleTag>
          <RuleTag>PII 마스킹 후 불변 저장</RuleTag>
        </div>
        <p className="mt-3 rounded-xl border border-line bg-paper p-4 text-[13.5px] leading-loose text-ink">
          …(인사와 근황 — 신호 없는 노이즈)… 선생님께서{" "}
          <mark className="evidence">2제 실패한 17세 환자인데 성인 허가라 손을 쓸 수 없다</mark>고 하셨고, 이어서
          청소년 용량·안전성 자료가 있으면 보내 달라는 요청이 있었다. …
        </p>
        <p className="mt-2 text-[11.5px] leading-relaxed text-muted">
          Field 앱이 수집한 새 면담(예시). 원문은 마스킹 뒤 documents/interactions에 불변으로 저장되고, 이 시점의
          문서 전문이 이후 모든 문자 오프셋의 기준이 된다.
        </p>
      </div>
    );
  if (step === 1)
    return (
      <div>
        <div className="flex flex-wrap items-center gap-1.5">
          <RuleTag>절대 규칙 #2 — 원문 없는 주장 저장 금지</RuleTag>
          <RuleTag>절대 규칙 #6 — AE는 여기서 분기</RuleTag>
        </div>
        <pre className="mt-3 overflow-x-auto rounded-xl border border-line bg-paper p-4 font-mono text-[11.5px] leading-relaxed text-navy">
{`{                                      // 구조화 출력 (JSON schema 강제) — 예시 값
  "signal_type":     "UNMET_NEED",
  "patient_segment": "PEDIATRIC_TRANSITION",
  "solicitation":    "SOLICITED_BY_MSL",   // 08/19 신규 필드가 즉시 일함
  "verbatim_quote":  "2제 실패한 17세 환자인데 성인 허가라 손을 쓸 수 없다",
  "summary_ko":      "청소년 약물난치성 환자에서 성인 허가로 인한 치료 공백",
  "evidence": { "doc_id": "DOC-…(예시)", "char_start": 214, "char_end": 246 }
}`}
        </pre>
        <p className="mt-2 text-[11.5px] leading-relaxed text-muted">
          LLM은 verbatim을 원문에서 그대로 복사할 뿐이고, 문자 오프셋은 파서가 결정론적으로 계산한다. 서버는
          verbatim이 원문의 실제 부분 문자열인지 검증하며, 실패하면 저장 자체를 거부한다. 이 문장이 이상사례였다면
          claims가 아니라 safety_candidates로 갈라졌다.
        </p>
      </div>
    );
  if (step === 2)
    return (
      <div>
        <div className="flex flex-wrap items-center gap-1.5">
          <RuleTag>절대 규칙 #3 — 집계 반영 0건</RuleTag>
          <RuleTag>등급은 결정론 계산 (LLM 아님)</RuleTag>
        </div>
        <div className="mt-3 rounded-xl border border-line bg-paper px-4 py-2">
          <KV k="claims.status" v="CANDIDATE" note="사람 승인 전 — 어떤 숫자에도 안 들어감" />
          <KV k="claims.patient_segment" v="PEDIATRIC_TRANSITION" />
          <KV k="claims.label_scope" v="OUT_OF_LABEL" note="서버 자동판정 — derivations 규칙" />
          <KV k="claims.purpose_domain" v="MEDICAL" note="signal_type에서 결정론 파생" />
          <KV k="claims.solicitation" v="SOLICITED_BY_MSL" />
          <KV k="claims.evidence_json" v='{"doc_id":…,"char_start":214,…}' />
          <KV k="claims.review_grade" v="HIGH" note="원문 일치 ∧ 용어 매핑 ∧ 규칙 통과" />
          <KV k="claims.contract_version" v="0.1" note="생성 당시 버전 영구 보존" />
        </div>
        <p className="mt-2 text-[11.5px] leading-relaxed text-muted">
          부트스트랩에서 태어난 컬럼(solicitation)과 자동판정 컬럼(label_scope)이 나란히 채워진다 — ①·②의 판정이
          그대로 행의 모양이 됐다.
        </p>
      </div>
    );
  if (step === 3)
    return (
      <div>
        <div className="flex flex-wrap items-center gap-1.5">
          <RuleTag>HIGH 등급도 자동 승인 없음</RuleTag>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3 rounded-xl border border-line bg-paper p-4">
          <span className="rounded-full bg-sky-soft px-3 py-1 text-[12px] font-bold text-sky">CANDIDATE</span>
          <span className="text-muted">→</span>
          <span className="rounded-full bg-green-soft px-3 py-1 text-[12px] font-bold text-green">APPROVED</span>
          <span className="font-mono text-[11px] text-muted">reviewed_by=건태 · reviewed_at 기록</span>
        </div>
        <p className="mt-2 text-[11.5px] leading-relaxed text-muted">
          Field의 카드 승인(스와이프)이 곧 이 전이다. 검토 행위는 상태가 아니라 reviewed_by/at 두 필드로 남고,
          반려되면 REJECTED로 보존될 뿐 삭제되지 않는다.
        </p>
      </div>
    );
  return (
    <div>
      <div className="flex flex-wrap items-center gap-1.5">
        <RuleTag>절대 규칙 #1 — 수치는 SQL만</RuleTag>
      </div>
      <div className="mt-3 rounded-xl border border-line bg-paper p-4">
        <div className="font-mono text-[11px] text-muted">GET /aggregates/signals → computedBy: &quot;SQL&quot;</div>
        <div className="mt-2 flex flex-wrap items-baseline gap-3">
          <span className="font-mono text-[12px] font-bold text-navy">PEDIATRIC_TRANSITION</span>
          <span className="text-2xl font-extrabold tabular-nums text-navy">
            14 <span className="text-muted">→</span> <span className="text-orange-deep">15</span>
          </span>
          <span className="rounded-full bg-orange-soft px-2 py-0.5 text-[11px] font-bold text-orange-deep">+1 (예시)</span>
        </div>
      </div>
      <p className="mt-2 text-[11.5px] leading-relaxed text-muted">
        한국어 면담 한 건이 영문 원석의 같은 canonical 코드에 합산되는 순간 — 다국어 시연 포인트(docs/03 §1.5)다.
        이 한 건은 HYP-001의 observedFacts에 claimId로 연결되어, 화면의 모든 숫자가 원문까지 되짚어진다.
      </p>
    </div>
  );
}

function Trace() {
  const [step, setStep] = useState(0);
  return (
    <div className="rounded-2xl border border-line bg-card p-5">
      <h2 className="text-lg font-extrabold tracking-tight text-navy">한 문장 따라가기 — 원문이 숫자가 되기까지</h2>
      <p className="text-xs text-muted">
        위에서 확정된 스키마가 실제로 어떻게 DB가 되는지, Field 면담 한 문장(예시)의 다섯 단계
      </p>

      <div className="mt-4 flex flex-wrap items-center gap-1.5">
        {TRACE_STEPS.map((t, i) => (
          <button
            key={t}
            onClick={() => setStep(i)}
            className={`rounded-full px-3 py-1.5 text-[12px] font-bold transition-colors ${
              i === step
                ? "bg-navy text-white"
                : i < step
                  ? "bg-green-soft text-green"
                  : "bg-paper text-muted hover:bg-sky-soft hover:text-navy"
            }`}
          >
            {i + 1}. {t}
          </button>
        ))}
      </div>

      <div className="mt-4">
        <TraceStep step={step} />
      </div>

      <div className="mt-4 flex items-center justify-between">
        <button
          onClick={() => setStep((s) => Math.max(0, s - 1))}
          disabled={step === 0}
          className="rounded-lg border border-line bg-card px-3 py-1.5 text-[12px] font-bold text-navy transition-colors hover:bg-paper disabled:opacity-40"
        >
          ← 이전
        </button>
        <span className="text-[11px] tabular-nums text-muted">{step + 1} / 5</span>
        <button
          onClick={() => setStep((s) => Math.min(TRACE_STEPS.length - 1, s + 1))}
          disabled={step === TRACE_STEPS.length - 1}
          className="rounded-lg bg-navy px-3 py-1.5 text-[12px] font-bold text-white transition-colors hover:opacity-90 disabled:opacity-40"
        >
          다음 →
        </button>
      </div>
    </div>
  );
}

/* ── 페이지 본체 ─────────────────────────────────────────────────────── */
export default function ProvenanceView() {
  const [selectedKey, setSelectedKey] = useState("solicitation");
  const selected = CONCEPTS.find((c) => c.key === selectedKey) ?? CONCEPTS[0];

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <div className="rounded-2xl border border-line bg-card px-4 py-3">
          <div className="text-[11px] font-bold text-muted">격리 초안이 열람한 표본</div>
          <div className="text-2xl font-extrabold tabular-nums text-navy">
            15<span className="ml-0.5 text-sm font-bold text-muted">건</span>
          </div>
          <div className="mt-0.5 text-[10.5px] leading-snug text-muted">v0.1 비공개 상태에서 작성 · 한국어 1건 포함</div>
        </div>
        <div className="rounded-2xl border border-line bg-card px-4 py-3">
          <div className="text-[11px] font-bold text-muted">신규 채택</div>
          <div className="text-2xl font-extrabold tabular-nums text-orange-deep">
            9<span className="ml-0.5 text-sm font-bold text-muted">항목</span>
          </div>
          <div className="mt-0.5 text-[10.5px] leading-snug text-muted">발언경위 1 + 논조 1 + 언급 3 + 안전성 3 + 신호값 1</div>
        </div>
        <div className="rounded-2xl border border-line bg-card px-4 py-3">
          <div className="text-[11px] font-bold text-muted">제외 — 전 항목 사유 기록</div>
          <div className="text-2xl font-extrabold text-rust">✕</div>
          <div className="mt-0.5 text-[10.5px] leading-snug text-muted">용량 수치 5종 · 사고과정 컬럼 등</div>
        </div>
        <div className="rounded-2xl border border-line bg-card px-4 py-3">
          <div className="text-[11px] font-bold text-muted">보류 → SCP 후보</div>
          <div className="text-2xl font-extrabold tabular-nums text-sky">
            5<span className="ml-0.5 text-sm font-bold text-muted">묶음</span>
          </div>
          <div className="mt-0.5 text-[10.5px] leading-snug text-muted">직함 · msl_response · 채널/시간 메타 등</div>
        </div>
      </div>

      <div className="grid items-start gap-4 lg:grid-cols-[1.55fr_1fr]">
        <Matrix selected={selectedKey} onSelect={setSelectedKey} />
        <EvidencePanel c={selected} />
      </div>

      <SchemaToDb c={selected} />
      <Trace />

      <p className="text-[11px] leading-relaxed text-muted">
        이 화면은 기록의 결정론적 렌더링이다 — 판정: docs/DECISIONS.md 08/19 · AI 초안 무편집 원문:
        docs/assets/bootstrap-ai-draft.md · 스키마: contract_v0_1.yaml. 인용과 문서 ID는 초안이 원문에서 발췌한
        것을 그대로 옮겼고, 모든 evidence는 doc_id + 문자 위치로 원문에 연결된다(절대 규칙 #2).
      </p>
    </div>
  );
}
