"use client";

/**
 * 처리 라인 — 원석 한 건이 에이전트 3종을 지나 구조화되는 과정을 눈으로 본다 (08/22 신설).
 * [오너: 건태 — 도메인 화면. 디자인 토큰 정리는 소정 8/24]
 *
 * 이 화면의 목적은 "됐다"가 아니라 **"어떻게 됐는지"**를 보여주는 것이다.
 *  ① Contract 설계자 — 원석을 읽고 뽑을 항목 자체를 제안 (활성 Contract는 안 바뀐다)
 *  ② 발언 귀속자     — 한 문서 안에서 누가 말했는지 구간을 가르고, 정답과 대조해 점수를 낸다
 *  ③ 인사이트 분석가 — 그 구간을 읽고 스키마 항목으로 뽑는다. 근거가 원문과 다르면 버려진다
 *
 * 버려진 건수(`rejectedNoEvidence`)를 숨기지 않고 같은 크기로 보여준다 — 막고 있다는 증거이므로.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { api, ApiError } from "@/lib/api";

// ── 타입 (docs/04 §1·§5·§8) ────────────────────────────────────────────────

type Agent = {
  agent: string; labelKo: string; model: string;
  keyEnv: string; keySource: string | null; ready: boolean;
};
type DocRow = {
  id: string; sourceType: string; sourceFormat: string; language: string;
  occurredOn: string; interactionCount: number;
  claimCounts: { candidate: number; approved: number; rejected: number };
};
type DocDetail = DocRow & {
  rawText: string;
  interactions: { interactionId: string; hcpRef: string; blockIndex: number | null;
                  docCharStart: number | null; docCharEnd: number | null }[];
};
type Block = {
  hcpSurface: string; specialtySurface: string | null; institutionSurface: string | null;
  confidence: "CLEAR" | "INFERRED" | "UNCERTAIN"; boundaryNoteKo: string | null;
  charStart: number; charEnd: number;
};
type Attribution = {
  documentId: string; blocks: Block[];
  dropped: { hcpSurface: string; reason: string }[];
  unattributedNoteKo: string | null; coverageRatio: number;
  confidenceCounts: Record<string, number>;
  score: { truthBlocks: number; aiBlocks: number; matched: number; missed: number;
           extra: number; meanIou: number; blockRecall: number } | null;
};
type Extraction = {
  documentId: string; skipped: boolean; existingClaims?: number;
  blocks: number; claims: number; safety: number; safetyRerouted: number;
  rejectedNoEvidence: number; unmapped: number;
  byGrade: Record<string, number>;
};
type Claim = {
  id: string; interactionId: string; signalType: string; patientSegment: string;
  labelScope: string; reviewGrade: string; status: string; summaryKo: string;
  verbatimQuote: string; evidence: { docId: string; charStart: number; charEnd: number };
};
type Proposal = {
  sampledDocuments: string[]; sourceFormats: string[]; activeContractVersion: string;
  fields: { key: string; labelKo: string; kind: string; rationaleKo: string;
            observedInDocs: number; alreadyInContract: boolean;
            values: { value: string; labelKo: string }[];
            evidence: { docId: string; quote: string }[] }[];
  rejected: { key: string; reasonKo: string }[];
  droppedEvidence: number;
  note_ko: string;
};

const GRADE_KO: Record<string, string> = {
  HIGH: "H · 자동검증 3종 통과",
  MEDIUM: "M · 용어 매핑 실패",
  LOW: "L · 파생 규칙 미충족",
};
const CONF_KO: Record<string, string> = {
  CLEAR: "문서가 명시", INFERRED: "문맥으로 이어붙임", UNCERTAIN: "경계 모호",
};
const BLOCK_TINT = ["#EAF0FF", "#FCF1E0", "#E2F5EE", "#FBE9EC", "#F0EDFB", "#EAF6FA"];

// ── 원문 뷰어: 단계에 따라 다른 것을 덮어씌운다 ─────────────────────────────

function RawText({ text, blocks, claims }: { text: string; blocks: Block[]; claims: Claim[] }) {
  const parts = useMemo(() => {
    type Mark = { start: number; end: number; kind: "block" | "claim"; i: number; label?: string };
    const marks: Mark[] = [
      ...blocks.map((b, i) => ({ start: b.charStart, end: b.charEnd, kind: "block" as const, i,
                                 label: b.hcpSurface })),
      ...claims.map((c, i) => ({ start: c.evidence.charStart, end: c.evidence.charEnd,
                                 kind: "claim" as const, i })),
    ].sort((a, b) => a.start - b.start || (a.kind === "block" ? -1 : 1));

    // 블록 위에 claim 하이라이트를 겹쳐 그린다 — 블록을 배경, claim을 형광펜으로
    const out: React.ReactNode[] = [];
    const blockMarks = marks.filter((m) => m.kind === "block");
    const claimMarks = marks.filter((m) => m.kind === "claim");
    let cursor = 0;

    const renderInner = (from: number, to: number, key: string) => {
      const inner: React.ReactNode[] = [];
      let c = from;
      for (const cm of claimMarks) {
        if (cm.start < from || cm.end > to) continue;
        if (cm.start > c) inner.push(text.slice(c, cm.start));
        inner.push(
          <mark key={`c${cm.i}`} className="rounded-sm bg-orange px-0.5 text-white">
            {text.slice(cm.start, cm.end)}
          </mark>,
        );
        c = cm.end;
      }
      if (c < to) inner.push(text.slice(c, to));
      return <span key={key}>{inner}</span>;
    };

    for (const bm of blockMarks) {
      if (bm.start > cursor) out.push(renderInner(cursor, bm.start, `g${bm.i}`));
      out.push(
        <span key={`b${bm.i}`} className="relative block rounded-md border-l-4 px-2 py-1"
              style={{ background: BLOCK_TINT[bm.i % BLOCK_TINT.length], borderColor: "var(--sky)" }}>
          <span className="mb-1 block text-[11px] font-bold tracking-wide text-muted">
            블록 {bm.i + 1} · {bm.label}
          </span>
          {renderInner(bm.start, bm.end, `bi${bm.i}`)}
        </span>,
      );
      cursor = bm.end;
    }
    if (cursor < text.length) out.push(renderInner(cursor, text.length, "tail"));
    return out;
  }, [text, blocks, claims]);

  return (
    <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap rounded-xl border border-line
                    bg-card p-4 text-[13px] leading-relaxed text-ink">
      {parts}
    </pre>
  );
}

// ── 단계 카드 ───────────────────────────────────────────────────────────────

function Stage({ n, title, agent, model, ready, busy, onRun, disabled, children }: {
  n: string; title: string; agent: string; model: string; ready: boolean;
  busy: boolean; onRun: () => void; disabled?: boolean; children?: React.ReactNode;
}) {
  return (
    <section className="rounded-2xl border border-line bg-card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="rounded-md bg-navy px-2 py-0.5 text-xs font-bold text-white">{n}</span>
            <h2 className="text-base font-bold text-navy">{title}</h2>
          </div>
          <p className="mt-1 text-xs text-muted">
            에이전트 <b className="text-ink">{agent}</b> · 모델 <code>{model}</code> ·{" "}
            {ready ? <span className="text-green">키 연결됨</span>
                   : <span className="text-rust">키 없음 — 캐시에 있으면 동작</span>}
          </p>
        </div>
        <button onClick={onRun} disabled={busy || disabled}
                className="rounded-lg bg-orange px-4 py-2 text-sm font-bold text-white
                           disabled:cursor-not-allowed disabled:bg-line disabled:text-muted">
          {busy ? "실행 중…" : "실행"}
        </button>
      </div>
      {children && <div className="mt-4">{children}</div>}
    </section>
  );
}

function Stat({ label, value, tone }: { label: string; value: React.ReactNode; tone?: "warn" | "ok" }) {
  return (
    <div className="rounded-lg border border-line px-3 py-2">
      <div className="text-[11px] text-muted">{label}</div>
      <div className={`text-lg font-bold ${tone === "warn" ? "text-rust" : tone === "ok" ? "text-green" : "text-navy"}`}>
        {value}
      </div>
    </div>
  );
}

// ── 페이지 ──────────────────────────────────────────────────────────────────

export default function PipelinePage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [docs, setDocs] = useState<DocRow[]>([]);
  const [docId, setDocId] = useState<string | null>(null);
  const [detail, setDetail] = useState<DocDetail | null>(null);
  const [attr, setAttr] = useState<Attribution | null>(null);
  const [extract, setExtract] = useState<Extraction | null>(null);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const agentOf = (name: string) => agents.find((a) => a.agent === name);

  useEffect(() => {
    api<{ agents: Agent[] }>("/system/agents").then((d) => setAgents(d.agents)).catch(() => {});
    api<DocRow[]>("/documents").then((d) => {
      // 의료진이 여럿 담긴 문서를 앞에 — 귀속이 하는 일이 한눈에 보인다
      const sorted = [...d].sort((a, b) => b.interactionCount - a.interactionCount);
      setDocs(sorted);
      if (sorted[0]) setDocId(sorted[0].id);
    }).catch((e) => setErr(e.message));
  }, []);

  const loadDoc = useCallback(async (id: string) => {
    setAttr(null); setExtract(null); setClaims([]); setErr(null);
    setDetail(await api<DocDetail>(`/documents/${id}`));
    setClaims(await api<Claim[]>(`/claims?documentId=${id}`).catch(() => []));
  }, []);

  useEffect(() => { if (docId) loadDoc(docId).catch((e) => setErr(e.message)); }, [docId, loadDoc]);

  const run = async (key: string, fn: () => Promise<void>) => {
    setBusy(key); setErr(null);
    try { await fn(); }
    catch (e) { setErr(e instanceof ApiError ? `${e.code} — ${e.message}` : String(e)); }
    finally { setBusy(null); }
  };

  return (
    <div className="space-y-5">
      <header>
        <h1 className="text-xl font-bold text-navy">처리 라인 — 원석에서 구조화까지</h1>
        <p className="mt-1 text-sm text-muted">
          비정형 파일 한 건이 에이전트 셋을 지나 의료진별 구조화 데이터가 되는 과정입니다.
          <b className="text-ink"> 판단은 에이전트가, 숫자와 검증은 서버가</b> 합니다 — 아래 수치는 전부 서버가 센 것입니다.
        </p>
      </header>

      {err && (
        <div className="rounded-xl border border-rust bg-rust-soft px-4 py-3 text-sm text-ink">
          {err}
        </div>
      )}

      {/* ── ① Contract 설계자 ───────────────────────────────────────────── */}
      <Stage
        n="①" title="스키마 자체를 제안한다" agent="Contract 설계자"
        model={agentOf("contract_architect")?.model ?? "—"}
        ready={!!agentOf("contract_architect")?.ready}
        busy={busy === "propose"}
        onRun={() => run("propose", async () => {
          setProposal(await api<Proposal>("/contract/propose?sampleSize=12",
            { method: "POST", role: "DATA_STEWARD" }));
        })}
      >
        {!proposal ? (
          <p className="text-sm text-muted">
            원석 표본을 읽고 <b className="text-ink">무엇을 뽑을지</b>부터 제안합니다.
            활성 Contract는 변경되지 않습니다 — 채택은 사람(Data Steward)만 합니다.
          </p>
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Stat label="표본 문서" value={proposal.sampledDocuments.length} />
              <Stat label="제안 항목" value={proposal.fields.length} />
              <Stat label="제외 항목" value={proposal.rejected.length} />
              <Stat label="근거 폐기" value={proposal.droppedEvidence}
                    tone={proposal.droppedEvidence ? "warn" : "ok"} />
            </div>
            <p className="text-xs text-muted">{proposal.note_ko}</p>
            <div className="space-y-2">
              {proposal.fields.map((f) => (
                <div key={f.key} className="rounded-lg border border-line p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <code className="text-sm font-bold text-navy">{f.key}</code>
                    <span className="text-sm text-ink">{f.labelKo}</span>
                    <span className="rounded bg-sky-soft px-1.5 py-0.5 text-[11px] text-muted">{f.kind}</span>
                    <span className="text-[11px] text-muted">문서 {f.observedInDocs}건에서 관찰</span>
                    {f.alreadyInContract && (
                      <span className="rounded bg-green-soft px-1.5 py-0.5 text-[11px] text-green">
                        v{proposal.activeContractVersion}에 이미 있음
                      </span>
                    )}
                  </div>
                  <p className="mt-1 text-xs text-muted">{f.rationaleKo}</p>
                  {f.evidence.slice(0, 2).map((e, i) => (
                    <blockquote key={i} className="mt-2 border-l-2 border-orange pl-2 text-xs italic text-ink">
                      “{e.quote}” <span className="not-italic text-muted">— {e.docId}</span>
                    </blockquote>
                  ))}
                </div>
              ))}
            </div>
            {proposal.rejected.length > 0 && (
              <details className="rounded-lg border border-line p-3">
                <summary className="cursor-pointer text-sm font-bold text-navy">
                  제외한 항목 {proposal.rejected.length}건 — 무엇을 뺐는지가 스키마의 절반입니다
                </summary>
                <ul className="mt-2 space-y-1 text-xs text-muted">
                  {proposal.rejected.map((r) => (
                    <li key={r.key}><code className="text-ink">{r.key}</code> — {r.reasonKo}</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        )}
      </Stage>

      {/* ── 원석 고르기 ─────────────────────────────────────────────────── */}
      <section className="rounded-2xl border border-line bg-card p-5">
        <h2 className="text-base font-bold text-navy">원석 고르기</h2>
        <p className="mt-1 text-xs text-muted">
          의료진이 여럿 담긴 문서가 위에 옵니다 — 귀속 에이전트가 하는 일이 한눈에 보입니다.
        </p>
        <select value={docId ?? ""} onChange={(e) => setDocId(e.target.value)}
                className="mt-3 w-full rounded-lg border border-line bg-paper px-3 py-2 text-sm">
          {docs.map((d) => (
            <option key={d.id} value={d.id}>
              {d.id} · {d.sourceFormat} · 의료진 {d.interactionCount}인 · claim {d.claimCounts.candidate + d.claimCounts.approved}건
            </option>
          ))}
        </select>
      </section>

      {/* ── ② 발언 귀속자 ───────────────────────────────────────────────── */}
      <Stage
        n="②" title="누가 말했는지 가른다" agent="발언 귀속자"
        model={agentOf("hcp_attributor")?.model ?? "—"}
        ready={!!agentOf("hcp_attributor")?.ready}
        busy={busy === "attr"} disabled={!docId}
        onRun={() => run("attr", async () => {
          setAttr(await api<Attribution>(`/documents/${docId}/attribute`, { method: "POST" }));
        })}
      >
        {!attr ? (
          <p className="text-sm text-muted">
            원석 한 파일에 의료진이 여럿 섞여 있습니다. 이 구간을 잘못 가르면
            <b className="text-ink"> A 의사의 발언이 B 의사 것으로 집계</b>됩니다 —
            &ldquo;독립 의료진 몇 명&rdquo;이 판단의 근거이므로 그 오류는 결론을 뒤집습니다.
          </p>
        ) : (
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
              <Stat label="AI가 가른 구간" value={attr.blocks.length} />
              <Stat label="원문 커버리지" value={`${Math.round(attr.coverageRatio * 100)}%`} />
              <Stat label="경계 인용 실패" value={attr.dropped.length}
                    tone={attr.dropped.length ? "warn" : "ok"} />
              <Stat label="경계 모호" value={attr.confidenceCounts.UNCERTAIN ?? 0} />
            </div>
            {attr.score && (
              <div className="rounded-lg border border-line bg-sky-soft p-3 text-sm">
                <b className="text-navy">정답 대조</b>{" "}
                <span className="text-muted">— 합성 코퍼스에만 있는 정답 분할과 비교했습니다.
                  실제 사내 원석에는 정답이 없으므로 이 칸이 비어서 나옵니다.</span>
                <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
                  <Stat label="정답 구간" value={attr.score.truthBlocks} />
                  <Stat label="맞힘 (IoU≥0.8)" value={attr.score.matched} tone="ok" />
                  <Stat label="놓침" value={attr.score.missed}
                        tone={attr.score.missed ? "warn" : "ok"} />
                  <Stat label="평균 IoU" value={attr.score.meanIou} />
                </div>
              </div>
            )}
            {attr.unattributedNoteKo && (
              <p className="text-xs text-muted">귀속 불가 구간: {attr.unattributedNoteKo}</p>
            )}
            <div className="space-y-1">
              {attr.blocks.map((b, i) => (
                <div key={i} className="flex flex-wrap items-center gap-2 rounded-lg border border-line px-3 py-2 text-xs">
                  <span className="h-3 w-3 rounded-sm"
                        style={{ background: BLOCK_TINT[i % BLOCK_TINT.length] }} />
                  <b className="text-ink">{b.hcpSurface}</b>
                  {b.specialtySurface && <span className="text-muted">{b.specialtySurface}</span>}
                  <span className="ml-auto text-muted">
                    {b.charStart}–{b.charEnd}자 · {CONF_KO[b.confidence]}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </Stage>

      {/* ── ③ 인사이트 분석가 ───────────────────────────────────────────── */}
      <Stage
        n="③" title="스키마 항목으로 뽑는다" agent="인사이트 분석가"
        model={agentOf("insight_analyst")?.model ?? "—"}
        ready={!!agentOf("insight_analyst")?.ready}
        busy={busy === "extract"} disabled={!docId}
        onRun={() => run("extract", async () => {
          // force = 기존 claim을 지우고 재적재. LLM 캐시는 그대로 쓰므로 다시 눌러도 비용이 0이다
          // (모델을 실제로 다시 부르려면 refresh=true — 프롬프트를 고친 뒤에만 쓴다)
          setExtract(await api<Extraction>(`/documents/${docId}/extract?force=true`, { method: "POST" }));
          setClaims(await api<Claim[]>(`/claims?documentId=${docId}`).catch(() => []));
        })}
      >
        {!extract ? (
          <p className="text-sm text-muted">
            구간마다 한 줄씩 읽고 스키마 항목으로 뽑습니다. 인용문이 원문과
            <b className="text-ink"> 한 글자라도 다르면 저장하지 않습니다</b> — 근거 없는 값은 DB에 들어가지 않습니다.
          </p>
        ) : (
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
            <Stat label="읽은 구간" value={extract.blocks} />
            <Stat label="저장된 claim" value={extract.claims} tone="ok" />
            <Stat label="근거 불일치로 거부" value={extract.rejectedNoEvidence}
                  tone={extract.rejectedNoEvidence ? "warn" : "ok"} />
            <Stat label="안전성 분기" value={extract.safety} />
            <Stat label="미매핑 용어" value={extract.unmapped} />
          </div>
        )}
        {extract && (
          <p className="mt-2 text-xs text-muted">
            등급 — {Object.entries(extract.byGrade).map(([g, n]) => `${GRADE_KO[g]}: ${n}`).join(" · ")}.
            저장된 claim은 전부 <code>CANDIDATE</code>이며 승인 전까지 공식 집계에 들어가지 않습니다.
          </p>
        )}
      </Stage>

      {/* ── 결과: 원문 + 의료진별 claim ─────────────────────────────────── */}
      {detail && (
        <section className="grid gap-4 lg:grid-cols-2">
          <div>
            <h2 className="mb-2 text-base font-bold text-navy">원문</h2>
            <p className="mb-2 text-xs text-muted">
              배경색 = ②가 가른 의료진 구간 · <mark className="bg-orange px-1 text-white">주황</mark> = ③이 근거로 지목한 문장
            </p>
            <RawText text={detail.rawText} blocks={attr?.blocks ?? []} claims={claims} />
          </div>
          <div>
            <h2 className="mb-2 text-base font-bold text-navy">
              구조화 결과 <span className="text-sm font-normal text-muted">— 의료진별 {claims.length}건</span>
            </h2>
            <div className="max-h-[32rem] space-y-2 overflow-auto">
              {claims.length === 0 && (
                <p className="rounded-xl border border-line bg-card p-4 text-sm text-muted">
                  아직 없습니다. ③을 실행하세요.
                </p>
              )}
              {claims.map((c) => (
                <article key={c.id} className="rounded-xl border border-line bg-card p-3">
                  <div className="flex flex-wrap items-center gap-2 text-[11px]">
                    <code className="font-bold text-navy">{c.interactionId}</code>
                    <span className="rounded bg-sky-soft px-1.5 py-0.5 text-muted">{c.signalType}</span>
                    <span className="rounded bg-sky-soft px-1.5 py-0.5 text-muted">{c.patientSegment}</span>
                    {c.labelScope === "OUT_OF_LABEL" && (
                      <span className="rounded bg-rust-soft px-1.5 py-0.5 font-bold text-rust">허가 범위 밖</span>
                    )}
                    <span className="ml-auto text-muted">{GRADE_KO[c.reviewGrade] ?? c.reviewGrade}</span>
                  </div>
                  <p className="mt-2 text-sm text-ink">{c.summaryKo}</p>
                  <blockquote className="mt-1 border-l-2 border-orange pl-2 text-xs italic text-muted">
                    “{c.verbatimQuote}”
                  </blockquote>
                  <p className="mt-1 text-[11px] text-muted">
                    근거 위치 {c.evidence.charStart}–{c.evidence.charEnd}자 · 상태 {c.status}
                  </p>
                </article>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
