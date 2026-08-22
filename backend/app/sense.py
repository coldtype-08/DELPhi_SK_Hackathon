"""Sense 추출 파이프라인 — 원석 문서 → 의료진별 구조화 claim (docs/01 §3, docs/02 §5).

[08/22 신설 · [cross] 엔진 층은 인혁 오너십 — 협의 필요]

**LLM이 하는 일과 코드가 하는 일이 이 파일에서 갈린다.**

| | 하는 일 |
|---|---|
| LLM | 어떤 문장이 신호인지 고르고, 스키마 항목으로 이름 붙이고, 인용문을 **복사**한다 |
| 코드 | 인용문이 원문에 **실제로 있는지** 대조하고, 문자 위치를 계산하고, 용어를 canonical로 매핑하고, |
| | 등급을 규칙으로 매기고, 안전성 후보를 떼어내고, 저장 여부를 결정한다 |

절대 규칙 대응:
- #1 수치는 LLM이 계산하지 않는다 → 오프셋·등급·카운트 전부 여기 파이썬 코드
- #2 evidence pointer 필수 → `_locate()` 실패 = **저장 거부**. 근거 없는 값은 DB에 들어가지 않는다
- #3 CANDIDATE로 시작 → `status="CANDIDATE"` 고정. 이 파이프라인은 승인 권한이 없다
- #6 AE 분리 → `safety_candidates`에만 적재하고 `claims`에는 한 건도 넣지 않는다
"""

import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .contract import (
    derive_label_scope,
    derive_purpose_domain,
    enum_values,
    load_active_contract,
    validate_claim_fields,
)
from .llm import call_llm, load_prompt, render
from .models import (
    BlockedLog,
    Claim,
    Document,
    Interaction,
    SafetyCandidate,
    UnmappedTerm,
    VocabTerm,
)

PROMPT_FILE = "sense_extract.md"
SCHEMA_NAME = "sense_extract_v1"

# ── 구조화 출력 스키마 — LLM은 이 모양으로만 답할 수 있다 ────────────────────
# enum을 스키마에 박지 않고 프롬프트로만 주는 이유: 계약 위반을 **서버가 잡아서 기록**해야
# "스키마 밖 개념이 반복된다"(SCP 신호)를 셀 수 있다. 스키마가 막아버리면 그 신호가 사라진다.
SENSE_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "verbatim_quote": {"type": "string", "description": "원문에서 글자 그대로 복사한 연속 문자열"},
                    "summary_ko": {"type": "string", "description": "한국어 한 문장. 관찰된 사실만"},
                    "signal_type": {"type": "string"},
                    "patient_segment": {"type": "string"},
                    "patient_segment_surface": {"type": ["string", "null"]},
                    "journey_stage": {"type": ["string", "null"]},
                    "barrier_type": {"type": ["string", "null"]},
                    "barrier_surface": {"type": ["string", "null"]},
                    "solicitation": {"type": ["string", "null"]},
                    "sentiment": {"type": ["string", "null"]},
                    "indication_mention": {"type": ["string", "null"]},
                    "concomitant_drugs": {"type": ["string", "null"]},
                    "administration_note": {"type": ["string", "null"]},
                },
                "required": ["verbatim_quote", "summary_ko", "signal_type", "patient_segment"],
            },
        },
        "safety": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "verbatim_quote": {"type": "string"},
                    "event_terms": {"type": ["string", "null"]},
                    "severity_note": {"type": ["string", "null"]},
                    "product_named": {"type": ["boolean", "null"]},
                },
                "required": ["verbatim_quote"],
            },
        },
    },
    "required": ["claims", "safety"],
}


# ── 프롬프트 조립 ───────────────────────────────────────────────────────────


