"""환경 설정 — .env(레포 루트 → backend/ 순서)를 읽는다. 키는 커밋 금지 (docs/06 §5)."""

import os
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent


def _load_env():
    for env_path in (ROOT_DIR / ".env", BACKEND_DIR / ".env"):
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"'))


_load_env()

# DB 경로는 cwd와 무관하게 backend/data/delphi.db 로 고정 (env로 재정의 가능 — docs/01 §6)
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'data' / 'delphi.db'}")
DEMO_OFFLINE = os.environ.get("DEMO_OFFLINE", "0") == "1"
MODEL_EXTRACT = os.environ.get("DELPHI_MODEL_EXTRACT", "claude-sonnet-5")
MODEL_BOARD = os.environ.get("DELPHI_MODEL_BOARD", "claude-opus-5")
ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001"
    ).split(",") if o.strip()
]
CORPUS_DIR = BACKEND_DIR / "data" / "corpus"
CACHE_DIR = BACKEND_DIR / "data" / "cache"
