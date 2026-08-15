"use client";

/**
 * Data Review — 수직 슬라이스 (docs/01 §5 · docs/00 §1.5 체크 1·2·3의 증명 화면)
 * 문서 목록 → 원문(evidence 하이라이트) ↔ claim 카드 → 승인/반려 → 집계 반영.
 * [오너: 건태] 리플레이 연출·수정(amend) UI·검토 큐 뷰는 8/22~26에 이 위에 얹는다.
 */

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

type DocRow = {
  id: string;
  sourceType: string;
  sourceFormat: string;
  language: string;
  occurredOn: string;
  interactionCount: number;
  claimCounts: { candidate: number; approved: number; rejected: number };
};

type DocDetail = DocRow & {
  rawText: string;
  interactions: { interactionId: string; hcpRef: string; region: string; blockIndex: number | null }[];
};

type Claim = {
  id: string;
  interactionId: string;
  signalType: string;
  patientSegment: string;
  labelScope: string;
  reviewGrade: string;
  status: string;
  summaryKo: string;
  verbatimQuote: string;
  evidence: { docId: string; charStart: number; charEnd: number };
};

const TYPE_KO: Record<string, string> = {
  HIGHLIGHT_DOC: "하이라이트",
  CONGRESS_REPORT: "학회 보고서",
  MEETING_NOTE: "면담 기록",
  CALL_NOTE: "전화 메모",
  EMAIL_SUMMARY: "이메일",
  VOICE_TRANSCRIPT: "음성 전사",
};

function Highlighted({ text, claims }: { text: string; claims: Claim[] }) {
  const spans = claims
    .map((c) => ({ start: c.evidence.charStart, end: c.evidence.charEnd, id: c.id }))
    .sort((a, b) => a.start - b.start);
  const parts: React.ReactNode[] = [];
  let cursor = 0;
  for (const s of spans) {
    if (s.start > cursor) parts.push(text.slice(cursor, s.start));
    parts.push(
      <mark key={s.id} id={`ev-${s.id}`} className="evidence">
        {text.slice(s.start, s.end)}
      </mark>,
    );
    cursor = s.end;
  }
  parts.push(text.slice(cursor));
  return <pre className="whitespace-pre-wrap font-mono text-[12.5px] leading-relaxed">{parts}</pre>;
}

