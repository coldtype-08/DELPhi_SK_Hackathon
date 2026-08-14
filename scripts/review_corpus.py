#!/usr/bin/env python3
"""
review_corpus.py — 코퍼스 리얼리티 검수 페이지 생성기 (2026-08-14)

docs/03 §5.6 사람 검수(8/15–18)용. 생성된 코퍼스를 HTML 한 장으로 만들어
 ① 문서가 "우리 회사 문서 같은지" 읽고 판정하고
 ② 심어둔 신호 문장이 ground_truth의 문자 위치대로 정확히 하이라이트되는지 눈으로 검증한다.
   (하이라이트가 문장과 어긋나면 evidence pointer 오프셋이 틀렸다는 뜻 — 절대 규칙 #2의 사전 점검)

사용: python3 scripts/review_corpus.py  →  backend/data/corpus/REVIEW.html
"""

import json
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "backend" / "data" / "corpus"
OUT = CORPUS / "REVIEW.html"

SIGNAL_LABEL = {
    "S1": "S1 청소년 치료공백 (대표가설)", "S2": "S2 이상사례 시사 → 안전성 분리",
    "S3": "S3 스키마 공백 (post-stroke)", "S4": "S4 자료 요청",
    "S5": "S5 긍정 신호", "S6": "S6 노인 DDI (In-label)",
    "X1": "의도 삽입 — Critic 차단 대상", "X2": "의도 삽입 — Critic 차단 대상",
}
TYPE_LABEL = {
    "HIGHLIGHT_DOC": "하이라이트 묶음 (영문 · docx)", "CONGRESS_REPORT": "학회 참관 보고서 (영문 · pdf)",
    "MEETING_NOTE": "면담 기록 (영문)", "CALL_NOTE": "전화 메모 (영문)",
    "EMAIL_SUMMARY": "이메일 요약 (영문)", "VOICE_TRANSCRIPT": "음성 전사 (한국어)",
}
TYPE_ORDER = ["HIGHLIGHT_DOC", "CONGRESS_REPORT", "MEETING_NOTE", "CALL_NOTE", "EMAIL_SUMMARY", "VOICE_TRANSCRIPT"]


def read_jsonl(path):
    if not path.exists():
        sys.exit(f"{path} 가 없습니다. 먼저 코퍼스를 생성하세요: bash scripts/generate.sh")
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def mark_text(raw, spans):
    """오프셋 기준으로 하이라이트 삽입 — 뒤에서부터 넣어야 앞 오프셋이 밀리지 않는다."""
    out = raw
    for s in sorted(spans, key=lambda x: x["char_start"], reverse=True):
        a, b = s["char_start"], s["char_end"]
        sid = s["signal_id"]
        cls = "bait" if sid.startswith("X") else ("safety" if sid == "S2" else "sig")
        out = (out[:a] + f"\x00{cls}\x01{sid}\x02" + out[a:b] + "\x03" + out[b:])
    out = escape(out)
    for cls in ("sig", "safety", "bait"):
        out = out.replace(f"\x00{cls}\x01", f'<mark class="{cls}" data-sid="')
    return out.replace("\x02", '">').replace("\x03", "</mark>")


