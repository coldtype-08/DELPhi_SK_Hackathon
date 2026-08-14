#!/usr/bin/env bash
# 합성 코퍼스 생성 실행기 — uv가 의존성(anthropic·python-docx·reportlab·pypdf)을 임시 환경에 자동 설치
# 사용: bash scripts/generate.sh [--limit 3] [--dry-run]
set -euo pipefail
cd "$(dirname "$0")/.."
exec uv run --with anthropic --with python-docx --with reportlab --with pypdf scripts/generate_corpus.py "$@"
