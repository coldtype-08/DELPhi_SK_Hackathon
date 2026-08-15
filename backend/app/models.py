"""DB 테이블 전부 — docs/02 §4를 그대로 옮긴 것. 필드를 바꾸면 docs/02를 같은 커밋에서 수정한다.

규약: 날짜·시각은 ISO 8601 문자열(Text), JSON은 *_json Text 컬럼(앱에서 json.dumps/loads).
SQLite 전용 타입·함수 금지 (향후 Snowflake 이관 대비 — docs/01 §2).
"""

from sqlalchemy import Boolean, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(Text, primary_key=True)          # DOC-{YYYYMMDD}-{seq}
    filename: Mapped[str] = mapped_column(Text)
    source_format: Mapped[str] = mapped_column(Text)                 # TXT | DOCX | PDF
    language: Mapped[str] = mapped_column(Text)                      # EN | KO
    raw_text: Mapped[str] = mapped_column(Text)                      # 마스킹 후 전문(불변) — evidence 오프셋 기준
    sha256: Mapped[str] = mapped_column(Text)
    imported_at: Mapped[str] = mapped_column(Text)


class Interaction(Base):
    __tablename__ = "interactions"
    interaction_id: Mapped[str] = mapped_column(Text, primary_key=True)  # INT-{YYYYMMDD}-{seq}
    document_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_on: Mapped[str] = mapped_column(Text)
    hcp_ref: Mapped[str] = mapped_column(Text)                       # 가명 HCP-###
    hcp_specialty: Mapped[str] = mapped_column(Text)
    region: Mapped[str] = mapped_column(Text)
    setting: Mapped[str] = mapped_column(Text)
    source_type: Mapped[str] = mapped_column(Text)
    market: Mapped[str] = mapped_column(Text, default="US")
    consent_confirmed: Mapped[bool] = mapped_column(Boolean, default=True)
    raw_text: Mapped[str] = mapped_column(Text)                      # 블록 텍스트 (1문서=1면담이면 본문 전체)
    masked_spans_json: Mapped[str] = mapped_column(Text, default="[]")
    language: Mapped[str] = mapped_column(Text, default="EN")
    block_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    doc_char_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    doc_char_end: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Claim(Base):
    __tablename__ = "claims"
    claim_id: Mapped[str] = mapped_column(Text, primary_key=True)    # CLM-{seq}
    interaction_id: Mapped[str] = mapped_column(Text)
    product: Mapped[str] = mapped_column(Text, default="XCOPRI")
    signal_type: Mapped[str] = mapped_column(Text)
    patient_segment: Mapped[str] = mapped_column(Text)
    label_scope: Mapped[str] = mapped_column(Text)                   # IN_LABEL | OUT_OF_LABEL (자동판정)
    journey_stage: Mapped[str | None] = mapped_column(Text, nullable=True)
    barrier_type: Mapped[str | None] = mapped_column(Text, nullable=True)
    purpose_domain: Mapped[str] = mapped_column(Text)                # 조회 게이트의 단위 (docs/02 §9)
    verbatim_quote: Mapped[str] = mapped_column(Text)
    summary_ko: Mapped[str] = mapped_column(Text)
    evidence_json: Mapped[str] = mapped_column(Text)                 # {doc_id, char_start, char_end} — 문서 전문 기준
    review_grade: Mapped[str] = mapped_column(Text)                  # HIGH | MEDIUM | LOW (결정론 계산)
    status: Mapped[str] = mapped_column(Text, default="CANDIDATE")   # CANDIDATE | APPROVED | REJECTED
    contract_version: Mapped[str] = mapped_column(Text, default="0.1")
    reviewed_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(Text)


class VocabTerm(Base):
    __tablename__ = "vocab_terms"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    surface_form: Mapped[str] = mapped_column(Text)
    lang: Mapped[str] = mapped_column(Text, default="EN")            # EN | KO — 다국어 정규화 (docs/02 §3)
    canonical_id: Mapped[str] = mapped_column(Text)
    canonical_label_ko: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(Text, default="CUSTOM")      # MESH_REF | CUSTOM


class UnmappedTerm(Base):
    __tablename__ = "unmapped_terms"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    surface_form: Mapped[str] = mapped_column(Text)
    first_seen_claim_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)


