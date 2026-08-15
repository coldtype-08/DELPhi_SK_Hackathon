"""DELPHi backend 진입점 — 라우터 등록, CORS(3000·3001), 오류 응답 형태 통일 (docs/04 공통 규약)."""

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import ALLOWED_ORIGINS, SEED_ON_STARTUP
from .db import init_db
from .routers import aggregates, claims, contract, documents, field, hypotheses, safety, system

app = FastAPI(title="DELPHi API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],  # X-Delphi-Role 포함
)


@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    # 실패 응답은 항상 { "error": { code, message_ko } } (docs/04 공통)
    detail = exc.detail if isinstance(exc.detail, dict) else {"code": "ERROR", "message_ko": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content={"error": detail})


@app.exception_handler(RequestValidationError)
async def validation_error(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={
        "error": {"code": "VALIDATION_ERROR", "message_ko": "요청 형식이 스펙(docs/04)과 다릅니다.", "detail": exc.errors()},
    })


@app.on_event("startup")
def startup():
    init_db()
    if SEED_ON_STARTUP:
        # 배포본의 빈 볼륨 대응 — 이미 데이터가 있으면 아무것도 하지 않는다 (docs/07 §2)
        from .seed import ensure_seeded

        if ensure_seeded():
            print("[startup] 빈 DB를 감지해 코퍼스를 시드했습니다.")


for r in (documents, claims, aggregates, hypotheses, contract, field, safety, system):
    app.include_router(r.router, prefix="/api")
