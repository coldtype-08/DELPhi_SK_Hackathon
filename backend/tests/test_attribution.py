"""발언 귀속의 **결정론 부분** 검증 — LLM 없이.

AI는 경계 문자열을 인용할 뿐이고 문자 위치는 파이썬이 찾는다 (절대 규칙 #1).
인용이 원문과 다르거나 문서 안에서 유일하지 않으면 그 구간은 **버려진다** (절대 규칙 #2).
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app import attribution                                   # noqa: E402
from app.db import Base                                       # noqa: E402
from app.models import Document, Interaction                  # noqa: E402

HEAD = "[SYNTHETIC SAMPLE] Fictional record.\n\n"
A = "HCP: Ada Bellweather, MD, Northfield Neurology\nRaised the adolescent gap that keeps coming up."
B = "HCP: Cyrus Danforth, MD, Westgate Epilepsy Center\nNoted the interaction checks before any start."
DOC = HEAD + A + "\n\n" + B
A_LO, A_HI = len(HEAD), len(HEAD) + len(A)
B_LO, B_HI = A_HI + 2, len(DOC)


@pytest.fixture()
def db():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)()
    now = datetime.now(timezone.utc).isoformat()
    s.add(Document(id="DOC-1", filename="d.txt", source_format="TXT", language="EN",
                   raw_text=DOC, sha256="x", imported_at=now))
    for iid, hcp, lo, hi, bi in [("INT-1", "HCP-001", A_LO, A_HI, 1),
                                 ("INT-2", "HCP-002", B_LO, B_HI, 2)]:
        s.add(Interaction(interaction_id=iid, document_id="DOC-1", occurred_on="2026-01-01",
                          hcp_ref=hcp, hcp_specialty="Neurology", region="NE", setting="CLINIC",
                          source_type="HIGHLIGHT_DOC", raw_text=DOC[lo:hi], block_index=bi,
                          doc_char_start=lo, doc_char_end=hi))
    s.commit()
    yield s
    s.close()


def run(db, monkeypatch, out):
    monkeypatch.setattr(attribution, "build_system_text", lambda *a, **k: "system")
    monkeypatch.setattr(attribution, "call_agent", lambda db, name, **kw: out)
    return attribution.attribute_document(db, "DOC-1")


GOOD = {"blocks": [
    {"hcp_surface": "Ada Bellweather, MD", "confidence": "CLEAR",
     "start_quote": "HCP: Ada Bellweather, MD, Northfield Neurology",
     "end_quote": "Raised the adolescent gap that keeps coming up."},
    {"hcp_surface": "Cyrus Danforth, MD", "confidence": "CLEAR",
     "start_quote": "HCP: Cyrus Danforth, MD, Westgate Epilepsy Center",
     "end_quote": "Noted the interaction checks before any start."},
]}


def test_경계_인용이_맞으면_오프셋이_정확히_복원된다(db, monkeypatch):
    r = run(db, monkeypatch, GOOD)
    assert [(b["charStart"], b["charEnd"]) for b in r["blocks"]] == [(A_LO, A_HI), (B_LO, B_HI)]
    assert r["dropped"] == []
    assert r["score"]["matched"] == 2 and r["score"]["blockRecall"] == 1.0
    assert r["score"]["meanIou"] == 1.0


def test_경계_인용이_원문에_없으면_그_구간만_버린다(db, monkeypatch):
    out = {"blocks": [GOOD["blocks"][0],
                      {**GOOD["blocks"][1], "start_quote": "HCP: Cyrus Danforth, M.D."}]}
    r = run(db, monkeypatch, out)
    assert len(r["blocks"]) == 1
    assert r["dropped"] == [{"hcpSurface": "Cyrus Danforth, MD", "reason": "START_QUOTE_NOT_FOUND"}]
    assert r["score"]["missed"] == 1 and r["score"]["blockRecall"] == 0.5


def test_문서에_두_번_나오는_문자열은_경계로_쓰지_않는다(db, monkeypatch):
    """위치를 정할 수 없으면 추측하지 않는다 — 'HCP:' 는 두 블록 모두에 있다."""
    out = {"blocks": [{**GOOD["blocks"][0], "start_quote": "HCP:"}]}
    r = run(db, monkeypatch, out)
    assert r["blocks"] == []
    assert r["dropped"][0]["reason"] == "START_QUOTE_NOT_FOUND"


def test_구간이_겹치면_뒤엣것을_버린다(db, monkeypatch):
    out = {"blocks": [
        {**GOOD["blocks"][0], "end_quote": "Noted the interaction checks before any start."},
        GOOD["blocks"][1],
    ]}
    r = run(db, monkeypatch, out)
    assert len(r["blocks"]) == 1 and r["dropped"][0]["reason"] == "OVERLAPS_PREVIOUS"


def test_경계가_어긋나면_IoU로_감점된다(db, monkeypatch):
    """머리말까지 끌어온 경우 — 구간은 남지만 그 블록은 '맞았다'로 세지 않는다.

    IoU 0.8 이 기준선이다. 머리말 38자를 끌어오면 0.71 로 떨어져 미달이 된다 —
    "대충 그 근처"를 정답으로 세면 채점이 의미를 잃으므로 선을 낮추지 않는다.
    """
    out = {"blocks": [{**GOOD["blocks"][0], "start_quote": "[SYNTHETIC SAMPLE] Fictional record."},
                      GOOD["blocks"][1]]}
    r = run(db, monkeypatch, out)
    assert r["blocks"][0]["charStart"] == 0        # 버려지지는 않는다
    assert r["dropped"] == []
    assert r["score"]["matched"] == 1              # 머리말을 끌어온 블록은 미달
    assert 0.8 < r["score"]["meanIou"] < 1.0


def test_커버리지와_확신도가_집계된다(db, monkeypatch):
    out = {"blocks": [GOOD["blocks"][0], {**GOOD["blocks"][1], "confidence": "UNCERTAIN"}]}
    r = run(db, monkeypatch, out)
    assert r["confidenceCounts"] == {"CLEAR": 1, "INFERRED": 0, "UNCERTAIN": 1}
    assert 0.8 < r["coverageRatio"] <= 1.0        # 머리말만큼 빠진다


def test_정답_분할이_없는_문서면_채점을_생략한다(db, monkeypatch):
    """진짜 사내 원석에는 manifest가 없다 — 그때는 blocks만 쓰고 score는 비어 나온다."""
    for it in db.query(Interaction).all():
        it.doc_char_start = it.doc_char_end = None
    db.commit()
    r = run(db, monkeypatch, GOOD)
    assert r["score"] is None and len(r["blocks"]) == 2
