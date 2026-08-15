"""Hypotheses & Screen & Board — docs/04 §4. 조회·사람 승인은 실제, Screen/Board 실행은 stub."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..access import get_role, scope_violation
from ..db import get_db
from ..models import BoardMinute, Claim, Decision, Hypothesis, ScreenFinding

router = APIRouter()


def _card(db: Session, h: Hypothesis, brief: bool = False) -> dict:
    out = {
        "id": h.id,
        "titleKo": h.title_ko,
        "kind": h.kind,
        "labelScope": "OUT_OF_LABEL" if h.kind == "DEVELOPMENT" else "IN_LABEL",
        "commercialActionBlocked": h.kind == "DEVELOPMENT",  # 절대 규칙 #5
        "status": h.status,
        "patientSegment": h.segment,
        "notBoardReadyReason": h.not_board_ready_reason,
    }
    if brief:
        return out
    agg = json.loads(h.created_from_aggregate_json or "{}")
    claims = db.execute(
        select(Claim).where(Claim.patient_segment == h.segment, Claim.status == "APPROVED")
    ).scalars().all()
    findings = db.execute(
        select(ScreenFinding).where(ScreenFinding.hypothesis_id == h.id).order_by(ScreenFinding.id)
    ).scalars().all()
    minutes = db.execute(
        select(BoardMinute).where(BoardMinute.hypothesis_id == h.id).order_by(BoardMinute.seq)
    ).scalars().all()
    decisions = db.execute(
        select(Decision).where(Decision.hypothesis_id == h.id).order_by(Decision.id)
    ).scalars().all()
    # 5단계 구분이 응답 구조에 그대로 반영된다 (절대 규칙 #8)
    out.update({
        "observedFacts": [
            {"statementKo": c.summary_ko, "claimId": c.claim_id} for c in claims
        ],
        "statisticalPatterns": (
            [{"statementKo": f"{agg.get('distinctHcp', 0)}인의 독립 HCP가 "
                             f"{agg.get('distinctRegions', 0)}개 권역에서 {agg.get('claimCount', 0)}회 언급",
              "computedBy": "SQL"}] if agg else []
        ),
        "aiInterpretations": (
            [{"statementKo": h.driver_summary_ko, "llmRunId": None}] if h.driver_summary_ko else []
        ),
        "strategicProposals": [],   # Board CEO 권고가 채운다 [오너: 소정 프롬프트 · 인혁 파이프라인]
        "approvedActions": [
            {"statementKo": d.rationale_ko, "decision": d.decision, "decidedBy": d.decided_by}
            for d in decisions if d.decision == "APPROVED"
        ],
        "screenFindings": [{
            "agent": f.agent, "findingType": f.finding_type, "statementKo": f.statement_ko,
            "sourceUrl": f.source_url, "sourceLocator": f.source_locator,
            "sourceAsOf": f.source_as_of, "caveatKo": f.caveat_ko,
        } for f in findings],
        "boardMinutes": [{"role": m.role, "positionKo": m.position_ko, "seq": m.seq} for m in minutes],
    })
    return out


@router.get("/hypotheses")
def list_hypotheses(db: Session = Depends(get_db), role: str = Depends(get_role)):
    rows = db.execute(select(Hypothesis).order_by(Hypothesis.id)).scalars().all()
    if role == "COMMERCIAL":
        rows = [h for h in rows if h.kind != "DEVELOPMENT"]  # docs/02 §9 — 목록에서도 차단
    return {"data": [_card(db, h, brief=True) for h in rows]}


@router.get("/hypotheses/{hyp_id}")
def get_hypothesis(hyp_id: str, db: Session = Depends(get_db), role: str = Depends(get_role)):
    h = db.get(Hypothesis, hyp_id)
    if not h:
        raise HTTPException(404, detail={"code": "NOT_FOUND", "message_ko": "가설이 없습니다."})
    if role == "COMMERCIAL" and h.kind == "DEVELOPMENT":
        raise scope_violation("COMMERCIAL 롤은 Development 가설에 접근할 수 없습니다.")
    return {"data": _card(db, h)}


@router.post("/hypotheses/{hyp_id}/screen")
def run_screen(hyp_id: str, role: str = Depends(get_role)):
    """Screen 4개 에이전트 실행 — [스캐폴딩 stub, 오너: 인혁 8/28 · 프롬프트: 소정].
    실제 구현: 결정론적 순서(FieldSignal→Evidence→Safety→Critic), SSE 스트림, 재시도 한도 2."""
    raise HTTPException(501, detail={"code": "NOT_IMPLEMENTED",
                                     "message_ko": "Screen 오케스트레이션은 stub — 8/28 [오너: 인혁]"})


@router.post("/hypotheses/{hyp_id}/board")
def run_board(hyp_id: str, role: str = Depends(get_role)):
    """Board 심의 실행 — [스캐폴딩 stub, 오너: 인혁 8/29 · 프롬프트: 소정]."""
    raise HTTPException(501, detail={"code": "NOT_IMPLEMENTED",
                                     "message_ko": "Board 파이프라인은 stub — 8/29 [오너: 인혁]"})


@router.post("/hypotheses/{hyp_id}/decision")
def decide(hyp_id: str, body: dict = Body(...), db: Session = Depends(get_db), role: str = Depends(get_role)):
    """사람의 최종 승인/보류/기각 — AI가 아니라 사람의 액션이므로 스캐폴딩 단계에서 실제 구현."""
    h = db.get(Hypothesis, hyp_id)
    if not h:
        raise HTTPException(404, detail={"code": "NOT_FOUND", "message_ko": "가설이 없습니다."})
    if role not in ("CLINICAL_STRATEGY",):  # 가설 승인 권한 (docs/02 §9)
        raise scope_violation(f"{role} 롤에는 가설 승인 권한이 없습니다.")
    decision = body.get("decision")
    if decision not in ("APPROVED", "HOLD", "REJECTED"):
        raise HTTPException(400, detail={"code": "BAD_DECISION", "message_ko": "decision은 APPROVED|HOLD|REJECTED"})
    follow_up = body.get("followUp") or {}
    db.add(Decision(
        hypothesis_id=h.id, decision=decision,
        decided_by=body.get("decidedBy") or role,
        rationale_ko=body.get("rationaleKo") or "",
        follow_up_json=json.dumps(follow_up, ensure_ascii=False),
        decided_at=datetime.now(timezone.utc).isoformat(),
    ))
    h.status = decision if decision != "HOLD" else "HOLD"
    db.commit()
    return {"data": _card(db, h)}
