"""Documents & Sense — docs/04 §1. 원문 조회·추출 실행 모두 실제 동작 (08/22) [오너: 인혁]."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..access import get_role, require_raw_text_access
from ..db import get_db
from ..llm import LlmUnavailable
from ..models import Claim, Document, Interaction
from ..sense import extract_document

router = APIRouter()


def _claim_counts(db: Session, doc_id: str) -> dict:
    rows = db.execute(
        select(Claim.status, func.count())
        .join(Interaction, Interaction.interaction_id == Claim.interaction_id)
        .where(Interaction.document_id == doc_id)
        .group_by(Claim.status)
    ).all()
    counts = {s.lower(): c for s, c in rows}
    return {
        "candidate": counts.get("candidate", 0),
        "approved": counts.get("approved", 0),
        "rejected": counts.get("rejected", 0),
    }


@router.get("/documents")
def list_documents(db: Session = Depends(get_db), role: str = Depends(get_role)):
    docs = db.execute(select(Document)).scalars().all()
    out = []
    for d in docs:
        first = db.execute(
            select(Interaction).where(Interaction.document_id == d.id).order_by(Interaction.block_index)
        ).scalars().first()
        out.append({
            "id": d.id,
            "sourceType": first.source_type if first else None,
            "sourceFormat": d.source_format,
            "language": d.language,
            "occurredOn": first.occurred_on if first else None,
            "interactionCount": db.execute(
                select(func.count()).where(Interaction.document_id == d.id)
            ).scalar_one(),
            "claimCounts": _claim_counts(db, d.id),
        })
    out.sort(key=lambda x: (x["occurredOn"] or "", x["id"]))
    return {"data": out}


@router.get("/documents/{doc_id}")
def get_document(doc_id: str, db: Session = Depends(get_db), role: str = Depends(get_role)):
    require_raw_text_access(role)  # 원문 접근 게이트 (docs/02 §9)
    d = db.get(Document, doc_id)
    if not d:
        raise HTTPException(404, detail={"code": "NOT_FOUND", "message_ko": "문서가 없습니다."})
    inters = db.execute(
        select(Interaction).where(Interaction.document_id == doc_id).order_by(Interaction.block_index)
    ).scalars().all()
    first = inters[0] if inters else None
    return {"data": {
        "id": d.id,
        "sourceType": first.source_type if first else None,
        "sourceFormat": d.source_format,
        "language": d.language,
        "occurredOn": first.occurred_on if first else None,
        "rawText": d.raw_text,
        "interactions": [{
            "interactionId": i.interaction_id,
            "hcpRef": i.hcp_ref,
            "region": i.region,
            "specialty": i.hcp_specialty,
            "setting": i.setting,
            "blockIndex": i.block_index,
            "docCharStart": i.doc_char_start,
            "docCharEnd": i.doc_char_end,
            "maskedSpans": json.loads(i.masked_spans_json or "[]"),
        } for i in inters],
        "claimCounts": _claim_counts(db, doc_id),
    }}


def _camel_stats(stats: dict) -> dict:
    """내부는 snake_case, API 응답은 camelCase (CLAUDE.md 코딩 컨벤션)."""
    def camel(k: str) -> str:
        head, *rest = k.split("_")
        return head + "".join(w.capitalize() for w in rest)
    return {camel(k): v for k, v in stats.items()}


@router.post("/documents/{doc_id}/extract")
def extract_document_route(
    doc_id: str,
    force: bool = False,
    db: Session = Depends(get_db),
    role: str = Depends(get_role),
):
    """Sense 추출 실행 — 원석 1건 → 의료진 블록별 claim 후보 (08/22 구현, docs/04 §1).

    LLM은 무엇이 신호인지 고르고 인용문을 복사할 뿐이고, 인용문 대조·오프셋·등급·
    안전성 분리는 전부 `app/sense.py`의 결정론 코드가 한다 (절대 규칙 #1·#2·#6).
    """
    require_raw_text_access(role)   # 원문을 읽는 작업이므로 원문 게이트와 동일
    if not db.get(Document, doc_id):
        raise HTTPException(404, detail={"code": "NOT_FOUND", "message_ko": "문서가 없습니다."})
    try:
        return {"data": _camel_stats(extract_document(db, doc_id, force=force))}
    except LlmUnavailable as e:
        raise HTTPException(503, detail={"code": "LLM_UNAVAILABLE", "message_ko": str(e)})