def _enum_table(contract: dict) -> str:
    """계약의 허용값을 프롬프트에 넣을 표로. 계약이 바뀌면 프롬프트도 자동으로 바뀐다."""
    lines = []
    for key in ("signal_type", "patient_segment", "journey_stage", "barrier_type",
                "solicitation", "sentiment"):
        spec = contract["fields"].get(key)
        if not spec:
            continue
        vals = ", ".join(f"`{v['value']}`({v['label_ko']})" for v in spec.get("values", []))
        req = "필수" if spec.get("required") else (
            f"조건부 필수 — {spec['required_if']['field']}={spec['required_if']['equals']}일 때"
            if spec.get("required_if") else "선택")
        lines.append(f"- **{key}** ({spec['label_ko']}, {req}): {vals}")
    return "\n".join(lines)


def build_system_text(contract: dict, interaction: Interaction) -> str:
    prompt, _ = load_prompt(PROMPT_FILE)
    return render(prompt, {
        "CONTRACT_VERSION": str(contract["version"]),
        "ENUMS": _enum_table(contract),
        "HCP_REF": interaction.hcp_ref,
        "SPECIALTY": interaction.hcp_specialty or "전문과 미상",
    })


# ── 근거 검증: 이 함수가 절대 규칙 #2를 강제한다 ─────────────────────────────


def _locate(doc_text: str, interaction: Interaction, quote: str) -> tuple[int, int] | None:
    """인용문의 문서 전문 기준 문자 위치. 못 찾거나 블록 밖이면 None → 저장 거부.

    블록 범위가 있으면 **그 안에서만** 찾는다. 다른 의료진 블록의 문장을 이 의료진의
    발언으로 붙이는 것이 가장 위험한 오류이므로, 문서 전체 검색으로 물러서지 않는다.
    """
    if not quote or not quote.strip():
        return None
    lo = interaction.doc_char_start
    hi = interaction.doc_char_end
    if lo is not None and hi is not None:
        idx = doc_text.find(quote, lo, hi)
        if idx < 0:
            return None
        return idx, idx + len(quote)
    idx = doc_text.find(quote)
    if idx < 0:
        return None
    # 문서 안에 같은 문장이 두 번 있으면 어느 쪽인지 결정할 수 없다 → 거부
    if doc_text.find(quote, idx + 1) >= 0:
        return None
    return idx, idx + len(quote)


# ── 용어 매핑 (체크 ②) ──────────────────────────────────────────────────────


def _vocab_map(db: Session) -> list[tuple[str, str]]:
    rows = db.execute(select(VocabTerm.surface_form, VocabTerm.canonical_id)).all()
    return [(s.lower(), c) for s, c in rows]


def _map_surface(vocab: list[tuple[str, str]], surface: str | None, allowed: list[str]) -> str | None:
    """원문 표현 → canonical. vocab에 없으면 None (= 매핑 실패, unmapped_terms 후보)."""
    if not surface:
        return None
    low = surface.lower()
    for form, canon in vocab:
        if form in low and canon in allowed:
            return canon
    return None


def _note_unmapped(db: Session, surface: str, claim_id: str | None):
    row = db.execute(
        select(UnmappedTerm).where(func.lower(UnmappedTerm.surface_form) == surface.lower())
    ).scalar_one_or_none()
    if row:
        row.occurrence_count += 1
    else:
        db.add(UnmappedTerm(surface_form=surface, first_seen_claim_id=claim_id, occurrence_count=1))


# ── 등급 (체크 ①②③ → H/M/L, docs/02 §5) ───────────────────────────────────


def grade(check_b_ok: bool, check_c_ok: bool) -> str:
    """A(원문 일치)는 이미 통과한 상태로 들어온다 — 실패하면 저장 자체가 없다.

    HIGH = A∧B∧C · MEDIUM = A∧C (B 실패) · LOW = 그 외.
    검토 큐는 LOW → MEDIUM → HIGH 순으로 올린다(위험한 것부터). 즉 **큐 위쪽에 오는 것은
    언제나 ②(용어 매핑)나 ③(파생 규칙)에 걸린 행**이다 — ①은 애초에 저장되지 않으므로.
    """
    if check_b_ok and check_c_ok:
        return "HIGH"
    if check_c_ok:
        return "MEDIUM"
    return "LOW"


# ── 적재 ────────────────────────────────────────────────────────────────────


