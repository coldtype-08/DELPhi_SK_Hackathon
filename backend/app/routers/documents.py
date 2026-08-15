"""Documents & Sense — docs/04 §1. 원문 조회는 실제 DB, 추출 실행은 stub [오너: 인혁]."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..access import get_role, require_raw_text_access
from ..db import get_db
from ..models import Claim, Document, Interaction

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


@router.post("/documents/{doc_id}/extract")
def extract_document(doc_id: str, role: str = Depends(get_role)):
    """Sense 추출 실행 — [스캐폴딩 stub, 오너: 인혁 8/21].

    실제 구현: llm.py 경유 구조화 추출 → evidence 검증(원문 일치) → claims 저장 →
    SAFETY_CANDIDATE 분리(절대 규칙 #6) → unmapped_terms 적재.
    개발용 CANDIDATE는 시드에 이미 포함되어 있다 (scripts/seed_db.py).
    """
    raise HTTPException(501, detail={
        "code": "NOT_IMPLEMENTED",
        "message_ko": "추출 파이프라인은 stub입니다 — 8/21 'stub을 실제 LLM 추출로 교체' [오너: 인혁]",
    })
