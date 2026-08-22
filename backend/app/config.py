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

# DB 경로는 cwd와 무관하게 backend/data/delphi.db 로 고정.
# 클라우드 배포에서는 볼륨 경로로 재정의한다: sqlite:////data/delphi.db (docs/07 §2)
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'data' / 'delphi.db'}")
DEMO_OFFLINE = os.environ.get("DEMO_OFFLINE", "0") == "1"
# 빈 DB를 만나면 서버가 스스로 시드할지 — 배포본 기본 켬, 로컬은 명시적으로 끌 수 있다
SEED_ON_STARTUP = os.environ.get("SEED_ON_STARTUP", "1") == "1"
# 데모 리셋 엔드포인트 보호 토큰. 비어 있으면 리셋 자체가 비활성 (docs/07 §5)
RESET_TOKEN = os.environ.get("RESET_TOKEN", "")
MODEL_EXTRACT = os.environ.get("DELPHI_MODEL_EXTRACT", "claude-sonnet-5")
MODEL_BOARD = os.environ.get("DELPHI_MODEL_BOARD", "claude-opus-5")

# ── 에이전트별 키 분리 (08/22) ──────────────────────────────────────────────
# 에이전트마다 다른 키를 꽂을 수 있다. 이유는 셋:
#   ① 어느 에이전트가 얼마를 썼는지 콘솔에서 따로 보인다 (해커톤 크레딧 배분)
#   ② 하나가 rate limit에 걸려도 나머지가 산다
#   ③ 사내 이관 시 "설계 에이전트는 사내 LLM, 추출은 외부" 같은 분리가 코드 변경 없이 된다
# 값이 없으면 ANTHROPIC_API_KEY 로 자동 폴백한다 — 키 하나만 있어도 전부 동작한다.
AGENT_KEY_FALLBACK = "ANTHROPIC_API_KEY"
ALLOWED_ORIGINS = [
    o.strip() for o in os.environ.get(
        "ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001"
    ).split(",") if o.strip()
]
CORPUS_DIR = BACKEND_DIR / "data" / "corpus"          # 이미지에 포함 (읽기 전용)
FIXTURES_DIR = BACKEND_DIR / "data" / "fixtures"      # 이미지에 포함 (시드 입력·API 스냅샷)
# 캐시는 배포 시 볼륨으로 옮긴다 (외부 API 스냅샷을 재배포 사이에 보존 — docs/07 §2)
CACHE_DIR = Path(os.environ.get("DELPHI_CACHE_DIR", str(BACKEND_DIR / "data" / "cache")))
