"""목적·권한 조회 게이트 — docs/02 §9의 코드화. 모든 claim/집계 조회가 여기를 경유한다.

원칙 (docs/01 §2): 권한은 프론트 필터가 아니라 이 게이트가 SQL 조건으로 강제한다.
위반 쿼리는 조용히 빈 결과를 주지 않고 403 예외를 던진다 — 조용한 누락이 더 위험하다.
"""

from fastapi import Header, HTTPException

ROLES = {"MEDICAL_AFFAIRS", "CLINICAL_STRATEGY", "SAFETY", "COMMERCIAL", "DATA_STEWARD"}

# 롤 → 조회 가능한 purpose_domain (docs/02 §9 매트릭스가 유일한 정의)
ROLE_DOMAINS: dict[str, set[str]] = {
    "MEDICAL_AFFAIRS": {"MEDICAL", "PUBLIC_EVIDENCE"},
    "CLINICAL_STRATEGY": {"MEDICAL", "PUBLIC_EVIDENCE"},
    "SAFETY": {"SAFETY"},
    "COMMERCIAL": {"COMMERCIAL"},
    "DATA_STEWARD": set(),  # 값이 아니라 구조(스키마·SCP·버전)를 다룬다
}

# 원문(raw_text·verbatim) 접근이 가능한 롤 — COMMERCIAL은 필드 자체가 응답에서 사라진다
RAW_TEXT_ROLES = {"MEDICAL_AFFAIRS", "CLINICAL_STRATEGY"}
COMMERCIAL_MIN_DISTINCT_HCP = 3  # 개인 역추정 차단 (docs/02 §9)


def scope_violation(message_ko: str) -> HTTPException:
    return HTTPException(
        status_code=403,
        detail={"code": "PURPOSE_SCOPE_VIOLATION", "message_ko": message_ko},
    )


def get_role(x_delphi_role: str | None = Header(default=None)) -> str:
    """모든 요청의 롤. 미지정 시 CLINICAL_STRATEGY (MVP 편의 — docs/04 §0)."""
    role = x_delphi_role or "CLINICAL_STRATEGY"
    if role not in ROLES:
        raise HTTPException(
            status_code=400,
            detail={"code": "UNKNOWN_ROLE", "message_ko": f"알 수 없는 롤: {role}"},
        )
    return role


def allowed_domains(role: str) -> set[str]:
    return ROLE_DOMAINS[role]


def require_raw_text_access(role: str):
    if role not in RAW_TEXT_ROLES:
        raise scope_violation(f"{role} 롤은 원문(raw_text)에 접근할 수 없습니다.")


def require_domain(role: str, domain: str):
    if domain not in ROLE_DOMAINS[role]:
        raise scope_violation(f"{role} 롤은 {domain} 영역을 조회할 수 없습니다.")
