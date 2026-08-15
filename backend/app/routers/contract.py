"""Contract & SCP — docs/04 §5. 조회는 실제, SCP 승인→버전 활성화는 stub [오너: 인혁 8/30]."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access import get_role
from ..contract import load_active_contract
from ..db import get_db
from ..models import SchemaChangeProposal

router = APIRouter()


@router.get("/contract/active")
def active_contract(db: Session = Depends(get_db), role: str = Depends(get_role)):
    c = load_active_contract(db)
    return {"data": {
        "version": c["version"],
        "product": c.get("product"),
        "fields": {
            key: {
                "labelKo": spec["label_ko"],
                "required": bool(spec.get("required")),
                "requiredIf": spec.get("required_if"),
                "values": [
                    {"value": v["value"], "labelKo": v["label_ko"],
                     **({"labelScope": v["label_scope"]} if v.get("label_scope") else {}),
                     **({"isNew": True} if v.get("is_new") else {})}
                    for v in spec.get("values", [])
                ],
            }
            for key, spec in c["fields"].items()
        },
    }}


@router.get("/contract/proposals")
def list_proposals(db: Session = Depends(get_db), role: str = Depends(get_role)):
    rows = db.execute(select(SchemaChangeProposal).order_by(SchemaChangeProposal.id)).scalars().all()
    return {"data": [{
        "id": p.id, "kind": p.kind, "targetField": p.target_field, "proposedValue": p.proposed_value,
        "rationaleKo": p.rationale_ko, "exampleClaimIds": json.loads(p.example_claim_ids_json or "[]"),
        "occurrenceCount": p.occurrence_count, "distinctHcpCount": p.distinct_hcp_count,
        "impactNoteKo": p.impact_note_ko, "status": p.status,
    } for p in rows]}


@router.post("/contract/proposals/{proposal_id}/decision")
def decide_proposal(proposal_id: int, role: str = Depends(get_role)):
    """SCP 승인 → 새 버전 ACTIVE화 → form-config 즉시 반영 — [스캐폴딩 stub, 오너: 인혁 8/30].
    구현 규칙: 추가(additive)만 허용, v0.2 전환 안전 규칙 준수 (docs/02 §7.5)."""
    raise HTTPException(501, detail={"code": "NOT_IMPLEMENTED",
                                     "message_ko": "SCP 승인→버전 활성화는 stub — 8/30 [오너: 인혁]"})
