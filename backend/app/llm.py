"""Claude 호출 단일 래퍼 — 모든 LLM 호출은 반드시 이 파일을 경유한다 (docs/01 §7·§8).

[스캐폴딩 상태 · 오너: 인혁]
- 시그니처와 llm_runs 로깅은 완성되어 있다.
- 실제 Anthropic 호출부(call_llm 내부 TODO)만 채우면 추출·Screen·Board가 이 함수를 그대로 쓴다.
- 벤더 교체·사내 LLM 전환 시에도 이 파일만 바꾼다 (기획서 §4-3 계층 분리).
"""

import hashlib
import json
import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from .config import MODEL_EXTRACT
from .models import LlmRun

PARSER_VERSION = "scaffold@0"  # 파서 로직을 고치면 반드시 올린다 (docs/01 §7)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def call_llm(
    db: Session,
    *,
    purpose: str,
    prompt_file: str,
    prompt_version: str,
    schema_name: str,
    input_text: str,
    model: str | None = None,
    external_data_as_of: str | None = None,
) -> dict:
    """구조화 출력(JSON schema)을 강제한 Claude 호출 + llm_runs 기록.

    TODO(인혁, 8/21): anthropic SDK 호출 구현 — temperature 0, structured output,
    프롬프트는 backend/app/prompts/*.md 에서 로드 (하드코딩 금지, 오너: 소정).
    """
    started = time.time()
    model = model or MODEL_EXTRACT

    # ── 실제 호출부 (stub) ──────────────────────────────────────────────
    raise NotImplementedError(
        "LLM 호출은 아직 stub입니다 — docs/00 8/21 칸: 'stub을 실제 LLM 추출로 교체' [오너: 인혁]. "
        "구현 후 아래 log_llm_run 호출은 그대로 사용하세요."
    )
    # output = {...}
    # log_llm_run(db, purpose=purpose, model=model, prompt_file=prompt_file,
    #             prompt_version=prompt_version, schema_name=schema_name,
    #             external_data_as_of=external_data_as_of,
    #             input_text=input_text, output_text=json.dumps(output),
    #             latency_ms=int((time.time() - started) * 1000))
    # return output


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