def _next_seq(db: Session, model, column, prefix: str) -> int:
    last = db.execute(select(func.max(column))).scalar_one_or_none()
    if not last:
        return 1
    try:
        return int(str(last).rsplit("-", 1)[1]) + 1
    except (IndexError, ValueError):
        return db.execute(select(func.count()).select_from(model)).scalar_one() + 1


def _block(db: Session, reason: str, detail_ko: str, payload: dict):
    db.add(BlockedLog(source="SENSE", reason_code=reason, detail_ko=detail_ko,
                      payload_json=json.dumps(payload, ensure_ascii=False),
                      created_at=datetime.now(timezone.utc).isoformat()))


def _ingest_claim(db, contract, vocab, doc: Document, it: Interaction, raw: dict,
                  seq: int, stats: dict) -> bool:
    quote = (raw.get("verbatim_quote") or "").strip()
    span = _locate(doc.raw_text, it, quote)
    if span is None:
        # 체크 ① 실패 — 절대 규칙 #2. 큐에도 올리지 않고 버린다. 다만 버린 사실은 남긴다.
        stats["rejected_no_evidence"] += 1
        _block(db, "VERBATIM_NOT_FOUND",
               "인용문이 해당 의료진 블록의 원문과 일치하지 않아 저장하지 않았습니다.",
               {"interaction_id": it.interaction_id, "quote": quote[:200]})
        return False

    signal_type = raw.get("signal_type") or "OTHER"
    if signal_type == "SAFETY_CANDIDATE":
        # 안전성은 claims 경로로 들어오지 않는다 (절대 규칙 #6) — safety[]로 냈어야 한다.
        stats["safety_rerouted"] += 1
        _ingest_safety(db, doc, it, {"verbatim_quote": quote}, stats)
        return False

    seg_allowed = enum_values(contract, "patient_segment")
    segment = raw.get("patient_segment") or "UNSPECIFIED"
    seg_surface = raw.get("patient_segment_surface")
    if segment not in seg_allowed:
        # 계약에 없는 값을 냈다 → 표현으로 취급하고 UNSPECIFIED로 낙착 (SCP 신호가 된다)
        seg_surface = seg_surface or segment
        segment = "UNSPECIFIED"
    if segment == "UNSPECIFIED" and seg_surface:
        mapped = _map_surface(vocab, seg_surface, seg_allowed)
        if mapped:
            segment = mapped

    barrier_allowed = enum_values(contract, "barrier_type")
    barrier = raw.get("barrier_type")
    if barrier and barrier not in barrier_allowed:
        barrier = _map_surface(vocab, raw.get("barrier_surface") or barrier, barrier_allowed)

    fields = {
        "signal_type": signal_type,
        "patient_segment": segment,
        "journey_stage": raw.get("journey_stage"),
        "barrier_type": barrier,
        "solicitation": raw.get("solicitation"),
        "sentiment": raw.get("sentiment"),
    }
    errors = validate_claim_fields(contract, fields)

    check_b = segment != "UNSPECIFIED"          # ② 용어 매핑
    check_c = not errors                        # ③ 파생 규칙
    claim_id = f"CLM-{seq:04d}"
    if not check_b and seg_surface:
        _note_unmapped(db, seg_surface, claim_id)
        stats["unmapped"] += 1

    db.add(Claim(
        claim_id=claim_id,
        interaction_id=it.interaction_id,
        product="XCOPRI",
        signal_type=signal_type,
        patient_segment=segment,
        label_scope=derive_label_scope(contract, segment, signal_type),
        journey_stage=fields["journey_stage"],
        barrier_type=barrier,
        purpose_domain=derive_purpose_domain(signal_type),
        solicitation=fields["solicitation"],
        sentiment=fields["sentiment"],
        indication_mention=raw.get("indication_mention"),
        concomitant_drugs=raw.get("concomitant_drugs"),
        administration_note=raw.get("administration_note"),
        verbatim_quote=quote,
        summary_ko=(raw.get("summary_ko") or "").strip(),
        evidence_json=json.dumps({"doc_id": doc.id, "char_start": span[0], "char_end": span[1]}),
        review_grade=grade(check_b, check_c),
        status="CANDIDATE",                     # 절대 규칙 #3 — 승인은 사람만
        contract_version=str(contract["version"]),
        created_at=datetime.now(timezone.utc).isoformat(),
    ))
    stats["claims"] += 1
    stats["by_grade"][grade(check_b, check_c)] += 1
    return True


