#!/usr/bin/env python3
"""
seed_db.py — 코퍼스 → DB 적재 CLI (docs/03 §5.5).

실제 로직은 `backend/app/seed.py`에 있다 (배포 환경에서 서버가 스스로 시드해야 하므로 backend 패키지 소유).
이 파일은 문서에 적힌 명령을 유지하는 얇은 진입점이다.

사용 (레포 루트에서):
  uv run --project backend python scripts/seed_db.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.seed import seed  # noqa: E402

if __name__ == "__main__":
    counts = seed()
    print(
        f"시드 완료: documents {counts['documents']} · interactions {counts['interactions']} · "
        f"claims(CANDIDATE) {counts['claims']} · hypotheses {counts['hypotheses']} · "
        f"vocab {counts['vocab']} · contract v0.1 ACTIVE"
    )
