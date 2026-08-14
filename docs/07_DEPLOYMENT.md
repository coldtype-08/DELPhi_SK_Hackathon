# 07. 배포 — 심사위원 상시 접속 (Railway)

> 08/14 확정 (DECISIONS 08/14). 배경: 주최측 요건이 "심사위원이 접속 가능해야 함"이고 기간이 불명확 → 가장 안전한 **상시 접속 기준**으로 설계. 당일 접속으로 확정돼도 이 구성 그대로 쓰고 URL 공유만 늦추면 된다.
> **원칙: 무대 위 라이브 발표의 정본은 여전히 로컬 + 캐시다** (docs/00 §0). 클라우드는 심사위원의 자유 접속용 별도 트랙이며, 배포가 죽어도 발표는 무사해야 한다.

## 1. 왜 Vercel이 아니라 Railway 하나인가

- 백엔드가 FastAPI + **SQLite 파일 DB**라서 서버리스(Vercel Functions)에서는 디스크가 사라져 DB가 살 수 없다. 백엔드에는 **영구 디스크(볼륨)가 붙는 상시 서버**가 필요하다.
- 그런 서버를 주는 Railway는 Next.js 두 개도 같이 돌린다 → 비개발자 3인 팀은 **플랫폼 하나만** 배우면 된다 (대시보드·환경변수·로그·도메인 관리 지점 1곳).
- 대안(프론트 Vercel + 백엔드 Railway 분리)은 관리 지점이 두 배라 기각.

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
  - backend: `ANTHROPIC_API_KEY` `ALLOWED_ORIGINS` `DEMO_OFFLINE` `RESET_TOKEN` `DATABASE_URL(볼륨 경로)`
  - console·field: `NEXT_PUBLIC_API_BASE_URL`

## 3. 일정 (담당: 인혁, 건태 보조 — docs/00 표에 반영됨)

| 날짜 | 할 일 | 완료 기준 |
|---|---|---|
| 8/14–16 | 레포 생성 시 모노레포 구조·`.gitignore`(.env·*.db·cache) 확인 + Railway 가입(GitHub 로그인) | — |
| **8/24** | **첫 배포**: 체크포인트 #1 통과 코드를 3서비스로 올림 + 볼륨·환경변수·CORS | 폰에서 Field URL이 열리고 Console에 문서 목록이 뜬다 |
| 8/26 | 외부 API 스냅샷 → `backend/data/fixtures/` 커밋 → 시드가 볼륨 cache/로 복사 | 배포본에서 `DEMO_OFFLINE=1` 동작 |
| 9/1 | 심사용 마감 점검: `RESET_TOKEN` 보호 리셋 엔드포인트(reset_demo.sh의 서버판) · 프론트 `noindex` 메타 · 유료 플랜 전환 | `GET /health`로 육안 확인 |
| **9/3** | 리허설 #2 통과본에 `demo-final` 태그 → 리셋 실행 → **심사 URL 공유**. 이후 push는 핫픽스만 | 새 시크릿 창에서 시나리오 완주 |

## 4. 브랜치·배포 운용 (docs/06 §1의 main 단일 유지)

- **8/24–9/2**: push = 팀 스테이징. 부담 없이 자주 올린다. 부수 이득: 소정이 실물 폰으로 Field를 매일 테스트.
- **9/3–9/4**: push = 심사위원 화면. 로컬에서 시나리오 한 바퀴 돈 커밋만 push.
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
