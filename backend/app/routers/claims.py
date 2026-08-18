"""Claims 검토·승인 — docs/04 §2. 검토 큐 정렬은 결정론(docs/02 §5.5), 프론트가 정렬하지 않는다."""

import json
from datetime import datetime, timezone

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..access import allowed_domains, get_role, require_raw_text_access, scope_violation
from ..contract import load_active_contract, derive_label_scope, derive_purpose_domain, validate_claim_fields
from ..db import get_db
from ..models import Claim, Interaction

router = APIRouter()

_GRADE_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}  # 저등급 우선 (원문 불일치 위험 큰 것부터)


def _to_dict(c: Claim) -> dict:
    return {
        "id": c.claim_id,
        "interactionId": c.interaction_id,
        "signalType": c.signal_type,
        "patientSegment": c.patient_segment,
        "journeyStage": c.journey_stage,
        "barrierType": c.barrier_type,
        "solicitation": c.solicitation,
        "sentiment": c.sentiment,
        "indicationMention": c.indication_mention,
        "concomitantDrugs": c.concomitant_drugs,
        "administrationNote": c.administration_note,
        "summaryKo": c.summary_ko,
        "verbatimQuote": c.verbatim_quote,
        "evidence": _camel_evidence(json.loads(c.evidence_json)),
        "purposeDomain": c.purpose_domain,
        "labelScope": c.label_scope,
        "reviewGrade": c.review_grade,
        "status": c.status,
        "contractVersion": c.contract_version,
    }


def _camel_evidence(e: dict) -> dict:
    return {"docId": e["doc_id"], "charStart": e["char_start"], "charEnd": e["char_end"]}


@router.get("/claims")
def list_claims(
    status: str | None = None,
    documentId: str | None = None,
    queue: str | None = None,
    db: Session = Depends(get_db),
    role: str = Depends(get_role),
):
    require_raw_text_access(role)  # claim에는 verbatim이 있다 → 원문 접근 게이트와 동일
    domains = allowed_domains(role)
    q = select(Claim).where(Claim.purpose_domain.in_(domains))
    if status:
        q = q.where(Claim.status == status)
    if documentId:
        sub = select(Interaction.interaction_id).where(Interaction.document_id == documentId)
        q = q.where(Claim.interaction_id.in_(sub))
    claims = db.execute(q).scalars().all()

    if queue == "review":
        # 위험 기반 검토 큐 (docs/02 §5.5): ① 가설 후보 참조 → ② 반복 수 상위 → ③ 저등급 우선
        # 스캐폴딩 단계: 가설-claim 연결이 아직 없어 ②③만 적용 [①은 오너: 인혁]
        counts = dict(db.execute(
            select(Claim.patient_segment + "|" + Claim.signal_type, func.count())
            .where(Claim.status == "CANDIDATE")
            .group_by(Claim.patient_segment, Claim.signal_type)
        ).all())
        claims = [c for c in claims if c.status == "CANDIDATE"]
        claims.sort(key=lambda c: (
            -counts.get(f"{c.patient_segment}|{c.signal_type}", 0),
            _GRADE_ORDER.get(c.review_grade, 0),
            c.claim_id,
        ))
        out = []
        for c in claims:
            row = _to_dict(c)
            n = counts.get(f"{c.patient_segment}|{c.signal_type}", 0)
            row["queueReasonKo"] = f"같은 신호({c.patient_segment}·{c.signal_type}) 반복 {n}건 — 반복 수 상위"
            out.append(row)
        return {"data": out}

    return {"data": [_to_dict(c) for c in sorted(claims, key=lambda c: c.claim_id)]}


@router.patch("/claims/{claim_id}")
def review_claim(
    claim_id: str,
    body: dict = Body(...),
    db: Session = Depends(get_db),
    role: str = Depends(get_role),
):
    require_raw_text_access(role)
    c = db.get(Claim, claim_id)
    if not c:
        raise HTTPException(404, detail={"code": "NOT_FOUND", "message_ko": "claim이 없습니다."})
    if c.purpose_domain not in allowed_domains(role):
        raise scope_violation(f"{role} 롤은 이 claim({c.purpose_domain})을 검토할 수 없습니다.")

    action = body.get("action")
    if action not in ("approve", "reject", "amend"):
        raise HTTPException(400, detail={"code": "BAD_ACTION", "message_ko": "action은 approve|reject|amend"})

    contract = load_active_contract(db)
    if action == "amend":
        am = body.get("amendments") or {}
        fields = {
            "signal_type": am.get("signalType", c.signal_type),
            "patient_segment": am.get("patientSegment", c.patient_segment),
            "journey_stage": am.get("journeyStage", c.journey_stage),
            "barrier_type": am.get("barrierType", c.barrier_type),
            "solicitation": am.get("solicitation", c.solicitation),
            "sentiment": am.get("sentiment", c.sentiment),
        }
        errors = validate_claim_fields(contract, fields)
        if errors:
            raise HTTPException(400, detail={"code": "CONTRACT_VIOLATION", "message_ko": "; ".join(errors)})
        c.signal_type = fields["signal_type"]
        c.patient_segment = fields["patient_segment"]
        c.journey_stage = fields["journey_stage"]
        c.barrier_type = fields["barrier_type"]
        c.solicitation = fields["solicitation"]
        c.sentiment = fields["sentiment"]
        c.indication_mention = am.get("indicationMention", c.indication_mention)
        c.concomitant_drugs = am.get("concomitantDrugs", c.concomitant_drugs)
        c.administration_note = am.get("administrationNote", c.administration_note)
        if am.get("summaryKo"):
            c.summary_ko = am["summaryKo"]
        # 수정 후에도 자동판정 재계산 (절대 규칙 #5 코드화)
        c.label_scope = derive_label_scope(contract, c.patient_segment, c.signal_type)
        c.purpose_domain = derive_purpose_domain(c.signal_type)

    c.status = "APPROVED" if action in ("approve", "amend") else "REJECTED"
    c.reviewed_by = body.get("reviewedBy") or role
    c.reviewed_at = datetime.now(timezone.utc).isoformat()
    db.commit()
    return {"data": _to_dict(c)}
