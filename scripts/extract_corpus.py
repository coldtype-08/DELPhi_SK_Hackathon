#!/usr/bin/env python3
"""
extract_corpus.py — 원석 코퍼스에 Sense 추출을 돌려 claims를 채우고 LLM 캐시를 만든다.

[08/22 신설 · [cross] scripts/·backend/ 는 인혁 오너십 — 협의 필요]

왜 스크립트인가: 추출은 **한 번 돌려서 결과를 커밋해 두는 작업**이다.
심사위원 환경과 발표 현장은 네트워크·API 키 없이도 같은 결과를 보여줘야 하므로
(`docs/07 §4.5`), 응답을 `backend/data/llm_cache/`에 남기고 그 폴더를 커밋한다.
두 번째 실행부터는 API를 호출하지 않는다.

사용 (레포 루트에서):
  # 키 필요 — 레포 루트 .env 에 ANTHROPIC_API_KEY (커밋 금지)
  uv run --project backend python scripts/extract_corpus.py --limit 5      # 맛보기 5건
  uv run --project backend python scripts/extract_corpus.py                # 전체 320건
  uv run --project backend python scripts/extract_corpus.py --doc DOC-2026...  # 1건만
  uv run --project backend python scripts/extract_corpus.py --dry-run      # 대상·비용만 계산

  # 키 없이 캐시만으로 재적재 (심사위원 환경·CI)
  DEMO_OFFLINE=1 uv run --project backend python scripts/extract_corpus.py --force
"""

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from sqlalchemy import func, select                      # noqa: E402
from app.db import SessionLocal                          # noqa: E402
from app.llm import LlmUnavailable, cache_stats          # noqa: E402
from app.models import Claim, Document, Interaction, SafetyCandidate  # noqa: E402
from app.sense import extract_document                   # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="앞에서 N건만 (0=전체)")
    ap.add_argument("--doc", action="append", default=[], help="특정 문서 ID (반복 가능)")
    ap.add_argument("--force", action="store_true", help="이미 추출된 문서도 다시 (기존 claim 삭제)")
    ap.add_argument("--dry-run", action="store_true", help="대상만 세고 호출하지 않는다")
    args = ap.parse_args()

    db = SessionLocal()
    try:
        q = select(Document.id).order_by(Document.id)
        doc_ids = [d for d in db.execute(q).scalars().all()]
        if args.doc:
            missing = [d for d in args.doc if d not in doc_ids]
            if missing:
                sys.exit(f"없는 문서 ID: {', '.join(missing)}")
            doc_ids = args.doc
        if args.limit:
            doc_ids = doc_ids[: args.limit]

        n_blocks = db.execute(
            select(func.count()).select_from(Interaction)
            .where(Interaction.document_id.in_(doc_ids))
        ).scalar_one()
        print(f"대상: 문서 {len(doc_ids)}건 · 의료진 블록 {n_blocks}개")
        print(f"캐시: {cache_stats()['entries']}건 ({cache_stats()['dir']})")
        if args.dry_run:
            print("dry-run 종료 — 블록 1개당 LLM 1회 호출(캐시 미적중 시).")
            return

        total = {"claims": 0, "safety": 0, "rejected_no_evidence": 0, "unmapped": 0,
                 "skipped": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        t0 = time.time()
        for i, doc_id in enumerate(doc_ids, 1):
            try:
                r = extract_document(db, doc_id, force=args.force)
            except LlmUnavailable as e:
                sys.exit(f"\n중단 — {e}")
            if r.get("skipped"):
                total["skipped"] += 1
                print(f"[{i}/{len(doc_ids)}] {doc_id} 건너뜀 (claim {r['existingClaims']}건 존재)")
                continue
            for k in ("claims", "safety", "rejected_no_evidence", "unmapped"):
                total[k] += r[k]
            for g in ("HIGH", "MEDIUM", "LOW"):
                total[g] += r["by_grade"][g]
            print(f"[{i}/{len(doc_ids)}] {doc_id} 블록 {r['blocks']} · "
                  f"claim {r['claims']}(H{r['by_grade']['HIGH']}/M{r['by_grade']['MEDIUM']}/"
                  f"L{r['by_grade']['LOW']}) · 안전성 {r['safety']} · 거부 {r['rejected_no_evidence']}")

        db_claims = db.execute(select(func.count()).select_from(Claim)).scalar_one()
        db_safety = db.execute(select(func.count()).select_from(SafetyCandidate)).scalar_one()
        print(f"\n완료 ({time.time() - t0:.0f}s) — 이번 실행: claim {total['claims']}건 "
              f"(H {total['HIGH']} / M {total['MEDIUM']} / L {total['LOW']}) · "
              f"안전성 {total['safety']} · 근거 불일치로 거부 {total['rejected_no_evidence']} · "
              f"미매핑 용어 {total['unmapped']} · 건너뜀 {total['skipped']}문서")
        print(f"DB 누계: claims {db_claims} · safety_candidates {db_safety}")
        print(f"캐시: {cache_stats()['entries']}건 — `git add backend/data/llm_cache` 를 잊지 마세요")
    finally:
        db.close()


if __name__ == "__main__":
    main()
