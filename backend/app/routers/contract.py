"""Contract & SCP — docs/04 §5. 조회는 실제, SCP 승인→버전 활성화는 stub [오너: 인혁 8/30]."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access import get_role
from ..bootstrap import propose_contract
from ..contract import load_active_contract
from ..llm import LlmUnavailable
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


@router.post("/contract/propose")
def propose_contract_route(
    sampleSize: int = 12,
    force: bool = False,
    db: Session = Depends(get_db),
    role: str = Depends(get_role),
):
    """Contract 부트스트랩 — 원석 표본을 읽고 **뽑을 항목 자체**를 AI가 제안한다 (08/22, 데모 ①).

    활성 Contract는 변경되지 않는다 (절대 규칙 #4). 채택은 Data Steward 승인으로만.
    각 제안 항목의 `observedInDocs`는 AI가 적은 값이 아니라 **서버가 검증된 인용으로 다시 센 값**이다.
    """
    if role not in ("DATA_STEWARD", "MEDICAL_AFFAIRS", "CLINICAL_STRATEGY"):
        raise HTTPException(403, detail={
            "code": "PURPOSE_SCOPE_VIOLATION",
            "message_ko": f"{role} 롤은 Contract 제안을 실행할 수 없습니다."})
    if not 3 <= sampleSize <= 40:
        raise HTTPException(400, detail={
            "code": "SAMPLE_SIZE_OUT_OF_RANGE",
            "message_ko": "표본은 3~40건 사이여야 합니다."})
    try:
        return {"data": propose_contract(db, sample_size=sampleSize, force=force)}
    except LlmUnavailable as e:
        raise HTTPException(503, detail={"code": "LLM_UNAVAILABLE", "message_ko": str(e)})
