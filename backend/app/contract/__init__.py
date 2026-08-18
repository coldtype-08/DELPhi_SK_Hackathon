"""Data Contract 로드·검증·파생 규칙 — 스키마의 단일 소비 지점.

[오너: 인혁] SCP 승인 → 새 버전 ACTIVE화 로직은 여기에 추가한다 (docs/02 §7).
"""

import json
from pathlib import Path

import yaml
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import ContractVersion

CONTRACT_DIR = Path(__file__).resolve().parent
SEED_YAML = CONTRACT_DIR / "contract_v0_1.yaml"


def load_active_contract(db: Session) -> dict:
    """ACTIVE 버전의 contract를 dict로. 시드 전이면 파일의 v0.1을 폴백으로 쓴다."""
    row = db.execute(
        select(ContractVersion).where(ContractVersion.status == "ACTIVE")
    ).scalar_one_or_none()
    if row:
        return yaml.safe_load(row.body_yaml)
    return yaml.safe_load(SEED_YAML.read_text(encoding="utf-8"))


def enum_values(contract: dict, field: str) -> list[str]:
    return [v["value"] for v in contract["fields"].get(field, {}).get("values", [])]


def derive_label_scope(contract: dict, patient_segment: str, signal_type: str | None = None) -> str:
    # 리퍼포징 신호(미허가 적응증)는 환자군과 무관하게 허가 범위 밖 (08/19 부트스트랩)
    if signal_type == "REPURPOSING_SIGNAL":
        return "OUT_OF_LABEL"
    for v in contract["fields"]["patient_segment"]["values"]:
        if v["value"] == patient_segment:
            return v.get("label_scope", "IN_LABEL")
    return "IN_LABEL"


def derive_purpose_domain(signal_type: str) -> str:
    if signal_type == "ACCESS_ISSUE":
        return "COMMERCIAL"
    if signal_type == "SAFETY_CANDIDATE":
        return "SAFETY"
    return "MEDICAL"


def validate_claim_fields(contract: dict, fields: dict) -> list[str]:
    """enum 위반 목록을 돌려준다 (빈 리스트 = 통과). 검토등급 체크 C의 일부 (docs/02 §5)."""
    errors = []
    for key in ("signal_type", "patient_segment", "journey_stage", "barrier_type", "solicitation", "sentiment"):
        val = fields.get(key)
        if val is None:
            continue
        allowed = enum_values(contract, key)
        if allowed and val not in allowed:
            errors.append(f"{key}={val} 는 contract v{contract['version']}에 없는 값")
    if fields.get("signal_type") == "TREATMENT_BARRIER" and not fields.get("barrier_type"):
        errors.append("TREATMENT_BARRIER면 barrier_type 필수")
    return errors


def form_config(contract: dict, checklist_items: list[dict]) -> dict:
    """활성 contract → Field 입력 폼 정의 (docs/04 §6). v0.2 승인 직후 이 응답이 바뀌는 게 데모 클라이맥스."""
    out = []
    for key, spec in contract["fields"].items():
        if not spec.get("field_form"):
            continue
        options = []
        for v in spec.get("values", []):
            opt = {"value": v["value"], "labelKo": v["label_ko"]}
            if v.get("label_scope"):
                opt["labelScope"] = v["label_scope"]
            if v.get("is_new"):
                opt["isNew"] = True
            options.append(opt)
        out.append({
            "key": _camel(key),
            "labelKo": spec["label_ko"],
            "type": "select",
            "required": bool(spec.get("required")),
            "options": options,
        })
    out.append({"key": "checklist", "type": "checklist", "items": checklist_items})
    return {"contractVersion": contract["version"], "fields": out}


def _camel(snake: str) -> str:
    head, *rest = snake.split("_")
    return head + "".join(w.capitalize() for w in rest)