def main():
    manifest = read_jsonl(CORPUS / "manifest.jsonl")
    ground = read_jsonl(CORPUS / "ground_truth.jsonl")

    docs = {}
    for row in manifest:
        d = docs.setdefault(row["doc_id"], {
            "doc_id": row["doc_id"], "source_type": row["source_type"], "language": row["language"],
            "occurred_on": row["occurred_on"], "file": row["file"], "units": [], "formats": set(),
        })
        d["units"].append(row)
        d["formats"].add(row["source_format"])
    for d in docs.values():
        d["units"].sort(key=lambda u: u["block_index"] or 1)
        p = CORPUS / d["file"]
        d["raw"] = p.read_text(encoding="utf-8") if p.exists() else "(원문 파일 없음)"
        d["signals"] = [g for g in ground if g["doc_id"] == d["doc_id"]]

    sig_counts = {}
    for g in ground:
        sig_counts[g["signal_id"]] = sig_counts.get(g["signal_id"], 0) + 1
    n_docx = sum(1 for d in docs.values() if (CORPUS / (d["doc_id"] + ".docx")).exists())
    n_pdf = sum(1 for d in docs.values() if (CORPUS / (d["doc_id"] + ".pdf")).exists())

    P = []
    P.append("""<!doctype html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>DELPHi 코퍼스 검수</title><style>
:root{--paper:#FAF7F1;--card:#fff;--ink:#232A47;--navy:#162661;--muted:#5C6485;--line:rgba(22,38,97,.13);
--orange:#EF8B1C;--orange-deep:#C56E0D;--orange-soft:#FCF1E0;--rust:#B4552D;--rust-soft:#F8ECE4;--code:#F3EFE6}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);line-height:1.7;
font-family:Pretendard,-apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif;font-size:15px}
.wrap{max-width:1000px;margin:0 auto;padding:44px 22px 80px}
h1{color:var(--navy);font-size:30px;font-weight:800;letter-spacing:-.02em;margin:0 0 10px}
h2{color:var(--navy);font-size:20px;font-weight:800;margin:52px 0 4px;letter-spacing:-.015em}
.sub{color:var(--muted);font-size:13px;margin:0 0 18px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin:20px 0 8px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px}
.kpi .n{font-size:22px;font-weight:800;color:var(--navy);font-variant-numeric:tabular-nums}
.kpi .l{font-size:11.5px;color:var(--muted);font-weight:700;letter-spacing:.04em}
.how{background:var(--orange-soft);border:1px solid rgba(239,139,28,.32);border-radius:12px;padding:14px 18px;margin:18px 0}
.how b{color:var(--orange-deep)}.how ol{margin:8px 0 0;padding-left:20px}.how li{margin-bottom:4px;font-size:14px}
.doc{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;margin:12px 0;
box-shadow:0 1px 2px rgba(22,38,97,.04)}
.doc>summary{cursor:pointer;list-style:none;display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center}
.doc>summary::-webkit-details-marker{display:none}
.did{font-family:ui-monospace,Menlo,monospace;font-weight:700;color:var(--navy);font-size:13.5px}
.meta{font-size:12.5px;color:var(--muted)}
.badge{font-size:11px;font-weight:700;padding:2px 8px;border-radius:999px;border:1px solid var(--line);color:var(--muted);background:#fff}
.badge.fmt{color:var(--navy)}.badge.sig{background:var(--orange-soft);color:var(--orange-deep);border-color:rgba(239,139,28,.35)}
.badge.saf{background:var(--rust-soft);color:var(--rust);border-color:rgba(180,85,45,.3)}
.units{margin:12px 0 0;font-size:12.5px;color:var(--muted)}
.units code{background:var(--code);border-radius:4px;padding:1px 5px;font-size:11.5px}
pre.raw{background:var(--code);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:12px 0 0;
white-space:pre-wrap;word-break:break-word;font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12.5px;line-height:1.75}
mark{border-radius:3px;padding:1px 2px;position:relative}
mark.sig{background:rgba(239,139,28,.30);box-shadow:inset 0 -2px 0 var(--orange)}
mark.safety{background:rgba(180,85,45,.22);box-shadow:inset 0 -2px 0 var(--rust)}
mark.bait{background:rgba(180,85,45,.14);box-shadow:inset 0 -2px 0 var(--rust);outline:1px dashed rgba(180,85,45,.55)}
mark::after{content:attr(data-sid);font-size:9px;font-weight:800;color:var(--orange-deep);vertical-align:super;margin-left:2px}
mark.safety::after,mark.bait::after{color:var(--rust)}
.legend{display:flex;flex-wrap:wrap;gap:14px;font-size:12.5px;color:var(--muted);margin:10px 0 0}
.foot{margin-top:60px;padding-top:18px;border-top:1px solid var(--line);font-size:12.5px;color:var(--muted)}
</style></head><body><div class="wrap">""")

    P.append(f"""<h1>합성 코퍼스 검수</h1>
<p class="sub">docs/03 §5.6 · 검수 기준: <b>"우리 회사 문서 같다"</b> (내용 + 양식). 하이라이트는 ground_truth의 문자 위치로 그린 것이므로,
문장과 어긋나면 오프셋 버그다.</p>
<div class="kpis">
  <div class="kpi"><div class="n">{len(docs)}</div><div class="l">문서</div></div>
  <div class="kpi"><div class="n">{len(manifest)}</div><div class="l">인사이트 단위</div></div>
  <div class="kpi"><div class="n">{len(ground)}</div><div class="l">심은 신호</div></div>
  <div class="kpi"><div class="n">{n_docx}</div><div class="l">docx 포장</div></div>
  <div class="kpi"><div class="n">{n_pdf}</div><div class="l">pdf 포장</div></div>
</div>
<div class="legend">
  <span><mark class="sig" data-sid="S1">신호 문장</mark> 집계·가설의 근거</span>
  <span><mark class="safety" data-sid="S2">S2</mark> 안전성 분리 대상</span>
  <span><mark class="bait" data-sid="X1">X</mark> Critic이 막아야 하는 의도 삽입</span>
</div>
<div class="how"><b>검수 방법 (1인당 20문서)</b>
<ol>
<li>제목만 눌러 펼치고 <b>본문을 읽는다</b> — 실제 현장 기록처럼 읽히는지, 문체·오타·약어가 자연스러운지.</li>
<li>하이라이트가 <b>문장 경계와 정확히 맞는지</b> 본다 (반 글자라도 밀리면 그 문서 ID를 적어둔다).</li>
<li>하이라이트형·학회형은 <b>HCP 블록이 사람별로 갈리는지</b> 확인 (블록 목록과 본문 순서 대조).</li>
<li>어색한 문서는 <b>문서 ID를 메모</b> → 해당 블록 본문만 고쳐 재생성한다 (scripts/corpus_bodies/*.json).</li>
<li>양식 검수는 docx·pdf 파일을 직접 열어서 한다 (이 페이지는 텍스트 정본만 보여준다).</li>
</ol></div>
<p class="sub">신호 분포: {" · ".join(f"{k} {v}건" for k, v in sorted(sig_counts.items()))}</p>""")

    for st in TYPE_ORDER:
        group = [d for d in docs.values() if d["source_type"] == st]
        if not group:
            continue
        group.sort(key=lambda d: d["occurred_on"])
        P.append(f'<h2>{TYPE_LABEL[st]}</h2><p class="sub">{len(group)}건 · '
                 f'{sum(len(d["units"]) for d in group)} 인사이트 단위</p>')
        for d in group:
            sids = [g["signal_id"] for g in d["signals"]]
            badges = "".join(
                f'<span class="badge {"saf" if s in ("S2","X1","X2") else "sig"}">{escape(SIGNAL_LABEL.get(s, s))}</span>'
                for s in sorted(set(sids)))
            fmts = "".join(f'<span class="badge fmt">{f}</span>'
                           for f in ["TXT"] + sorted(x for x in d["formats"] if x != "TXT"))
            units = " ".join(
                f'<code>{u["hcp_ref"]}</code>' + (f'<sub>#{u["block_index"]}</sub>' if u["block_index"] else "")
                for u in d["units"])
            P.append(f"""<details class="doc"><summary>
<span class="did">{d["doc_id"]}</span>
<span class="meta">{d["occurred_on"]} · {d["language"]} · 단위 {len(d["units"])}개</span>
{fmts}{badges}</summary>
<div class="units">HCP 블록: {units}</div>
<pre class="raw">{mark_text(d["raw"], d["signals"])}</pre></details>""")

    P.append('<div class="foot">생성: scripts/review_corpus.py · 원본: backend/data/corpus/ · '
             '이 페이지는 검수용 산출물이며 서비스 로직은 ground_truth를 읽지 않는다 (docs/03 §4).</div>'
             "</div></body></html>")

    OUT.write_text("\n".join(P), encoding="utf-8")
    print(f"검수 페이지 생성: {OUT.relative_to(ROOT)}  (문서 {len(docs)} · 단위 {len(manifest)} · 신호 {len(ground)})")


if __name__ == "__main__":
    main()
