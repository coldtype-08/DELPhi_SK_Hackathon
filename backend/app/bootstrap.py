"""Contract 부트스트랩 — 원석을 읽고 **스키마 자체**를 AI가 제안한다 (08/22 신설, 데모 ①).

[cross] 엔진 층은 인혁 오너십

보통은 사람이 스키마를 먼저 정하고 데이터를 맞춘다. 그러면 정한 사람이 아는 것만 뽑힌다.
여기서는 원석이 먼저 말하고, 사람이 그 제안을 보고 확정한다 — 그 기록이 `/contract/provenance` 화면이다.

**AI에게는 스키마를 바꿀 권한이 없다** (절대 규칙 #4). 이 모듈은 *제안*만 만들고,
활성 Contract는 건드리지 않는다. 채택은 Data Steward가 화면에서 한다.

숫자는 여기 파이썬이 센다 (절대 규칙 #1):
- AI가 적은 `observed_in_docs`는 **버리고**, 근거 인용이 실제로 몇 개 문서에서 발견되는지 서버가 다시 센다
- 원문에서 찾을 수 없는 인용은 폐기하고, 근거가 0개가 된 제안 항목은 **제안 자체를 폐기**한다 (절대 규칙 #2)
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .agents import get_agent
from .contract import load_active_contract
from .llm import call_agent, load_prompt, render
from .models import Document

AGENT = "contract_architect"
EXCERPT_CHARS = 6000     # 문서당 발췌 상한 — 표본 문서 수를 늘리는 편이 낫다


def _sample(db: Session, limit: int, source_types: list[str] | None) -> list[Document]:
    """유형이 골고루 섞이도록 뽑는다. 한 유형만 보면 그 유형의 서식이 스키마가 되어 버린다."""
    docs = db.execute(select(Document).order_by(Document.id)).scalars().all()
    if not docs:
        return []
    buckets: dict[str, list[Document]] = {}
    for d in docs:
        buckets.setdefault(d.source_format or "TXT", []).append(d)
    out, i = [], 0
    keys = sorted(buckets)
    while len(out) < limit and any(buckets[k] for k in keys):
        k = keys[i % len(keys)]
        if buckets[k]:
            out.append(buckets[k].pop(0))
        i += 1
    return out[:limit]


def _excerpts(docs: list[Document]) -> str:
    parts = []
    for d in docs:
        body = d.raw_text[:EXCERPT_CHARS]
        cut = "\n…(이하 생략)" if len(d.raw_text) > EXCERPT_CHARS else ""
        parts.append(f"===== 문서 {d.id} ({d.source_format}) =====\n{body}{cut}")
    return "\n\n".join(parts)


def _verify_quotes(docs: list[Document], quotes: list[str]) -> tuple[list[dict], int]:
    """인용 → (검증된 근거, 폐기 수). 원문에 없는 인용은 근거로 세지 않는다."""
    kept, dropped = [], 0
    for q in quotes or []:
        q = (q or "").strip()
        hit = next((d for d in docs if q and q in d.raw_text), None)
        if hit is None:
            dropped += 1
            continue
        start = hit.raw_text.find(q)
        kept.append({"docId": hit.id, "quote": q, "charStart": start, "charEnd": start + len(q)})
    return kept, dropped


def propose_contract(db: Session, *, sample_size: int = 12, force: bool = False) -> dict:
    """원석 표본 → 스키마 제안. 활성 Contract는 변경하지 않는다."""
    docs = _sample(db, sample_size, None)
    if not docs:
        raise ValueError("원석이 없습니다 — 먼저 시드하세요.")
    types = sorted({d.source_format for d in docs})

    prompt, _ = load_prompt(get_agent(AGENT).persona_file)
    system_text = render(prompt, {
        "DOC_COUNT": str(len(docs)),
        "SOURCE_TYPES": ", ".join(types),
    })
    out = call_agent(db, AGENT, system_text=system_text,
                     input_text=_excerpts(docs), force=force)

    active = load_active_contract(db)
    existing = set(active["fields"].keys())

    fields, total_dropped = [], 0
    for f in out.get("fields") or []:
        ev, dropped = _verify_quotes(docs, f.get("evidence_quotes"))
        total_dropped += dropped
        if not ev:
            # 근거가 하나도 남지 않았다 → 제안 폐기 (절대 규칙 #2)
            total_dropped += 1
            continue
        values = []
        for v in f.get("values") or []:
            vq, vdrop = _verify_quotes(docs, [v.get("evidence_quote")])
            total_dropped += vdrop
            if vq:
                values.append({"value": v.get("value"), "labelKo": v.get("label_ko"),
                               "evidence": vq[0]})
        fields.append({
            "key": f.get("key"),
            "labelKo": f.get("label_ko"),
            "kind": f.get("kind"),
            "rationaleKo": f.get("rationale_ko"),
            "values": values,
            "evidence": ev,
            # AI가 적은 수치는 쓰지 않는다 — 검증된 인용이 몇 개 문서에서 나왔는지 서버가 센다
            "observedInDocs": len({e["docId"] for e in ev}),
            "alreadyInContract": f.get("key") in existing,
        })

    fields.sort(key=lambda f: (-f["observedInDocs"], f["key"] or ""))
    return {
        "sampledDocuments": [d.id for d in docs],
        "sourceFormats": types,
        "activeContractVersion": str(active["version"]),
        "fields": fields,
        "rejected": [{"key": r.get("key"), "reasonKo": r.get("reason_ko")}
                     for r in out.get("rejected") or []],
        "droppedEvidence": total_dropped,
        "note_ko": ("이 제안은 초안입니다. 활성 Contract는 변경되지 않았습니다 — "
                    "채택은 Data Steward 승인으로만 이뤄집니다 (절대 규칙 #4)."),
    }
