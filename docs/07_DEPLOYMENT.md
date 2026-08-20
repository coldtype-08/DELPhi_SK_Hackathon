# 07. 배포 — 심사위원 상시 접속 (Railway)

> 08/14 확정 (DECISIONS 08/14). 배경: 주최측 요건이 "심사위원이 접속 가능해야 함"이고 기간이 불명확 → 가장 안전한 **상시 접속 기준**으로 설계. 당일 접속으로 확정돼도 이 구성 그대로 쓰고 URL 공유만 늦추면 된다.
> **원칙: 무대 위 라이브 발표의 정본은 여전히 로컬 + 캐시다** (docs/00 §0). 클라우드는 심사위원의 자유 접속용 별도 트랙이며, 배포가 죽어도 발표는 무사해야 한다.

## 1. 왜 Vercel이 아니라 Railway 하나인가

- 백엔드가 FastAPI + **SQLite 파일 DB**라서 서버리스(Vercel Functions)에서는 디스크가 사라져 DB가 살 수 없다. 백엔드에는 **영구 디스크(볼륨)가 붙는 상시 서버**가 필요하다.
- 그런 서버를 주는 Railway는 Next.js 두 개도 같이 돌린다 → 비개발자 3인 팀은 **플랫폼 하나만** 배우면 된다 (대시보드·환경변수·로그·도메인 관리 지점 1곳).
- 대안(프론트 Vercel + 백엔드 Railway 분리)은 관리 지점이 두 배라 기각.

## 1.5 레포에 이미 들어있는 배포 설정 (08/15 — 스캐폴딩과 함께 선행)

Railway 대시보드에서 클릭할 것을 최소화하도록 설정 파일을 미리 커밋해 두었다.

| 파일 | 역할 |
|---|---|
| `backend/Dockerfile` | python:3.12-slim + uv로 `pyproject.toml`(+`uv.lock`) 설치 → `uvicorn --host 0.0.0.0 --port $PORT` |
| `backend/railway.json` | 빌더를 DOCKERFILE로 고정 (자동 감지에 맡기지 않는다) |
| `apps/console/railway.json`, `apps/field/railway.json` | `npm ci && npm run build` → `npm run start` (Next는 `PORT` 환경변수를 따른다) |
| `backend/.dockerignore` | `.venv`·로컬 `delphi.db`·`cache/`·`.env` 제외 (코퍼스와 fixtures는 이미지에 포함) |

**서버가 스스로 시드한다**: 배포하면 볼륨이 비어 있으므로, 기동 시 `documents`가 0건이면 코퍼스를 자동 적재한다(`app/seed.py: ensure_seeded`). 이미 데이터가 있으면 아무것도 하지 않으므로 심사 중 승인 상태를 덮어쓸 위험이 없다. 끄려면 `SEED_ON_STARTUP=0`.

**리셋은 API로 한다**: `POST /api/system/reset` + `X-Reset-Token` 헤더 → 시드 상태로 복원. `RESET_TOKEN`이 비어 있으면 엔드포인트 자체가 비활성(503)이라 실수로 초기화될 수 없다.

## 1.6 실제 배포 결과 (08/17 완료) — 이 표가 현재 상태다

| 서비스 | Railway 이름 | 공개 주소 | Root Directory |
|---|---|---|---|
| 백엔드 (FastAPI) | `DELPHi_Backend` | `https://delphiskhackathon-production.up.railway.app` | `/backend` |
| Console (Next.js) | `DELPHi_Console` | `https://delphi-console-production.up.railway.app` | `/apps/console` |
| Field (Next.js) | `DELPHi_Field` | `https://delphi-field-production.up.railway.app` | `/apps/field` |

프로젝트: `glistening-fascination` / 환경: `production` / 볼륨: `delphi_sk_hackathon-volume` → `/data` (백엔드에만)

**검증 완료(08/17)**: 헬스 200 · Console·Field 로드 · CORS 두 주소만 허용(그 외 차단) · 화면에서 승인 클릭 → KPI 즉시 반영.

