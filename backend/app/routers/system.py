"""시스템 — docs/04 §8. 시연 직전 육안 확인용."""

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import CACHE_DIR, DEMO_OFFLINE
from ..contract import load_active_contract
from ..db import get_db
from ..models import Document

router = APIRouter()


@router.get("/health")
def health(db: Session = Depends(get_db)):
    seeded_at = db.execute(select(func.max(Document.imported_at))).scalar_one_or_none()
    snapshots = sorted(CACHE_DIR.glob("*.json")) if CACHE_DIR.exists() else []
    return {"data": {
        "ok": True,
        "demoOffline": DEMO_OFFLINE,
        "activeContractVersion": load_active_contract(db)["version"],
        "dbSeededAt": seeded_at,
        "cacheSnapshotAsOf": snapshots[-1].stem.split("_")[-1] if snapshots else None,
    }}
