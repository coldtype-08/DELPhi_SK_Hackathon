"""발언 귀속 — 한 문서 안에서 "누가 말했는지"를 AI가 가른다 (08/22 신설).

[cross] 엔진 층은 인혁 오너십

**왜 이 파일이 생겼나.** 이전까지 `interactions`(의료진별 블록)는 합성 코퍼스 생성기가
`manifest.jsonl`에 적어 준 정답을 `seed.py`가 그대로 적재한 것이었다. 즉 **"AI가 의료진별로
분리했다"는 말이 사실이 아니었다** — 생성기가 답을 넘겨준 것이다. 실제 사내 원석에는 manifest가
없으므로, 이 구간을 가르는 일 자체가 AI의 몫이어야 한다.

**그런데 정답을 지우지는 않는다.** 생성기 분할은 **채점 기준**으로 남긴다:
- `attribute_document()` 는 AI에게 문서를 통째로 주고 구간을 가르게 한 뒤, 저장된 분할과 대조해 점수를 낸다
- 점수는 `3_검증결과`의 실측치가 되고, 화면에서는 "AI가 가른 경계"와 "정답 경계"를 겹쳐 보여준다
- 정답이 없는 진짜 원석에서는 `blocks` 결과만 쓰면 된다 (채점 부분이 비어서 나온다)

숫자는 전부 여기 파이썬이 센다 (절대 규칙 #1). AI는 **경계 문자열을 인용**할 뿐이고,
문자 위치는 `str.find`가 찾는다 — 인용이 원문과 다르면 그 구간은 버려진다 (절대 규칙 #2).
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from .agents import get_agent
from .llm import call_agent, load_prompt, render
from .models import Document, Interaction

AGENT = "hcp_attributor"


def build_system_text(doc: Document, source_type: str, occurred_on: str) -> str:
    prompt, _ = load_prompt(get_agent(AGENT).persona_file)
    return render(prompt, {
        "SOURCE_TYPE": source_type or "미상",
        "OCCURRED_ON": occurred_on or "미상",
    })


# ── 경계 문자열 → 문자 위치 (절대 규칙 #1·#2) ───────────────────────────────


def _unique_find(text: str, needle: str, start: int = 0) -> int:
    """유일하게 나타나는 위치. 없거나 두 번 이상이면 -1 — 위치를 정할 수 없으면 쓰지 않는다."""
    if not needle or not needle.strip():
        return -1
    i = text.find(needle, start)
    if i < 0:
        return -1
    if text.find(needle, i + 1) >= 0:
        return -1
    return i


def _resolve(doc_text: str, blocks: list[dict]) -> tuple[list[dict], list[dict]]:
    """AI가 인용한 경계 → (해결된 구간, 버려진 구간+사유). 순서·겹침도 여기서 검사한다."""
    resolved: list[dict] = []
    dropped: list[dict] = []
    cursor = 0
    for b in blocks:
        sq = (b.get("start_quote") or "").strip()
        eq = (b.get("end_quote") or "").strip()
        s = _unique_find(doc_text, sq, cursor)
        if s < 0:
            s = _unique_find(doc_text, sq)          # 순서가 어긋났을 수도 있으니 전역 재시도
        if s < 0:
            dropped.append({**b, "reason": "START_QUOTE_NOT_FOUND"})
            continue
        e = doc_text.find(eq, s)
        if e < 0:
            dropped.append({**b, "reason": "END_QUOTE_NOT_FOUND"})
            continue
        e += len(eq)
        if resolved and s < resolved[-1]["charEnd"]:
            dropped.append({**b, "reason": "OVERLAPS_PREVIOUS"})
            continue
        resolved.append({
            "hcpSurface": b.get("hcp_surface"),
            "specialtySurface": b.get("specialty_surface"),
            "institutionSurface": b.get("institution_surface"),
            "confidence": b.get("confidence") or "UNCERTAIN",
            "boundaryNoteKo": b.get("boundary_note_ko"),
            "charStart": s, "charEnd": e,
        })
        cursor = e
    return resolved, dropped


# ── 채점: AI 분할 vs 저장된 분할 ────────────────────────────────────────────


def _overlap(a: tuple[int, int], b: tuple[int, int]) -> int:
    return max(0, min(a[1], b[1]) - max(a[0], b[0]))


def _score(resolved: list[dict], truth: list[Interaction]) -> dict | None:
    """구간 경계가 얼마나 맞았나. 정답 분할이 없는 문서(진짜 원석)면 None."""
    spans = [(t.doc_char_start, t.doc_char_end) for t in truth
             if t.doc_char_start is not None and t.doc_char_end is not None]
    if not spans:
        return None

    matched, ious = 0, []
    for lo, hi in spans:
        best, best_iou = None, 0.0
        for r in resolved:
            ov = _overlap((lo, hi), (r["charStart"], r["charEnd"]))
            if ov <= 0:
                continue
            union = max(hi, r["charEnd"]) - min(lo, r["charStart"])
            iou = ov / union if union else 0.0
            if iou > best_iou:
                best, best_iou = r, iou
        ious.append(best_iou)
        if best_iou >= 0.8:          # 경계가 실질적으로 같다고 볼 수 있는 선
            matched += 1
    return {
        "truthBlocks": len(spans),
        "aiBlocks": len(resolved),
        "matched": matched,
        "missed": len(spans) - matched,
        "extra": max(0, len(resolved) - len(spans)),
        "meanIou": round(sum(ious) / len(ious), 3) if ious else 0.0,
        "blockRecall": round(matched / len(spans), 3),
    }


# ── 진입점 ──────────────────────────────────────────────────────────────────


def attribute_document(db: Session, doc_id: str, *, refresh: bool = False) -> dict:
    """문서 1건을 AI에게 통째로 주고 발언 구간을 가르게 한 뒤, 저장된 분할과 대조한다.

    **DB에 쓰지 않는다.** 이 함수는 보여 주고 채점하는 용도이고, 적재는 `sense.extract_document`가 한다.
    """
    doc = db.get(Document, doc_id)
    if not doc:
        raise ValueError(f"문서가 없습니다: {doc_id}")
    truth = db.execute(
        select(Interaction).where(Interaction.document_id == doc_id)
        .order_by(Interaction.block_index, Interaction.interaction_id)
    ).scalars().all()
    first = truth[0] if truth else None

    out = call_agent(
        db, AGENT,
        system_text=build_system_text(doc, first.source_type if first else "",
                                      first.occurred_on if first else ""),
        input_text=doc.raw_text,
        force=refresh,   # 캐시 무시 — 프롬프트를 고친 뒤에만
    )
    resolved, dropped = _resolve(doc.raw_text, out.get("blocks") or [])
    covered = sum(b["charEnd"] - b["charStart"] for b in resolved)
    return {
        "documentId": doc_id,
        "blocks": resolved,
        "dropped": [{"hcpSurface": d.get("hcp_surface"), "reason": d["reason"]} for d in dropped],
        "unattributedNoteKo": out.get("unattributed_note_ko"),
        "coverageRatio": round(covered / len(doc.raw_text), 3) if doc.raw_text else 0.0,
        "confidenceCounts": {
            c: sum(1 for b in resolved if b["confidence"] == c)
            for c in ("CLEAR", "INFERRED", "UNCERTAIN")
        },
        "score": _score(resolved, truth),
    }
