"""코퍼스 → DB 시드 (docs/03 §5.5). 리셋 후 재실행해도 항상 같은 상태 (결정론).

이 로직이 backend 패키지 안에 있는 이유: 클라우드 배포에서 **빈 볼륨을 만나면 서버가 스스로 시드**해야
하기 때문이다 (`ensure_seeded`). CLI 진입점은 `scripts/seed_db.py`가 그대로 유지한다.

하는 일:
  1) 테이블 전체 재생성 (drop_all → create_all — 시연 리셋의 기반)
  2) corpus/manifest.jsonl + *.txt → documents(전문) · interactions
     - PII는 masked_spans 위치를 '■'로 치환해 저장 (마스킹 전 원본은 저장하지 않는다 — docs/02 §1)
     - '■'는 글자 수를 보존하므로 evidence 오프셋이 흔들리지 않는다
  3) Data Contract v0.1 적재 (ACTIVE)
  4) 개발·데모용 CANDIDATE claim 시드 (data/fixtures/seed_claims.json)
     - verbatim을 문서 전문에서 찾아 evidence 오프셋 계산 + 유일성 검증 (절대 규칙 #2)
  5) 대표 가설 2건(HYP-001 Development / HYP-002 In-label) DRAFT 적재
  6) 용어 정규화 시드 (docs/02 §3 — EN·KO가 같은 canonical로 수렴)
"""

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import func, select

from .config import CORPUS_DIR, FIXTURES_DIR
from .contract import SEED_YAML, derive_label_scope, derive_purpose_domain, load_active_contract
from .db import Base, SessionLocal, engine
from .models import Claim, ContractVersion, Document, Hypothesis, Interaction, VocabTerm

VOCAB_SEED = [
    # (surface, lang, canonical, label_ko) — 영어·한국어가 같은 canonical로 수렴 (docs/02 §3)
    ("adolescent", "EN", "PEDIATRIC_TRANSITION", "청소년(12–17세) 전환기"),
    ("17-year-old", "EN", "PEDIATRIC_TRANSITION", "청소년(12–17세) 전환기"),
    ("until 18", "EN", "PEDIATRIC_TRANSITION", "청소년(12–17세) 전환기"),
    ("17세 환자", "KO", "PEDIATRIC_TRANSITION", "청소년(12–17세) 전환기"),
    ("청소년", "KO", "PEDIATRIC_TRANSITION", "청소년(12–17세) 전환기"),
    ("elderly", "EN", "ELDERLY_65_PLUS", "노인(65세 이상)"),
    ("older adults", "EN", "ELDERLY_65_PLUS", "노인(65세 이상)"),
    ("geriatric", "EN", "ELDERLY_65_PLUS", "노인(65세 이상)"),
    ("어르신", "KO", "ELDERLY_65_PLUS", "노인(65세 이상)"),
    ("고령", "KO", "ELDERLY_65_PLUS", "노인(65세 이상)"),
    ("drug-resistant", "EN", "DRE_2PLUS", "약물난치성(2제 이상 실패)"),
    ("refractory", "EN", "DRE_2PLUS", "약물난치성(2제 이상 실패)"),
    ("2제 실패", "KO", "DRE_2PLUS", "약물난치성(2제 이상 실패)"),
    ("난치성", "KO", "DRE_2PLUS", "약물난치성(2제 이상 실패)"),
    ("DDI", "EN", "DDI_CONCERN", "약물 상호작용 우려"),
    ("drug-drug interactions", "EN", "DDI_CONCERN", "약물 상호작용 우려"),
    ("상호작용", "KO", "DDI_CONCERN", "약물 상호작용 우려"),
    ("titration burden", "EN", "TITRATION_COMPLEXITY", "적정 복잡성"),
    ("타이트레이션 부담", "KO", "TITRATION_COMPLEXITY", "적정 복잡성"),
]


def mask(text: str, spans: list[dict]) -> str:
    """masked_spans 구간을 '■'로 치환 — 길이 보존으로 오프셋 불변."""
    out = list(text)
    for s in spans:
        for i in range(s["char_start"], s["char_end"]):
            out[i] = "■"
    return "".join(out)


