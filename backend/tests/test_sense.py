"""Sense 추출의 **결정론 부분**만 검증한다 — LLM 호출 없이, 네트워크 없이.

여기서 지키는 것은 절대 규칙 #1·#2·#3·#6이다. LLM이 무엇을 골랐는지는 이 테스트의 관심사가
아니고(그건 ground_truth 대조의 몫), **LLM이 틀린 것을 냈을 때 시스템이 막는지**를 본다.

실행: uv run --project backend --with pytest python -m pytest backend/tests -q
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app import sense                                                   # noqa: E402
from app.db import Base                                                 # noqa: E402
from app.models import (                                                # noqa: E402
    BlockedLog, Claim, Document, Interaction, SafetyCandidate, UnmappedTerm, VocabTerm,
)

# 블록 두 개짜리 문서 — 두 번째 의료진의 문장을 첫 번째에게 붙이지 못하는지 보려고 둘로 나눴다.
BLOCK_A = "Raised the adolescent patients who wait until 18 for an approved option."
BLOCK_B = "Noted the interaction checks required before starting anyone elderly."
DOC_TEXT = BLOCK_A + "\n\n" + BLOCK_B
A_START, A_END = 0, len(BLOCK_A)
B_START, B_END = len(BLOCK_A) + 2, len(DOC_TEXT)

CONTRACT = {
    "version": "0.1",
    "fields": {
        "signal_type": {"label_ko": "신호 유형", "required": True, "values": [
            {"value": "UNMET_NEED", "label_ko": "미충족 수요"},
            {"value": "TREATMENT_BARRIER", "label_ko": "치료 장벽"},
            {"value": "SAFETY_CANDIDATE", "label_ko": "안전성 후보"},
            {"value": "OTHER", "label_ko": "기타"},
        ]},
        "patient_segment": {"label_ko": "환자군", "required": True, "values": [
            {"value": "PEDIATRIC_TRANSITION", "label_ko": "청소년", "label_scope": "OUT_OF_LABEL"},
            {"value": "ELDERLY_65_PLUS", "label_ko": "노인"},
            {"value": "UNSPECIFIED", "label_ko": "미지정"},
        ]},
        "barrier_type": {"label_ko": "장벽 유형",
                         "required_if": {"field": "signal_type", "equals": "TREATMENT_BARRIER"},
                         "values": [{"value": "DDI_CONCERN", "label_ko": "상호작용 우려"}]},
    },
}


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    now = datetime.now(timezone.utc).isoformat()
    s.add(Document(id="DOC-1", filename="d.txt", source_format="TXT", language="EN",
                   raw_text=DOC_TEXT, sha256="x", imported_at=now))
    for iid, hcp, lo, hi, bi, txt in [("INT-1", "HCP-001", A_START, A_END, 1, BLOCK_A),
                                      ("INT-2", "HCP-002", B_START, B_END, 2, BLOCK_B)]:
        s.add(Interaction(interaction_id=iid, document_id="DOC-1", occurred_on="2026-01-01",
                          hcp_ref=hcp, hcp_specialty="Neurology", region="NE", setting="CLINIC",
                          source_type="HIGHLIGHT_DOC", raw_text=txt, block_index=bi,
                          doc_char_start=lo, doc_char_end=hi))
    s.add(VocabTerm(surface_form="adolescent", lang="EN",
                    canonical_id="PEDIATRIC_TRANSITION", canonical_label_ko="청소년"))
    s.commit()
    yield s
    s.close()


def run(db, monkeypatch, payload, *, force=False):
    """call_llm 을 가짜 응답으로 갈아끼우고 파이프라인을 돌린다."""
    monkeypatch.setattr(sense, "load_active_contract", lambda _db: CONTRACT)
    monkeypatch.setattr(sense, "build_system_text", lambda c, i: "system")
    calls = iter(payload)
    monkeypatch.setattr(sense, "call_llm", lambda db, **kw: next(calls, {"claims": [], "safety": []}))
    return sense.extract_document(db, "DOC-1", force=force)


# ── 근거 검증 (절대 규칙 #2) ────────────────────────────────────────────────


def test_인용문이_원문과_같으면_오프셋이_정확히_계산된다(db, monkeypatch):
    quote = "adolescent patients who wait until 18"
    r = run(db, monkeypatch, [{"claims": [{
        "verbatim_quote": quote, "summary_ko": "청소년 대기",
        "signal_type": "UNMET_NEED", "patient_segment": "PEDIATRIC_TRANSITION"}], "safety": []}])
    assert r["claims"] == 1
    c = db.execute(select(Claim)).scalar_one()
    ev = json.loads(c.evidence_json)
    assert DOC_TEXT[ev["char_start"]:ev["char_end"]] == quote
    assert c.status == "CANDIDATE"                      # 절대 규칙 #3
    assert c.label_scope == "OUT_OF_LABEL"              # 파생 규칙 — 청소년은 허가 범위 밖
    assert c.review_grade == "HIGH"


@pytest.mark.parametrize("bad,왜", [
    ("adolescent patients who wait until 19", "숫자를 바꿨다"),
    ("adolescent  patients who wait until 18", "공백을 늘렸다"),
    ("Adolescent patients who wait until 18", "대소문자를 고쳤다"),
    ("adolescent patients … until 18", "줄임표를 넣었다"),
    ("청소년 환자들이 18세까지 기다린다", "번역했다"),
])
def test_인용문이_한_글자라도_다르면_저장하지_않는다(db, monkeypatch, bad, 왜):
    r = run(db, monkeypatch, [{"claims": [{
        "verbatim_quote": bad, "summary_ko": "x",
        "signal_type": "UNMET_NEED", "patient_segment": "PEDIATRIC_TRANSITION"}], "safety": []}])
    assert r["claims"] == 0, 왜
    assert r["rejected_no_evidence"] == 1
    assert db.execute(select(Claim)).first() is None
    log = db.execute(select(BlockedLog)).scalar_one()
    assert log.reason_code == "VERBATIM_NOT_FOUND"      # 버렸다는 사실은 남는다


def test_다른_의료진_블록의_문장은_이_의료진에게_붙지_않는다(db, monkeypatch):
    """가장 위험한 오류 — 문서 전체에는 있는 문장이지만 이 블록에는 없다."""
    r = run(db, monkeypatch, [{"claims": [{
        "verbatim_quote": "interaction checks required before starting anyone elderly",
        "summary_ko": "노인 상호작용", "signal_type": "UNMET_NEED",
        "patient_segment": "ELDERLY_65_PLUS"}], "safety": []}])
    assert r["claims"] == 0 and r["rejected_no_evidence"] == 1


# ── 등급 (docs/02 §5) ───────────────────────────────────────────────────────


def test_등급_규칙_H_M_L():
    assert sense.grade(True, True) == "HIGH"
    assert sense.grade(False, True) == "MEDIUM"     # ② 용어 매핑 실패
    assert sense.grade(True, False) == "LOW"        # ③ 파생 규칙 실패
    assert sense.grade(False, False) == "LOW"


def test_조건부_필수를_안_채우면_LOW로_큐_위쪽에_온다(db, monkeypatch):
    r = run(db, monkeypatch, [{"claims": [{
        "verbatim_quote": "adolescent patients", "summary_ko": "x",
        "signal_type": "TREATMENT_BARRIER", "patient_segment": "PEDIATRIC_TRANSITION",
        "barrier_type": None}], "safety": []}])
    assert r["claims"] == 1
    assert db.execute(select(Claim)).scalar_one().review_grade == "LOW"


# ── 용어 매핑 (체크 ②) ─────────────────────────────────────────────────────


def test_스키마에_없는_환자군은_UNSPECIFIED로_낙착되고_미매핑_용어로_쌓인다(db, monkeypatch):
    """S3(post-stroke) 시나리오 — 이 카운트가 SCP 제안의 근거가 된다 (docs/02 §7)."""
    r = run(db, monkeypatch, [{"claims": [{
        "verbatim_quote": "adolescent patients", "summary_ko": "x",
        "signal_type": "UNMET_NEED", "patient_segment": "POST_STROKE",
        "patient_segment_surface": "post-stroke epilepsy"}], "safety": []}])
    assert r["claims"] == 1 and r["unmapped"] == 1
    c = db.execute(select(Claim)).scalar_one()
    assert c.patient_segment == "UNSPECIFIED"
    assert c.review_grade == "MEDIUM"               # ② 실패, ③ 통과
    assert db.execute(select(UnmappedTerm)).scalar_one().surface_form == "post-stroke epilepsy"


def test_원문_표현은_vocab을_통해_canonical로_수렴한다(db, monkeypatch):
    r = run(db, monkeypatch, [{"claims": [{
        "verbatim_quote": "adolescent patients", "summary_ko": "x",
        "signal_type": "UNMET_NEED", "patient_segment": "UNSPECIFIED",
        "patient_segment_surface": "adolescent"}], "safety": []}])
    assert r["claims"] == 1
    c = db.execute(select(Claim)).scalar_one()
    assert c.patient_segment == "PEDIATRIC_TRANSITION" and c.review_grade == "HIGH"


# ── 안전성 분리 (절대 규칙 #6) ──────────────────────────────────────────────


def test_안전성_후보는_claims에_한_건도_들어가지_않는다(db, monkeypatch):
    r = run(db, monkeypatch, [{"claims": [], "safety": [{
        "verbatim_quote": "adolescent patients", "event_terms": "dizziness",
        "severity_note": None, "product_named": True}]}])
    assert r["safety"] == 1 and r["claims"] == 0
    assert db.execute(select(Claim)).first() is None
    s = db.execute(select(SafetyCandidate)).scalar_one()
    assert s.event_terms == "dizziness" and s.status == "OPEN"


def test_LLM이_안전성을_claims에_넣어도_서버가_safety로_돌린다(db, monkeypatch):
    r = run(db, monkeypatch, [{"claims": [{
        "verbatim_quote": "adolescent patients", "summary_ko": "x",
        "signal_type": "SAFETY_CANDIDATE", "patient_segment": "UNSPECIFIED"}], "safety": []}])
    assert r["claims"] == 0 and r["safety"] == 1 and r["safety_rerouted"] == 1
    assert db.execute(select(Claim)).first() is None


# ── 재실행 ──────────────────────────────────────────────────────────────────


def test_두_번_돌려도_claim이_중복되지_않는다(db, monkeypatch):
    payload = [{"claims": [{"verbatim_quote": "adolescent patients", "summary_ko": "x",
                            "signal_type": "UNMET_NEED",
                            "patient_segment": "PEDIATRIC_TRANSITION"}], "safety": []}]
    run(db, monkeypatch, payload)
    again = run(db, monkeypatch, payload)
    assert again["skipped"] is True
    assert db.execute(select(Claim)).scalars().all().__len__() == 1


def test_force면_기존_claim을_지우고_다시_넣는다(db, monkeypatch):
    payload = [{"claims": [{"verbatim_quote": "adolescent patients", "summary_ko": "x",
                            "signal_type": "UNMET_NEED",
                            "patient_segment": "PEDIATRIC_TRANSITION"}], "safety": []}]
    run(db, monkeypatch, payload)
    r = run(db, monkeypatch, payload, force=True)
    assert r["skipped"] is False and r["claims"] == 1
    assert len(db.execute(select(Claim)).scalars().all()) == 1


# ── 노이즈 ──────────────────────────────────────────────────────────────────


def test_신호가_없는_블록은_빈_결과가_정상이다(db, monkeypatch):
    r = run(db, monkeypatch, [{"claims": [], "safety": []}, {"claims": [], "safety": []}])
    assert r["blocks"] == 2 and r["claims"] == 0 and r["rejected_no_evidence"] == 0
