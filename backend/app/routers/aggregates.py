"""집계 — 전부 SQL 계산 (절대 규칙 #1·#3의 코드화). 응답에 computedBy: SQL을 항상 포함한다."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..access import COMMERCIAL_MIN_DISTINCT_HCP, allowed_domains, get_role
from ..db import get_db
from ..models import Claim, Hypothesis, Interaction

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/aggregates/signals")
def signal_aggregates(
    groupBy: str = "patient_segment",
    db: Session = Depends(get_db),
    role: str = Depends(get_role),
):
    domains = allowed_domains(role)
    base = (
        select(
            Claim.patient_segment,
            Claim.signal_type,
            func.count().label("claim_count"),
            func.count(func.distinct(Interaction.hcp_ref)).label("distinct_hcp"),
            func.count(func.distinct(Interaction.region)).label("distinct_regions"),
        )
        .join(Interaction, Interaction.interaction_id == Claim.interaction_id)
        .where(Claim.status == "APPROVED")            # APPROVED만 (절대 규칙 #3)
        .where(Claim.purpose_domain.in_(domains))     # 조회 게이트 (docs/02 §9)
        .group_by(Claim.patient_segment, Claim.signal_type)
    )
    rows = db.execute(base).all()

    suppressed = 0
    out = []
    for seg, sig, cnt, hcp, regions in rows:
        if role == "COMMERCIAL" and hcp < COMMERCIAL_MIN_DISTINCT_HCP:
            suppressed += 1  # 개인 역추정 차단 — 숨겼다는 사실은 숨기지 않는다
            continue
        # 월별 추이: substr(ISO date, 1, 7) = 'YYYY-MM' — ANSI 범위 (strftime 금지)
        monthly = db.execute(
            select(func.substr(Interaction.occurred_on, 1, 7).label("month"), func.count())
            .join(Claim, Claim.interaction_id == Interaction.interaction_id)
            .where(Claim.status == "APPROVED")
            .where(Claim.patient_segment == seg, Claim.signal_type == sig)
            .group_by(func.substr(Interaction.occurred_on, 1, 7))
            .order_by(func.substr(Interaction.occurred_on, 1, 7))
        ).all()
        out.append({
            "patientSegment": seg,
            "signalType": sig,
            "claimCount": cnt,
            "distinctHcp": hcp,
            "distinctRegions": regions,
            "monthly": [{"month": m, "count": c} for m, c in monthly],
        })

    data = {"computedBy": "SQL", "asOf": _now(), "rows": out}
    if role == "COMMERCIAL":
        data["suppressedRowCount"] = suppressed
    return {"data": data}


@router.get("/aggregates/kpis")
def kpis(db: Session = Depends(get_db), role: str = Depends(get_role)):
    domains = allowed_domains(role)
    approved = db.execute(
        select(func.count()).select_from(Claim)
        .where(Claim.status == "APPROVED", Claim.purpose_domain.in_(domains))
    ).scalar_one()
    distinct_hcp = db.execute(
        select(func.count(func.distinct(Interaction.hcp_ref)))
        .select_from(Claim)
        .join(Interaction, Interaction.interaction_id == Claim.interaction_id)
        .where(Claim.status == "APPROVED", Claim.purpose_domain.in_(domains))
    ).scalar_one()
    open_hyp = db.execute(
        select(func.count()).select_from(Hypothesis)
        .where(Hypothesis.status.not_in(["APPROVED", "REJECTED"]))
    ).scalar_one()
    pending = db.execute(
        select(func.count()).select_from(Claim)
        .where(Claim.status == "CANDIDATE", Claim.purpose_domain.in_(domains))
    ).scalar_one()
    return {"data": {
        "computedBy": "SQL", "asOf": _now(),
        "approvedClaims": approved, "distinctHcp": distinct_hcp,
        "openHypotheses": open_hyp, "pendingReviews": pending,
    }}
