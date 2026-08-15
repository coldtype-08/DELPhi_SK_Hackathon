# DELPHi backend — Railway 배포용 (docs/07). 빌드 컨텍스트는 backend/ 이다.
FROM python:3.12-slim

# uv로 의존성 설치 (pyproject.toml 단일 소스 — uv.lock으로 버전 고정)
COPY --from=ghcr.io/astral-sh/uv:0.9.9 /uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv pip install --system --no-cache -r pyproject.toml

COPY . .

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Railway가 $PORT를 주입한다. 볼륨(/data)은 DATABASE_URL·DELPHI_CACHE_DIR 환경변수로 연결.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
