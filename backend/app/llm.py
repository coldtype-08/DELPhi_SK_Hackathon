"""Claude 호출 단일 래퍼 — 모든 LLM 호출은 반드시 이 파일을 경유한다 (docs/01 §7·§8).

[08/22 구현 — 스캐폴딩 해제. 오너: 인혁(엔진) / 프롬프트: 건태]

세 가지를 이 파일이 책임진다:
1. **구조화 출력 강제** — tool_choice로 JSON schema를 강제한다. 자유 텍스트를 파싱하지 않는다.
2. **재현 캐시** — 응답을 `backend/data/llm_cache/`에 저장하고, 같은 입력이면 API를 호출하지 않는다.
   캐시는 커밋 대상이다. 심사위원 환경·발표 현장에서 네트워크와 무관하게 같은 결과가 나와야 한다 (docs/07 §4.5).
3. **생성 조건 기록** — 캐시 적중이든 실제 호출이든 `llm_runs`에 남긴다. 남지 않은 값은 감사할 수 없다.

벤더 교체·사내 LLM 전환 시에도 이 파일만 바꾼다 (기획서 §4-3 계층 분리).
"""

import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from .config import BACKEND_DIR, DEMO_OFFLINE, MODEL_EXTRACT
from .models import LlmRun

PARSER_VERSION = "sense@1"  # 파서 로직을 고치면 반드시 올린다 (docs/01 §7)

PROMPT_DIR = Path(__file__).resolve().parent / "prompts"
CACHE_DIR = Path(os.environ.get("DELPHI_LLM_CACHE_DIR", str(BACKEND_DIR / "data" / "llm_cache")))
MAX_TOKENS = 4096


class LlmUnavailable(RuntimeError):
    """캐시에도 없고 API 키도 없다 — 조용히 빈 결과를 주지 않고 실패시킨다."""


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# ── 프롬프트 로드 ──────────────────────────────────────────────────────────


def load_prompt(prompt_file: str) -> tuple[str, str]:
    """`prompts/*.md` → (본문, 버전). 상단 `<!-- version: x@n | ... -->` 주석이 필수다."""
    path = PROMPT_DIR / prompt_file
    if not path.exists():
        raise FileNotFoundError(f"프롬프트가 없습니다: {path}")
    text = path.read_text(encoding="utf-8")
    first = text.lstrip().splitlines()[0] if text.strip() else ""
    if not (first.startswith("<!--") and "version:" in first):
        raise ValueError(f"{prompt_file}: 상단 version 주석이 없습니다 (prompts/README.md 규약)")
    version = first.split("version:", 1)[1].split("|", 1)[0].strip()
    return text, version


def render(prompt: str, values: dict[str, str]) -> str:
    """`{{KEY}}` 치환. 남은 자리표시자가 있으면 실패 — 조용히 빈칸으로 나가지 않게."""
    for k, v in values.items():
        prompt = prompt.replace("{{" + k + "}}", v)
    if "{{" in prompt:
        leftover = prompt[prompt.index("{{"):][:40]
        raise ValueError(f"치환되지 않은 자리표시자: {leftover}")
    return prompt


# ── 캐시 ───────────────────────────────────────────────────────────────────


def _cache_key(purpose: str, model: str, prompt_version: str, schema_name: str, input_text: str) -> str:
    raw = "\x1f".join([purpose, model, prompt_version, schema_name, input_text])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def _cache_path(key: str) -> Path:
    return CACHE_DIR / f"{key}.json"


def cache_stats() -> dict:
    n = len(list(CACHE_DIR.glob("*.json"))) if CACHE_DIR.exists() else 0
    return {"dir": str(CACHE_DIR), "entries": n}


# ── 호출 ───────────────────────────────────────────────────────────────────


def call_llm(
    db: Session,
    *,
    purpose: str,
    prompt_file: str,
    schema_name: str,
    schema: dict,
    system_text: str,
    input_text: str,
    model: str | None = None,
    external_data_as_of: str | None = None,
    force: bool = False,
) -> dict:
    """구조화 출력(JSON schema)을 강제한 Claude 호출 + 캐시 + llm_runs 기록.

    system_text 는 `load_prompt`+`render`로 만들어 넘긴다 — 프롬프트 하드코딩 금지 (CLAUDE.md 컨벤션).
    prompt_version 은 프롬프트 파일에서 읽으므로 호출부가 따로 넘기지 않는다.
    """
    started = time.time()
    model = model or MODEL_EXTRACT
    _, prompt_version = load_prompt(prompt_file)
    key = _cache_key(purpose, model, prompt_version, schema_name, input_text)
    path = _cache_path(key)

    cached = None
    if path.exists() and not force:
        cached = json.loads(path.read_text(encoding="utf-8"))

    if cached is not None:
        output = cached["output"]
        latency = 0
    else:
        if DEMO_OFFLINE:
            raise LlmUnavailable(
                f"DEMO_OFFLINE=1 인데 캐시에 없습니다 ({purpose}, key={key[:8]}). "
                "먼저 `python scripts/extract_corpus.py` 로 캐시를 채우세요."
            )
        output = _call_anthropic(model, system_text, input_text, schema_name, schema)
        latency = int((time.time() - started) * 1000)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({
            "purpose": purpose, "model": model, "prompt_file": prompt_file,
            "prompt_version": prompt_version, "schema_name": schema_name,
            "input_hash": _hash(input_text), "latency_ms": latency, "output": output,
        }, ensure_ascii=False, indent=1), encoding="utf-8")

    log_llm_run(db, purpose=purpose, model=model, prompt_file=prompt_file,
                prompt_version=prompt_version, schema_name=schema_name,
                external_data_as_of=external_data_as_of,
                input_text=input_text, output_text=json.dumps(output, ensure_ascii=False),
                latency_ms=latency)
    return output


def _call_anthropic(model: str, system_text: str, input_text: str, schema_name: str, schema: dict) -> dict:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise LlmUnavailable(
            "ANTHROPIC_API_KEY 가 없습니다. 레포 루트 `.env`에 넣으세요 (커밋 금지 — .gitignore 확인). "
            "캐시가 이미 있으면 키 없이도 동작합니다."
        )
    import anthropic  # 지연 임포트 — 캐시만 쓰는 환경에서는 SDK가 없어도 된다

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=model,
        max_tokens=MAX_TOKENS,
        temperature=0,
        system=system_text,
        messages=[{"role": "user", "content": input_text}],
        tools=[{
            "name": schema_name,
            "description": "구조화 결과를 이 스키마로만 반환한다.",
            "input_schema": schema,
        }],
        tool_choice={"type": "tool", "name": schema_name},
    )
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and block.name == schema_name:
            return block.input
    raise RuntimeError(f"구조화 출력이 오지 않았습니다 (stop_reason={resp.stop_reason})")


def log_llm_run(
    db: Session,
    *,
    purpose: str,
    model: str,
    prompt_file: str,
    prompt_version: str,
    schema_name: str,
    input_text: str,
    output_text: str,
    latency_ms: int,
    external_data_as_of: str | None = None,
) -> int:
    """생성 조건 5종(모델·prompt·schema·parser·외부데이터 시점) 기록 — 절대 누락 금지 (docs/01 §7)."""
    run = LlmRun(
        purpose=purpose,
        model=model,
        prompt_file=prompt_file,
        prompt_version=prompt_version,
        schema_name=schema_name,
        parser_version=PARSER_VERSION,
        external_data_as_of=external_data_as_of,
        input_hash=_hash(input_text),
        output_hash=_hash(output_text),
        latency_ms=latency_ms,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    db.add(run)
    db.flush()
    return run.id
