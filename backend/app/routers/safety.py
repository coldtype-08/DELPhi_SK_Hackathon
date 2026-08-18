"""Safety & 로그 & 추적 — docs/04 §7. safety_candidates는 SAFETY 롤 전용 (절대 규칙 #6)."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access import get_role, scope_violation
from ..db import get_db
from ..models import BlockedLog, LlmRun, SafetyCandidate

router = APIRouter()


@router.get("/safety/candidates")
def list_safety(db: Session = Depends(get_db), role: str = Depends(get_role)):
    if role != "SAFETY":
        raise scope_violation("safety_candidates는 SAFETY 롤 전용입니다.")
    rows = db.execute(select(SafetyCandidate).order_by(SafetyCandidate.id)).scalars().all()
    return {"data": [{
        "id": s.id, "interactionId": s.interaction_id, "verbatimQuote": s.verbatim_quote,
        "evidence": json.loads(s.evidence_json),
        "eventTerms": s.event_terms, "severityNote": s.severity_note, "productNamed": s.product_named,
        "routedAt": s.routed_at, "status": s.status,
    } for s in rows]}


@router.patch("/safety/candidates/{cand_id}")
def ack_safety(cand_id: str, body: dict = Body(default={}), db: Session = Depends(get_db),
               role: str = Depends(get_role)):
    if role != "SAFETY":
        raise scope_violation("safety_candidates는 SAFETY 롤 전용입니다.")
    s = db.get(SafetyCandidate, cand_id)
    if not s:
        raise HTTPException(404, detail={"code": "NOT_FOUND", "message_ko": "대상이 없습니다."})
    s.status = "ACKNOWLEDGED"
    db.commit()
    return {"data": {"id": s.id, "status": s.status, "ackedAt": datetime.now(timezone.utc).isoformat()}}


@router.get("/logs/blocked")
def blocked_logs(db: Session = Depends(get_db), role: str = Depends(get_role)):
    rows = db.execute(select(BlockedLog).order_by(BlockedLog.id)).scalars().all()
    return {"data": [{
        "id": b.id, "source": b.source, "reasonCode": b.reason_code,
        "detailKo": b.detail_ko, "payload": json.loads(b.payload_json or "{}"), "createdAt": b.created_at,
    } for b in rows]}


@router.get("/llm-runs/{run_id}")
def llm_run(run_id: int, db: Session = Depends(get_db), role: str = Depends(get_role)):
    """AI 산출물의 '생성 조건 보기' (docs/01 §7) — 모델·prompt·schema·parser·외부데이터 시점."""
    r = db.get(LlmRun, run_id)
    if not r:
        raise HTTPException(404, detail={"code": "NOT_FOUND", "message_ko": "기록이 없습니다."})
    return {"data": {
        "model": r.model, "promptFile": r.prompt_file, "promptVersion": r.prompt_version,
        "schemaName": r.schema_name, "parserVersion": r.parser_version,
        "externalDataAsOf": r.external_data_as_of, "latencyMs": r.latency_ms, "createdAt": r.created_at,
    }}