**디자인 초안도 같은 주소에서 본다 (08/20 추가)**: `https://delphi-console-production.up.railway.app/draft.html`
— 8탭 목업(`demo/design-draft.html`)을 `apps/console/public/draft.html`로 **복사해** 정적 서빙한다. 실 Console 앱과 코드가 섞이지 않고, 팀원이 링크 하나로 폰에서도 열어볼 수 있다. 두 파일은 바이트 동일해야 하며, 목업을 고치면 같은 커밋에서 다시 복사한다:

```bash
cp demo/design-draft.html apps/console/public/draft.html   # 목업 수정 시 반드시 함께
```

> 목업을 `demo/`에만 두면 Railway 어느 서비스의 root directory에도 들어가지 않아 배포되지 않는다(서비스 root는 `apps/console`·`apps/field`·`backend` 세 곳뿐). 초안은 합성 데이터·가짜 로그인이므로 루트(`/`)가 아닌 `/draft.html`에만 둔다 — 심사위원의 첫 화면은 언제나 실제 Console이다.

### 배포하며 실제로 막힌 지점 5개 (같은 데서 또 막히지 말 것)

| 증상 | 원인·해결 |
|---|---|
| 빌드 실패 "could not determine how to build" | Root Directory 미설정. **`/backend` 처럼 슬래시를 붙여야** 인식됐다 |
| "No start command detected" | Railway가 `railway.json`·Dockerfile을 무시하고 railpack으로 빌드. **Settings → Deploy → Start Command**에 `uvicorn app.main:app --host 0.0.0.0 --port $PORT` 직접 입력 |
| "Application failed to respond" | 도메인이 바라보는 포트 불일치. Railway가 주는 `$PORT`는 **8080** — Generate Domain 시 8080을 넣는다. 실제 값은 Deploy Logs의 `Uvicorn running on 0.0.0.0:XXXX`로 확인 |
| 프론트 빌드 실패 (EBADENGINE / EBUSY) | Nixpacks가 Node 18 선택 → `package.json`에 `engines.node >= 20` 명시. `buildCommand`의 중복 `npm ci` 제거(설치는 Nixpacks가 이미 함) |
| **Chrome에서만 흰 화면** (사파리·curl은 정상) | Next 자체 gzip이 Railway 엣지와 겹쳐 chunked 종료 청크가 유실 → `net::ERR_INVALID_CHUNKED_ENCODING`. **`next.config.ts`에 `compress: false`**. 심사위원 대다수가 Chrome이라 데모 치명 버그였다 |
| push해도 배포가 안 됨 (몇 시간째 옛 커밋) | **Settings → Source의 레포 연결이 끊어져 있었음** (레포 이름 변경 시점과 겹침). Disconnect→Connect로 재연결. 증상: Deployments에 새 항목이 아예 안 생김(실패도 아님) |
| 재연결 직후 크래시 루프: `'$PORT' is not a valid integer` | 재연결로 Dockerfile 빌드가 살아나자, 예전 railpack 시절 넣어둔 **대시보드 Start Command가 셸 없이 실행되며 `$PORT`가 안 풀림**. Dockerfile을 쓸 때는 **Custom Start Command를 비워둔다** (CMD가 이미 처리) |

> 교훈: **브라우저를 하나만 보고 "된다"고 판단하지 말 것.** 사파리에서 멀쩡한 화면이 Chrome에서는 백지였다.

## 1.7 사내망(SK 오피스)에서 railway.com 자체가 안 열릴 때 (08/19 원인 확정)

**증상**: 크롬에서 railway.com(대시보드·로그인 확인 페이지 전부)이 백지 + `net::ERR_INVALID_CHUNKED_ENCODING`. **배포된 우리 앱 3개와는 무관** — 그쪽은 `compress: false`로 이미 해결됐고 사내 크롬에서도 정상.

**원인**: 사내 보안장비(Palo Alto SSL Forward Proxy — 인증서 발급자가 `Forward Trust CA`로 바뀌어 있음)가 TLS를 복호화·재암호화하면서 railway.com의 chunked 응답을 깨뜨린다. GlobalProtect VPN이 모든 트래픽을 터널(utun)로 회사에 되돌려 보내므로 **휴대폰 테더링으로도 우회 불가** — 검사가 망이 아니라 노트북을 따라다닌다. Render·Fly·Vercel도 같은 장비를 통과함을 확인(08/19) → **플랫폼 이사는 해결책이 아님**.

