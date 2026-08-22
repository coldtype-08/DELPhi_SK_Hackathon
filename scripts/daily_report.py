#!/usr/bin/env python3
"""개발 일지 초안 생성기 — submission/4_제작과정/daily/

git 커밋 · docs/LOG.md · docs/DECISIONS.md 에서 그날의 사실을 모아
사람이 채울 칸만 비워 둔 마크다운 초안을 만든다.

    python3 scripts/daily_report.py                      # 오늘, 3인분
    python3 scripts/daily_report.py --date 2026-08-22    # 특정 날짜
    python3 scripts/daily_report.py --author 소정        # 한 사람만
    python3 scripts/daily_report.py --force              # 기존 파일 덮어쓰기
    python3 scripts/daily_report.py --stdout             # 파일로 쓰지 않고 출력만

의존성 없음 (표준 라이브러리만). 3인 노트북에서 그대로 돌아야 한다.
날짜 경계는 **실행하는 컴퓨터의 로컬 시간** 기준이다 (KST 노트북 = KST 하루).
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(REPO, "submission", "4_제작과정", "daily")

# ── 팀 (파트는 docs/06 §2.5 층 기준) ────────────────────────────────────
MEMBERS = {
    "건태": "도메인 — 스키마·프롬프트·추출 평가·가설/Contract 화면·제출물",
    "인혁": "엔진 — backend 파이프라인 전부",
    "소정": "화면 — Field 전체 + Console 일부 + 디자인 공통",
}

# git 신원 → 팀원. 새 팀원이 커밋을 시작하면 여기에 한 줄 추가한다.
IDENTITIES = {
    "geontaepark@sk.com": "건태",
    "geontaebak@gmail.com": "건태",
}

# Claude Code 세션 커밋은 author 가 Claude 로 찍혀 사람을 구분할 수 없다.
# → 건드린 경로의 오너십(CLAUDE.md)으로 추정하고 ※ 로 표시해 사람이 확인한다.
CLAUDE_IDENTITIES = {"noreply@anthropic.com"}

# 경로 → (오너, WBS, 라벨). 위에서부터 먼저 맞는 것을 쓴다 (구체적인 것 먼저).
PATH_RULES = [
    ("backend/app/prompts/",            "건태", "1.2", "추출·에이전트 프롬프트"),
    ("backend/app/llm.py",              "인혁", "1.1", "LLM 단일 래퍼"),
    ("backend/app/access.py",           "인혁", "1.6", "목적·권한 쿼리 게이트"),
    ("backend/app/contract/",           "건태", "0.5", "Data Contract 정의"),
    ("backend/tests/",                  "인혁", "7.5", "절대 규칙 회귀 테스트"),
    ("backend/app/routers/actions",     "인혁", "5.3", "Action Item API"),
    ("backend/data/cache/",             "인혁", "4.1", "외부 데이터 캐시"),
    ("backend/data/corpus/",            "건태", "0.6", "합성 코퍼스 산출물"),
    ("backend/",                        "인혁", "1.x", "backend 엔진"),
    ("apps/console/app/review",         "소정", "2.1", "Data Review 화면"),
    ("apps/console/app/hypotheses",     "건태", "2.3", "가설 보드·상세"),
    ("apps/console/app/contract",       "건태", "2.4", "Contract 화면"),
    ("apps/console/app/market",         "소정", "2.5", "시장·경쟁 화면"),
    ("apps/console/app/safety",         "소정", "2.6", "안전성·차단 로그"),
    ("apps/console/public/draft.html",  "건태", "8.x", "디자인 초안 배포본"),
    ("apps/console/",                   "건태", "2.x", "Console"),
    ("apps/field/",                     "소정", "3.x", "Field"),
    ("scripts/corpus",                  "건태", "0.6", "합성 코퍼스 생성기"),
    ("scripts/generate",                "건태", "0.6", "합성 코퍼스 생성기"),
    ("scripts/reset_demo",              "인혁", "7.1", "데모 리셋"),
    ("scripts/daily_report",            "건태", "8.2", "개발 일지 도구"),
    ("scripts/",                        "인혁", "0.x", "스크립트"),
    ("submission/",                     "건태", "8.x", "제출물"),
    ("demo/",                           "건태", "8.x", "디자인 초안"),
    ("docs/02_DATA_CONTRACT",           "건태", "0.5", "Data Contract 스펙"),
    ("docs/03_SYNTHETIC_DATA",          "건태", "0.6", "합성 데이터 스펙"),
    ("docs/04_API_SPEC",                "인혁", "1.x", "API 스펙"),
    ("docs/05_DESIGN_SYSTEM",           "소정", "0.2", "디자인 시스템"),
    ("docs/07_DEPLOYMENT",              "인혁", "7.3", "배포·운용"),
    ("docs/",                           "건태", "0.1", "스펙 문서"),
    ("CLAUDE.md",                       "건태", "0.1", "공통 컨텍스트"),
]


def sh(args: list[str]) -> str:
    try:
        return subprocess.run(
            args, cwd=REPO, check=True, capture_output=True, text=True
        ).stdout
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"[daily_report] git 실패: {' '.join(args)}\n{e.stderr}\n")
        return ""


def classify(paths: list[str]) -> tuple[str | None, str, str]:
    """건드린 경로들 → (추정 오너, WBS, 라벨). 가장 많이 맞은 규칙을 쓴다."""
    hits: dict[tuple[str, str, str], int] = {}
    for p in paths:
        for prefix, owner, wbs, label in PATH_RULES:
            if p.startswith(prefix):
                hits[(owner, wbs, label)] = hits.get((owner, wbs, label), 0) + 1
                break
    if not hits:
        return None, "—", "기타"
    (owner, wbs, label), _ = max(hits.items(), key=lambda kv: kv[1])
    return owner, wbs, label


def commits_on(date: str) -> list[dict]:
    """해당 날짜(로컬)의 커밋 목록. 파일 목록 포함."""
    raw = sh([
        # quotepath=false: 한글 경로가 "\355\225..." 로 인용되면 경로 매칭이 전부 실패한다
        "git", "-c", "core.quotepath=false", "log", "--no-merges",
        f"--since={date} 00:00:00", f"--until={date} 23:59:59",
        "--format=__C__%h\x1f%an\x1f%ae\x1f%ad\x1f%s", "--date=format:%H:%M",
        "--name-only",
    ])
    out: list[dict] = []
    cur: dict | None = None
    for line in raw.splitlines():
        if line.startswith("__C__"):
            if cur:
                out.append(cur)
            h, an, ae, ad, subject = line[len("__C__"):].split("\x1f", 4)
            cur = {"hash": h, "an": an, "ae": ae, "time": ad,
                   "subject": subject, "files": []}
        elif line.strip() and cur is not None:
            cur["files"].append(line.strip().strip('"'))
    if cur:
        out.append(cur)
    return out


def attribute(commits: list[dict]) -> tuple[dict[str, list[dict]], list[dict]]:
    """커밋을 사람별로 나눈다. 귀속이 불확실하면 estimated=True 로 표시."""
    by_person: dict[str, list[dict]] = {name: [] for name in MEMBERS}
    unknown: list[dict] = []
    for c in commits:
        owner_guess, wbs, label = classify(c["files"])
        c["wbs"], c["label"] = wbs, label
        person = IDENTITIES.get(c["ae"].lower())
        if person:
            c["estimated"] = False
        elif c["ae"].lower() in CLAUDE_IDENTITIES:
            person = owner_guess
            c["estimated"] = True          # Claude 세션 — 경로 오너십으로 추정
        else:
            person = None
        if person in by_person:
            by_person[person].append(c)
        else:
            unknown.append(c)
    return by_person, unknown


def lines_for_date(path: str, mmdd: str, name: str) -> list[str]:
    """docs/LOG.md · DECISIONS.md 에서 '- MM/DD ...' 중 그 사람 줄만.

    LOG      : `- 08/21 건태(Claude 세션): ...`
    DECISIONS: `- 08/21 [건태] ...`
    이름이 안 걸리면 빈 목록 — 남의 줄을 내 일지에 넣지 않는다.
    """
    full = os.path.join(REPO, path)
    if not os.path.exists(full):
        return []
    pat = re.compile(r"^\s*-\s*" + re.escape(mmdd) + r"\b")
    out = []
    with open(full, encoding="utf-8") as f:
        for ln in f:
            if not pat.match(ln):
                continue
            head = ln[:60]           # 날짜 바로 뒤 이름 표기 구간
            if name in head:
                out.append(ln.rstrip())
    return out


def headline(line: str, limit: int = 150) -> str:
    """긴 기록 줄에서 제목만 뽑는다. **강조** 구간이 있으면 그것이 제목이다."""
    body = re.sub(r"^\s*-\s*\d{2}/\d{2}\s*", "", line).strip()
    m = re.search(r"\*\*(.+?)\*\*", body)
    if m:
        return m.group(1).strip()
    return body if len(body) <= limit else body[:limit].rstrip() + "…"


def render(name: str, date: str, commits: list[dict],
           log_lines: list[str], decisions: list[str]) -> str:
    part = MEMBERS[name]
    L: list[str] = []
    L.append(f"# {date} · {name} ({part.split(' — ')[0]})")
    L.append("")
    L.append(f"> 파트: {part}")
    L.append(f"> 초안 자동 생성 (`scripts/daily_report.py`) — **아래 ✏️ 칸은 사람이 채운다.** 표의 `※` 는 귀속 추정이니 확인해 주세요.")
    L.append("")
    L.append("## 오늘 한 것")
    L.append("")
    if commits:
        L.append("| WBS | 무엇을 | 커밋 | 파일 |")
        L.append("|---|---|---|---|")
        for c in commits:
            mark = " ※" if c.get("estimated") else ""
            files = len(c["files"])
            head = c["files"][0] if c["files"] else "—"
            more = f" 외 {files - 1}개" if files > 1 else ""
            L.append(
                f"| {c['wbs']}{mark} | {c['subject']} | `{c['hash']}` {c['time']} "
                f"| `{head}`{more} |"
            )
    else:
        L.append("| WBS | 무엇을 | 커밋 | 파일 |")
        L.append("|---|---|---|---|")
        L.append("| | ✏️ 커밋이 없는 날 — 검수·회의·조사도 일이다. 무엇을 했는지 적는다 | — | — |")
    L.append("")
    if log_lines:
        L.append(f"<details><summary>docs/LOG.md 이 날의 줄 {len(log_lines)}건</summary>")
        L.append("")
        for ln in log_lines:
            L.append(f"- {headline(ln)}")
        L.append("")
        L.append("</details>")
        L.append("")
    L.append("## 막힌 것")
    L.append("")
    L.append("> 없으면 \"없음\" 한 줄. **있는데 안 적으면 그날 일이 사라진다.**")
    L.append("")
    L.append("- **증상**: ✏️")
    L.append("- **시도**: ✏️")
    L.append("- **결과**: 해결 / 미해결 / 우회")
    L.append("- `BLOCKERS.md` 에 올릴 것인가: 예 / 아니오")
    L.append("")
    L.append("## 결정한 것")
    L.append("")
    L.append("> ✏️ 30분 이상 고민한 갈림길만. 없으면 \"없음\". 있으면 `docs/DECISIONS.md` 에도 한 줄.")
    L.append("")
    if decisions:
        L.append(f"<details><summary>docs/DECISIONS.md 이 날의 결정 {len(decisions)}건 (제목만 — 전문은 그쪽)</summary>")
        L.append("")
        for ln in decisions:
            L.append(f"- {headline(ln)}")
        L.append("")
        L.append("</details>")
    else:
        L.append("-")
    L.append("")
    L.append("## 내일 할 것")
    L.append("")
    L.append("| WBS | 무엇을 |")
    L.append("|---|---|")
    L.append("| ✏️ | |")
    L.append("")
    L.append("## 오늘의 한 줄")
    L.append("")
    L.append("> ✏️ 하루를 한 문장으로.")
    L.append("")
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="개발 일지 초안 생성")
    ap.add_argument("--date", help="YYYY-MM-DD (기본: 오늘)")
    ap.add_argument("--author", help="팀원 이름 하나만 (기본: 3인 전원)")
    ap.add_argument("--force", action="store_true", help="기존 파일 덮어쓰기")
    ap.add_argument("--stdout", action="store_true", help="파일로 쓰지 않고 출력")
    a = ap.parse_args()

    date = a.date or dt.date.today().isoformat()
    try:
        d = dt.date.fromisoformat(date)
    except ValueError:
        sys.stderr.write(f"[daily_report] 날짜 형식이 아닙니다: {date}\n")
        return 2
    mmdd = f"{d.month:02d}/{d.day:02d}"

    targets = [a.author] if a.author else list(MEMBERS)
    for t in targets:
        if t not in MEMBERS:
            sys.stderr.write(
                f"[daily_report] 모르는 이름: {t} (가능: {', '.join(MEMBERS)})\n")
            return 2

    by_person, unknown = attribute(commits_on(date))

    os.makedirs(OUT_DIR, exist_ok=True)
    for name in targets:
        body = render(
            name, date, by_person[name],
            lines_for_date("docs/LOG.md", mmdd, name),
            lines_for_date("docs/DECISIONS.md", mmdd, name),
        )
        if a.stdout:
            print(body)
            continue
        path = os.path.join(OUT_DIR, f"{date}_{name}.md")
        if os.path.exists(path) and not a.force:
            print(f"  건너뜀 {os.path.relpath(path, REPO)} (이미 있음 — --force 로 덮어쓰기)")
            continue
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
        n = len(by_person[name])
        print(f"  생성   {os.path.relpath(path, REPO)}  (커밋 {n}건)")

    if unknown:
        sys.stderr.write(
            f"\n[daily_report] 귀속 못 한 커밋 {len(unknown)}건 — "
            f"IDENTITIES 에 신원을 추가하세요:\n")
        for c in unknown:
            sys.stderr.write(f"  {c['hash']} {c['an']} <{c['ae']}> {c['subject']}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