export default function ReviewPage() {
  const [docs, setDocs] = useState<DocRow[]>([]);
  const [detail, setDetail] = useState<DocDetail | null>(null);
  const [claims, setClaims] = useState<Claim[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const loadDocs = useCallback(() => {
    api<DocRow[]>("/documents").then(setDocs).catch((e) => setError(e.message));
  }, []);
  useEffect(loadDocs, [loadDocs]);

  const select = useCallback((id: string) => {
    setError(null);
    Promise.all([
      api<DocDetail>(`/documents/${id}`),
      api<Claim[]>(`/claims?documentId=${id}`),
    ])
      .then(([d, c]) => {
        setDetail(d);
        setClaims(c);
      })
      .catch((e) => setError(e.message));
  }, []);

  async function review(claimId: string, action: "approve" | "reject") {
    setBusy(claimId);
    try {
      await api(`/claims/${claimId}`, {
        method: "PATCH",
        body: JSON.stringify({ action, reviewedBy: "건태" }),
      });
      if (detail) select(detail.id);
      loadDocs(); // 목록의 카운트도 갱신 — 집계는 서버 SQL이 다시 센다
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="mx-auto max-w-7xl">
      <p className="text-xs font-bold tracking-widest text-orange-deep">SENSE · DATA REVIEW</p>
      <h1 className="mt-1 text-2xl font-extrabold tracking-tight text-navy">검토·승인</h1>
      <p className="mt-1 text-sm text-muted">
        카드의 근거는 원문 형광펜과 1:1로 연결된다 (절대 규칙 #2). 승인해야만 집계에 들어간다 (#3).
      </p>
      {error && (
        <div className="mt-4 rounded-lg bg-rust-soft px-4 py-2 text-sm text-rust">{error}</div>
      )}

      <div className="mt-6 grid gap-4 lg:grid-cols-[280px_1fr_360px]">
        {/* 문서 목록 */}
        <div className="max-h-[75vh] overflow-y-auto rounded-2xl border border-line bg-card p-2">
          {docs.map((d) => (
            <button
              key={d.id}
              onClick={() => select(d.id)}
              className={`block w-full rounded-lg px-3 py-2 text-left text-xs transition-colors ${
                detail?.id === d.id ? "bg-orange-soft" : "hover:bg-sky-soft"
              }`}
            >
              <div className="font-mono font-bold text-navy">{d.id}</div>
              <div className="mt-0.5 flex flex-wrap gap-1 text-[10px] text-muted">
                <span>{TYPE_KO[d.sourceType] ?? d.sourceType}</span>
                <span>· {d.language}</span>
                <span>· {d.sourceFormat}</span>
                {d.claimCounts.candidate > 0 && (
                  <span className="rounded bg-orange-soft px-1 font-bold text-orange-deep">
                    검토 {d.claimCounts.candidate}
                  </span>
                )}
                {d.claimCounts.approved > 0 && (
                  <span className="rounded bg-green-soft px-1 font-bold text-green">
                    승인 {d.claimCounts.approved}
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>

        {/* 원문 패널 */}
        <div className="max-h-[75vh] overflow-y-auto rounded-2xl border border-line bg-card p-5">
          {detail ? (
            <>
              <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-muted">
                <b className="font-mono text-navy">{detail.id}</b>
                <span>{detail.occurredOn}</span>
                <span>· 인사이트 단위 {detail.interactionCount}개</span>
              </div>
              <Highlighted text={detail.rawText} claims={claims} />
            </>
          ) : (
            <p className="py-20 text-center text-sm text-muted">
              왼쪽에서 문서를 선택하세요 — 원문과 추출 카드가 나란히 열립니다.
            </p>
          )}
        </div>

        {/* claim 카드 */}
        <div className="max-h-[75vh] space-y-3 overflow-y-auto">
          {detail && claims.length === 0 && (
            <div className="rounded-2xl border border-dashed border-line bg-card p-5 text-sm text-muted">
              이 문서의 추출 후보가 없습니다. 추출 실행(
              <code className="text-xs">POST /documents/:id/extract</code>)은 8/21 stub 교체
              [오너: 인혁].
            </div>
          )}
          {claims.map((c) => (
            <div key={c.id} className="rounded-2xl border border-line bg-card p-4 text-sm">
              <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-bold">
                <span className="rounded-full bg-sky-soft px-2 py-0.5 text-sky">{c.signalType}</span>
                <span className="rounded-full bg-sky-soft px-2 py-0.5 text-sky">{c.patientSegment}</span>
                <span
                  className={`rounded-full px-2 py-0.5 ${
                    c.labelScope === "OUT_OF_LABEL"
                      ? "bg-rust-soft text-rust"
                      : "bg-green-soft text-green"
                  }`}
                >
                  {c.labelScope === "OUT_OF_LABEL" ? "허가 범위 밖 · Development" : "In-label"}
                </span>
                <span className="rounded-full border border-line px-2 py-0.5 text-muted">
                  {c.reviewGrade}
                </span>
              </div>
              <p className="mt-2 font-semibold text-navy">{c.summaryKo}</p>
              <a
                href={`#ev-${c.id}`}
                className="mt-2 block rounded-lg bg-paper px-3 py-2 text-xs leading-relaxed text-muted"
              >
                “{c.verbatimQuote}”
                <span className="mt-1 block text-[10px] text-orange-deep">
                  원문 {c.evidence.charStart}–{c.evidence.charEnd}자 → 클릭하면 형광펜으로 이동
                </span>
              </a>
              <div className="mt-3 flex items-center gap-2">
                {c.status === "CANDIDATE" ? (
                  <>
                    <button
                      disabled={busy === c.id}
                      onClick={() => review(c.id, "approve")}
                      className="rounded-lg bg-navy px-3 py-1.5 text-xs font-bold text-white hover:opacity-90 disabled:opacity-50"
                    >
                      승인
                    </button>
                    <button
                      disabled={busy === c.id}
                      onClick={() => review(c.id, "reject")}
                      className="rounded-lg border border-line px-3 py-1.5 text-xs font-bold text-muted hover:bg-rust-soft hover:text-rust disabled:opacity-50"
                    >
                      반려
                    </button>
                    <span className="text-[10px] text-muted">수정 후 승인은 8/23 [건태]</span>
                  </>
                ) : (
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-bold ${
                      c.status === "APPROVED" ? "bg-green-soft text-green" : "bg-rust-soft text-rust"
                    }`}
                  >
                    {c.status === "APPROVED" ? "승인됨 — 집계 반영" : "반려됨 — 집계 제외·보존"}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