def _ingest_safety(db, doc: Document, it: Interaction, raw: dict, stats: dict):
    quote = (raw.get("verbatim_quote") or "").strip()
    span = _locate(doc.raw_text, it, quote)
    if span is None:
        stats["rejected_no_evidence"] += 1
        _block(db, "VERBATIM_NOT_FOUND",
               "안전성 후보 인용문이 원문과 일치하지 않아 저장하지 않았습니다.",
               {"interaction_id": it.interaction_id, "quote": quote[:200]})
        return
    seq = _next_seq(db, SafetyCandidate, SafetyCandidate.id, "SAF")
    db.add(SafetyCandidate(
        id=f"SAF-{seq:04d}",
        interaction_id=it.interaction_id,
        verbatim_quote=quote,
        evidence_json=json.dumps({"doc_id": doc.id, "char_start": span[0], "char_end": span[1]}),
        event_terms=raw.get("event_terms"),
        severity_note=raw.get("severity_note"),   # 등급 "판정"은 하지 않는다 — PV 관할
        product_named=raw.get("product_named"),
        routed_at=datetime.now(timezone.utc).isoformat(),
        status="OPEN",
    ))
    db.flush()
    stats["safety"] += 1


# ── 진입점 ──────────────────────────────────────────────────────────────────


def _empty_stats() -> dict:
    return {"blocks": 0, "claims": 0, "safety": 0, "safety_rerouted": 0,
            "rejected_no_evidence": 0, "unmapped": 0,
            "by_grade": {"HIGH": 0, "MEDIUM": 0, "LOW": 0}}


def extract_document(db: Session, doc_id: str, *, force: bool = False) -> dict:
    """문서 1건을 의료진 블록별로 추출해 claims/safety_candidates에 적재한다.

    이미 추출된 문서는 기본적으로 건너뛴다 (`force=True`면 기존 claim을 지우고 다시).
    """
    doc = db.get(Document, doc_id)
    if not doc:
        raise ValueError(f"문서가 없습니다: {doc_id}")
    inters = db.execute(
        select(Interaction).where(Interaction.document_id == doc_id)
        .order_by(Interaction.block_index, Interaction.interaction_id)
    ).scalars().all()

    existing = db.execute(
        select(func.count()).select_from(Claim)
        .join(Interaction, Interaction.interaction_id == Claim.interaction_id)
        .where(Interaction.document_id == doc_id)
    ).scalar_one()
    if existing and not force:
        return {"documentId": doc_id, "skipped": True, "reason": "ALREADY_EXTRACTED",
                "existingClaims": existing}
    if existing and force:
        ids = [i.interaction_id for i in inters]
        for c in db.execute(select(Claim).where(Claim.interaction_id.in_(ids))).scalars().all():
            db.delete(c)
        db.flush()

    contract = load_active_contract(db)
    vocab = _vocab_map(db)
    stats = _empty_stats()
    seq = _next_seq(db, Claim, Claim.claim_id, "CLM")

    for it in inters:
        stats["blocks"] += 1
        out = call_llm(
            db,
            purpose="sense_extract",
            prompt_file=PROMPT_FILE,
            schema_name=SCHEMA_NAME,
            schema=SENSE_SCHEMA,
            system_text=build_system_text(contract, it),
            input_text=it.raw_text,
            force=force,
        )
        for raw in out.get("claims") or []:
            if _ingest_claim(db, contract, vocab, doc, it, raw, seq, stats):
                seq += 1
        for raw in out.get("safety") or []:
            _ingest_safety(db, doc, it, raw, stats)

    db.commit()
    return {"documentId": doc_id, "skipped": False, **stats}