**우회 3단** (위에서부터 시도):
1. **사파리** — 깨진 응답에 관대해서 대부분 열린다 (느릴 수 있음).
2. **휴대폰 브라우저** — VPN이 없는 유일하게 깨끗한 경로. CLI 로그인 승인 페이지는 이걸로 여는 게 확실.
3. **IT 티켓(근본 해결)** — `railway.com, *.railway.com, *.up.railway.app` SSL 복호화 예외 요청.

**일상 운용은 CLI로 한다** (대시보드 접속 자체가 거의 불필요해짐 — CLI↔Railway API 통신은 검사망 아래서도 정상):

```bash
brew install railway
railway login --browserless   # 터미널에 링크+코드 → 휴대폰/사파리에서 코드 승인 (1회)
railway link --project glistening-fascination --environment production   # 레포 루트에서 1회
railway status                              # 3서비스 상태·URL 한눈에
railway logs --service DELPHi_Backend      # 배포 로그 (DELPHi_Console·DELPHi_Field 동일)
railway variables --service DELPHi_Backend # 환경변수 확인/설정
railway redeploy --service DELPHi_Backend  # 강제 재배포
```

**대시보드가 꼭 필요한 일만 사파리/휴대폰으로**: 플랜 전환·결제, 볼륨/도메인 생성, 이전 배포로 롤백 클릭, Watch Paths 설정.

## 2. 구성

```
GitHub 모노레포 (private, 합성 데이터만)
  main push ──▶ Railway 프로젝트 (싱가포르 리전) — 자동 빌드·배포 ≈3분
                 ├─ console  (Next.js)  delphi-console.up.railway.app ─┐
                 ├─ field    (Next.js)  delphi-field.up.railway.app  ─┼─▶ 심사위원·팀 브라우저
                 └─ backend  (FastAPI)  delphi-api.up.railway.app     │   (URL 두 개만 전달)
                      └─ 볼륨 /data: delphi.db + cache/  ◀── 이게 Vercel에 없는 것
                      └─ 외부: Claude API · PubMed·CT.gov·openFDA (캐시 우선, DEMO_OFFLINE=1이면 캐시만)
```

- 서비스별 root directory: `apps/console` / `apps/field` / `backend`. 프론트는 `NEXT_PUBLIC_API_BASE_URL`로 backend 공개 URL을 보고, backend CORS는 두 프론트 도메인을 허용.
- 환경변수는 Railway 대시보드에서만 관리 — `.env`·API 키 커밋 금지 규칙(docs/06 §5) 그대로.

| 서비스 | 환경변수 | 값 |
|---|---|---|
| backend | `DATABASE_URL` | `sqlite:////data/delphi.db` (슬래시 4개 = 절대경로) |
| | `DELPHI_CACHE_DIR` | `/data/cache` |
| | `ALLOWED_ORIGINS` | console·field 공개 URL 두 개, 쉼표 구분 |
| | `RESET_TOKEN` | 임의 문자열 (리셋 API 보호) |
| | `ANTHROPIC_API_KEY` | 추출·Screen·Board 구현 이후 필요 |
| | `DEMO_OFFLINE` | 시연 시 `1` (외부 API 캐시 강제) |
| console·field | `NEXT_PUBLIC_API_BASE_URL` | `https://<backend>.up.railway.app/api` |

> `NEXT_PUBLIC_*`는 **빌드 시점에 번들에 박힌다.** 값을 바꾸면 반드시 재배포해야 반영된다.

- 볼륨은 backend 서비스에 `/data`로 마운트한다 (SQLite + 외부 API 캐시가 재배포 사이에 살아남는 자리).

## 3. 일정 (담당: 인혁, 건태 보조 — docs/00 표에 반영됨)

