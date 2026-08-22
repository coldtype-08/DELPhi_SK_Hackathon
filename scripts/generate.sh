#!/usr/bin/env bash
# 합성 코퍼스 생성 실행기 — uv가 의존성(anthropic·python-docx·reportlab·pypdf)을 임시 환경에 자동 설치
# 사용: bash scripts/generate.sh [--limit 3] [--dry-run]
set -euo pipefail
cd "$(dirname "$0")/.."
# cryptography 명시 이유: 일부 환경(컨테이너)에서 pypdf가 시스템 dist-packages의
# cryptography를 집어 rust 바인딩이 panic한다. uv 환경에 직접 설치해 가려준다 (08/22).
exec uv run --with anthropic --with python-docx --with reportlab --with pypdf --with cryptography \
  scripts/generate_corpus.py "$@"
