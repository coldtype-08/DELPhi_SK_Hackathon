"""Field 전용 — docs/04 §6. form-config는 활성 contract에서 실제 생성 (v0.2 데모의 축)."""

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access import get_role
from ..contract import form_config, load_active_contract
from ..db import get_db
from ..models import Decision

router = APIRouter()


@router.get("/field/form-config")
def get_form_config(db: Session = Depends(get_db), role: str = Depends(get_role)):
    contract = load_active_contract(db)
    # Board 승인 후속 질문 → 체크리스트 항목 (루프가 닫히는 지점, docs/00 §1.5 #7)
    items = []
    for d in db.execute(select(Decision).where(Decision.decision == "APPROVED")).scalars():
        fu = json.loads(d.follow_up_json or "{}")
        if fu.get("checklistItemKo"):
            items.append({"labelKo": fu["checklistItemKo"], "origin": "BOARD_FOLLOW_UP"})
    return {"data": form_config(contract, items)}


@router.get("/field/briefing")
def briefing(hcpRef: str | None = None, db: Session = Depends(get_db), role: str = Depends(get_role)):
    items = []
    for d in db.execute(select(Decision).where(Decision.decision == "APPROVED")).scalars():
        fu = json.loads(d.follow_up_json or "{}")
        if fu.get("checklistItemKo"):
            items.append({"labelKo": fu["checklistItemKo"], "origin": "BOARD_FOLLOW_UP",
                          "hypothesisId": d.hypothesis_id})
    return {"data": {"hcpRef": hcpRef, "checklist": items}}


@router.post("/field/interactions")
def submit_interaction(role: str = Depends(get_role)):
    """신규 면담 제출 → 구조화 후보 + AE 분기 + 마스킹 — [스캐폴딩 stub, 오너: 소정·인혁 8/25].
    실제 구현: 마스킹 → llm.py 추출 → SAFETY_CANDIDATE 분리(절대 규칙 #6) → claim 후보 반환."""
    raise HTTPException(501, detail={"code": "NOT_IMPLEMENTED",
                                     "message_ko": "Field 수집 파이프라인은 stub — 8/25 [오너: 소정·인혁]"})