class SafetyCandidate(Base):
    __tablename__ = "safety_candidates"
    id: Mapped[str] = mapped_column(Text, primary_key=True)          # SAF-{seq}
    interaction_id: Mapped[str] = mapped_column(Text)
    verbatim_quote: Mapped[str] = mapped_column(Text)
    evidence_json: Mapped[str] = mapped_column(Text)
    routed_at: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="OPEN")        # OPEN | ACKNOWLEDGED


class ContractVersion(Base):
    __tablename__ = "contract_versions"
    version: Mapped[str] = mapped_column(Text, primary_key=True)     # "0.1"
    body_yaml: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, default="DRAFT")       # DRAFT | ACTIVE | RETIRED
    approved_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    approved_at: Mapped[str | None] = mapped_column(Text, nullable=True)


class SchemaChangeProposal(Base):
    __tablename__ = "schema_change_proposals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    kind: Mapped[str] = mapped_column(Text)                          # NEW_ENUM_VALUE | NEW_FIELD
    target_field: Mapped[str] = mapped_column(Text)
    proposed_value: Mapped[str] = mapped_column(Text)
    rationale_ko: Mapped[str] = mapped_column(Text)
    example_claim_ids_json: Mapped[str] = mapped_column(Text, default="[]")
    occurrence_count: Mapped[int] = mapped_column(Integer, default=0)
    distinct_hcp_count: Mapped[int] = mapped_column(Integer, default=0)
    impact_note_ko: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(Text, default="PROPOSED")    # PROPOSED | APPROVED | REJECTED
    decided_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    decided_at: Mapped[str | None] = mapped_column(Text, nullable=True)


class Hypothesis(Base):
    __tablename__ = "hypotheses"
    id: Mapped[str] = mapped_column(Text, primary_key=True)          # HYP-001
    title_ko: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)                          # IN_LABEL | DEVELOPMENT
    status: Mapped[str] = mapped_column(Text, default="DRAFT")       # docs/01 §3 상태 머신
    segment: Mapped[str] = mapped_column(Text)
    driver_summary_ko: Mapped[str] = mapped_column(Text, default="")
    created_from_aggregate_json: Mapped[str] = mapped_column(Text, default="{}")
    not_board_ready_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class ScreenFinding(Base):
    __tablename__ = "screen_findings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hypothesis_id: Mapped[str] = mapped_column(Text)
    agent: Mapped[str] = mapped_column(Text)                         # FIELD_SIGNAL | EVIDENCE | SAFETY | CRITIC
    finding_type: Mapped[str] = mapped_column(Text)                  # SUPPORT | COUNTER | GAP | SAFETY_SIGNAL | BLOCK
    statement_ko: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_locator: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_as_of: Mapped[str | None] = mapped_column(Text, nullable=True)   # 캐시 스냅샷 일시 (docs/01 §7)
    caveat_ko: Mapped[str | None] = mapped_column(Text, nullable=True)      # 외부 출처면 필수 (docs/02 §10)
    created_at: Mapped[str] = mapped_column(Text)


class BoardMinute(Base):
    __tablename__ = "board_minutes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hypothesis_id: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)                          # MEDICAL | DEVELOPMENT | SAFETY | MARKET_ACCESS | CEO
    position_ko: Mapped[str] = mapped_column(Text)
    action_item_json: Mapped[str] = mapped_column(Text, default="[]")
    seq: Mapped[int] = mapped_column(Integer)


class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    hypothesis_id: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(Text)                      # APPROVED | HOLD | REJECTED
    decided_by: Mapped[str] = mapped_column(Text)
    rationale_ko: Mapped[str] = mapped_column(Text, default="")
    follow_up_json: Mapped[str] = mapped_column(Text, default="[]")
    decided_at: Mapped[str] = mapped_column(Text)


class BlockedLog(Base):
    __tablename__ = "blocked_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(Text, default="CRITIC")
    reason_code: Mapped[str] = mapped_column(Text)
    detail_ko: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[str] = mapped_column(Text)


class LlmRun(Base):
    __tablename__ = "llm_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    purpose: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    prompt_file: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(Text)
    schema_name: Mapped[str] = mapped_column(Text)
    parser_version: Mapped[str] = mapped_column(Text)
    external_data_as_of: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_hash: Mapped[str] = mapped_column(Text)
    output_hash: Mapped[str] = mapped_column(Text)
    latency_ms: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[str] = mapped_column(Text)
