#!/usr/bin/env python3
"""
check_bodies.py — scripts/corpus_bodies/*.json 전수 검증 (2026-08-14)

generate_corpus.py의 실제 검증기(validate_block)와 각본(PLANTED·DOC_PLAN·PII_SENTENCE)을 그대로 import해서
준비된 본문 전부를 대조한다. 본문을 누가/어떻게 썼는지와 무관하게 이 스크립트만 통과하면 생성 가능하다.

사용: python3 scripts/check_bodies.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_corpus as g


def main():
    docs = {d["key"]: d for d in g.build_scenario()}
    bodies = g.load_bodies()
    expected = {k: [b["block_index"] for b in d["blocks"]]
                for k, d in docs.items() if d["source_type"] != "VOICE_TRANSCRIPT"}

    errors, warnings = [], []
    have = 0

    for key, block_idxs in sorted(expected.items()):
        doc = docs[key]
        for bi in block_idxs:
            body = bodies.get(key, {}).get(bi)
            if body is None:
                errors.append(f"{key}.{bi}  본문 없음")
                continue
            have += 1
            block = next(b for b in doc["blocks"] if b["block_index"] == bi)
            ok, err = g.validate_block(doc, block, body)
            if not ok:
                errors.append(f"{key}.{bi}  {err}")

    # 각본에 없는 키가 섞여 있는지
    for key, blocks in bodies.items():
        if key not in expected:
            errors.append(f"{key}  각본에 없는 문서 키")
            continue
        for bi in blocks:
            if bi not in expected[key]:
                errors.append(f"{key}.{bi}  각본에 없는 블록 번호")

    # 문서 단위 조립까지 시뮬레이션 — 오프셋·블록 경계·PII 위치까지 확인
    assembled = 0
    for key, block_idxs in sorted(expected.items()):
        doc = docs[key]
        if any(bodies.get(key, {}).get(bi) is None for bi in block_idxs):
            continue
        txt, spans = g.assemble_doc(doc, [bodies[key][bi] for bi in block_idxs])
        assembled += 1
        for b in doc["blocks"]:
            span = next(s for s in spans if s[0] == b["block_index"])
            for p in b["planted"]:
                start = txt.find(p["verbatim"])
                if txt.count(p["verbatim"]) != 1:
                    errors.append(f"{key}.{b['block_index']}  문서 전체에서 신호 문장이 {txt.count(p['verbatim'])}회")
                elif not (span[1] <= start and start + len(p["verbatim"]) <= span[2]):
                    errors.append(f"{key}.{b['block_index']}  신호 문장이 블록 범위 밖")
        for kind, literal in doc["pii"]:
            if txt.count(literal) != 1:
                errors.append(f"{key}  PII '{literal}' {txt.count(literal)}회 (1회 필요)")
        # 리얼리티 참고 지표 (경고만)
        if doc["source_type"] == "MEETING_NOTE":
            wc = len(txt.split())
            if not (100 <= wc <= 320):
                warnings.append(f"{key}  단어 수 {wc} (권장 120–260 + 헤더)")

    total = sum(len(v) for v in expected.values())
    print(f"본문 {have}/{total} 블록 · 조립 검증 {assembled}/{len(expected)} 문서")
    for w in warnings:
        print(f"  [경고] {w}")
    if errors:
        print(f"\n실패 {len(errors)}건:")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    if have < total:
        print(f"\n미완: {total - have}개 블록의 본문이 아직 없습니다 (검증된 부분은 모두 통과).")
        sys.exit(2)
    print("\n전수 통과 — 생성 가능 (bash scripts/generate.sh)")


if __name__ == "__main__":
    main()