| 날짜 | 할 일 | 완료 기준 |
|---|---|---|
| 8/14–16 | 레포 생성 시 모노레포 구조·`.gitignore`(.env·*.db·cache) 확인 + Railway 가입(GitHub 로그인) | ✅ 8/14 완료 |
| **8/15** | **배포 설정 선행 커밋** (§1.5) — Dockerfile·railway.json·자동 시드·리셋 API | ✅ 완료 |
| **8/15–16** | **첫 배포**: 워킹 스켈레톤을 3서비스로 올림 + 볼륨·환경변수·CORS (원래 8/24 예정이었으나 스켈레톤 단계에서 앞당김 — 배포까지 관통해야 진짜 스켈레톤이고, 빈 껍데기일 때 붙이는 게 가장 싸다) | 폰에서 Field URL이 열리고 Console에 문서 목록이 뜬다 |
| 8/26 | 외부 API 스냅샷 → `backend/data/fixtures/` 커밋 → 시드가 볼륨 cache/로 복사 | 배포본에서 `DEMO_OFFLINE=1` 동작 |
| 9/1 | 심사용 마감 점검: `RESET_TOKEN` 보호 리셋 엔드포인트(reset_demo.sh의 서버판) · 프론트 `noindex` 메타 · 유료 플랜 전환 | `GET /health`로 육안 확인 |
| **9/3** | 리허설 #2 통과본에 `demo-final` 태그 → 리셋 실행 → **심사 URL 공유**. 이후 push는 핫픽스만 | 새 시크릿 창에서 시나리오 완주 |

## 4. 브랜치·배포 운용 (docs/06 §1의 main 단일 유지)

- **8/24–9/2**: push = 팀 스테이징. 부담 없이 자주 올린다. 부수 이득: 소정이 실물 폰으로 Field를 매일 테스트.
- **9/3–9/4**: push = 심사위원 화면. 로컬에서 시나리오 한 바퀴 돈 커밋만 push.
- **9/1부터 배포 게이트 (08/18 결정)**: 팀원은 `dev` 브랜치에 push — Railway는 `main`만 감시하므로 배포되지 않는다 → 건태가 로컬 확인 → `main` 병합 시 배포. **Railway 설정은 그대로**, 올리는 곳만 바뀐다. 그 전(8/21~31)에는 main 직push 유지 — 속도 우선, 사고 시 롤백 1분.
- 안전장치 2개 (브랜치를 늘리지 않는 이유): ① 체크포인트마다 마일스톤 태그(`w1-exit`, `cp2-pass`, `demo-final`) — 되는 상태의 북마크. ② 배포 사고 시 Railway 대시보드에서 직전 배포로 **롤백(클릭 2번)**.

## 5. 심사용 운영 원칙

- **언제 들어와도 데모 시작 상태**: 여러 심사위원이 눌러보면 승인 상태가 섞이므로, 리셋 엔드포인트로 매일 아침(가능하면 자정 자동) 시드 상태 복원.
- **noindex**: 두 프론트에 `<meta name="robots" content="noindex">` — 합성 데이터지만 검색 노출은 차단.
- **비용**: Hobby $5/월 + 소형 3서비스 사용량 ≈ 해커톤 전체 1~2만 원. 무료 크레딧으로 시작하되 **9/1 전 유료 전환** (무료 상태 콜드스타트로 심사위원 첫 화면이 30초 걸리는 사고 방지). 본선 후 즉시 해지 가능.
- 실데이터·실명 반입 금지는 배포본에도 동일 (docs/06 §5) — 레포·볼륨 어디에도 합성 데이터만.

## 6. 맥스튜디오 판정 (08/14)

- 개발서버 ✕ — SQLite 파일 DB 구조라 각자 로컬 풀스택이 설계 의도(중앙 dev 서버는 서로 데이터를 밟는다), LLM은 Claude API라 로컬 연산 불필요.
- 심사 호스팅 ✕ — 가정용 네트워크·전원이 심사 기간의 단일 장애점.
- 발표장 백업 머신 ○ — 로컬 스택 + DB 스냅샷 + 리허설 녹화 영상을 넣어 9/4 "장비·환경 백업 대기"(인혁)로 활용.
