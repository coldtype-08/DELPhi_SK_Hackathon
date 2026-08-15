"""시스템 — docs/04 §8. 시연 직전 육안 확인용."""

import hmac

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import CACHE_DIR, DEMO_OFFLINE, RESET_TOKEN
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


@router.post("/system/reset")
def reset_demo(x_reset_token: str = Header(default="")):
    """데모 시작 상태로 복원 — `reset_demo.sh`의 서버판 (docs/07 §5).

    심사위원 여러 명이 승인을 눌러 상태가 섞이므로, 매일 아침(또는 자정 자동)에 이걸 호출한다.
    RESET_TOKEN이 설정되지 않은 환경에서는 비활성 — 실수로 노출된 배포본이 초기화되지 않게.
    """
    if not RESET_TOKEN:
        raise HTTPException(503, detail={
            "code": "RESET_DISABLED",
            "message_ko": "RESET_TOKEN 환경변수가 설정되지 않아 리셋이 비활성 상태입니다.",
        })
    if not hmac.compare_digest(x_reset_token, RESET_TOKEN):
        raise HTTPException(401, detail={"code": "BAD_RESET_TOKEN", "message_ko": "리셋 토큰이 올바르지 않습니다."})

    from ..seed import seed

    counts = seed()
    return {"data": {"reset": True, **counts}}