def seed() -> dict:
    """전체 시드를 실행하고 적재 건수를 돌려준다. 기존 데이터는 삭제된다."""
    manifest_path = CORPUS_DIR / "manifest.jsonl"
    if not manifest_path.exists():
        raise FileNotFoundError(f"코퍼스가 없습니다: {manifest_path} — 먼저 `bash scripts/generate.sh`")
    rows = [json.loads(l) for l in manifest_path.read_text(encoding="utf-8").splitlines() if l.strip()]
    now = datetime.now(timezone.utc).isoformat()

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        # ── documents + interactions ──────────────────────────────────────
        doc_masked: dict[str, str] = {}
        by_doc: dict[str, list[dict]] = {}
        for r in rows:
            by_doc.setdefault(r["doc_id"], []).append(r)

        for doc_id, units in sorted(by_doc.items()):
            raw = (CORPUS_DIR / units[0]["file"]).read_text(encoding="utf-8")
            all_spans = [s for u in units for s in (u["masked_spans"] or [])]
            masked_doc = mask(raw, all_spans)
            doc_masked[doc_id] = masked_doc
            db.add(Document(
                id=doc_id, filename=units[0]["file"],
                source_format=units[0]["source_format"], language=units[0]["language"],
                raw_text=masked_doc,
                sha256=hashlib.sha256(masked_doc.encode()).hexdigest(),
                imported_at=now,
            ))
            for u in sorted(units, key=lambda x: x["block_index"] or 1):
                if u["doc_char_start"] is not None:
                    block_txt = masked_doc[u["doc_char_start"]:u["doc_char_end"]]
                else:
                    idx = raw.find(u["raw_text"])
                    block_txt = masked_doc[idx: idx + len(u["raw_text"])] if idx >= 0 else u["raw_text"]
                db.add(Interaction(
                    interaction_id=u["interaction_id"], document_id=doc_id,
                    occurred_on=u["occurred_on"], hcp_ref=u["hcp_ref"],
                    hcp_specialty=u["hcp_specialty"], region=u["region"], setting=u["setting"],
                    source_type=u["source_type"], market=u["market"],
                    consent_confirmed=bool(u["consent_confirmed"]),
                    raw_text=block_txt,
                    masked_spans_json=json.dumps(u["masked_spans"] or [], ensure_ascii=False),
                    language=u["language"], block_index=u["block_index"],
                    doc_char_start=u["doc_char_start"], doc_char_end=u["doc_char_end"],
                ))
        db.flush()

        # ── Data Contract v0.1 ────────────────────────────────────────────
        db.add(ContractVersion(
            version="0.1", body_yaml=SEED_YAML.read_text(encoding="utf-8"),
            status="ACTIVE", approved_by="Data Steward (시드)", approved_at=now,
        ))
        db.flush()
        contract = load_active_contract(db)

        # ── 개발·데모용 CANDIDATE claims (verbatim → 오프셋 계산) ────────
        seeds = json.loads((FIXTURES_DIR / "seed_claims.json").read_text(encoding="utf-8"))["claims"]
        n_claims = 0
        for i, s in enumerate(seeds, 1):
            hits = [(doc_id, txt.find(s["verbatim"]))
                    for doc_id, txt in doc_masked.items() if s["verbatim"] in txt]
            assert len(hits) == 1, f"verbatim이 유일하지 않음({len(hits)}건): {s['verbatim'][:40]}…"
            doc_id, start = hits[0]
            inter = None
            for u in by_doc[doc_id]:
                lo, hi = u["doc_char_start"], u["doc_char_end"]
                if lo is None or (lo <= start < hi):
                    inter = u
                    if lo is not None:
                        break
            assert inter, f"interaction 매칭 실패: {doc_id}"
            db.add(Claim(
                claim_id=f"CLM-{i:04d}", interaction_id=inter["interaction_id"],
                product="XCOPRI", signal_type=s["signal_type"],
                patient_segment=s["patient_segment"],
                label_scope=derive_label_scope(contract, s["patient_segment"], s["signal_type"]),
                journey_stage=s.get("journey_stage"), barrier_type=s.get("barrier_type"),
                solicitation=s.get("solicitation"), sentiment=s.get("sentiment"),
                indication_mention=s.get("indication_mention"),
                concomitant_drugs=s.get("concomitant_drugs"),
                administration_note=s.get("administration_note"),
                purpose_domain=derive_purpose_domain(s["signal_type"]),
                verbatim_quote=s["verbatim"], summary_ko=s["summary_ko"],
                evidence_json=json.dumps(
                    {"doc_id": doc_id, "char_start": start, "char_end": start + len(s["verbatim"])}),
                review_grade="HIGH", status="CANDIDATE", contract_version="0.1", created_at=now,
            ))
            n_claims += 1

        # ── 대표 가설 2건 (DRAFT) ─────────────────────────────────────────
        db.add(Hypothesis(
            id="HYP-001", kind="DEVELOPMENT", status="DRAFT", segment="PEDIATRIC_TRANSITION",
            title_ko="청소년(12–17세) 약물난치성 초점발작 — 연령 확대 근거 생성 우선 검토",
            driver_summary_ko="허가 범위(성인 18+) 밖 반복 신호 — 전문조직 검토 대상으로만 전달 (상업 액션 차단)",
        ))
        db.add(Hypothesis(
            id="HYP-002", kind="IN_LABEL", status="DRAFT", segment="ELDERLY_65_PLUS",
            title_ko="노인(65+) 병용약물 상호작용·적정 부담 — 자료·교육으로 해소",
            driver_summary_ko="허가 범위 내 치료 장벽 — 교육 자료 제작 검토",
        ))

        # ── 용어 정규화 시드 ─────────────────────────────────────────────
        for surface, lang, canon, label in VOCAB_SEED:
            db.add(VocabTerm(surface_form=surface, lang=lang, canonical_id=canon,
                             canonical_label_ko=label, source="CUSTOM"))
        db.commit()
        return {"documents": len(by_doc), "interactions": len(rows), "claims": n_claims,
                "hypotheses": 2, "vocab": len(VOCAB_SEED)}
    finally:
        db.close()


def ensure_seeded() -> bool:
    """DB가 비어 있을 때만 시드한다 — 클라우드 배포의 빈 볼륨 대응 (docs/07).

    이미 데이터가 있으면 아무것도 하지 않으므로, 심사 중 승인 상태를 덮어쓸 위험이 없다.
    (의도적 초기화는 reset 경로에서 `seed()`를 직접 호출한다.)
    """
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        if db.execute(select(func.count()).select_from(Document)).scalar_one() > 0:
            return False
    finally:
        db.close()
    seed()
    return True
