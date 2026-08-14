# 05. 디자인 시스템 — "Paper & Glass"

> **공식 브랜드 HEX (팀장 확정, 2026-08-12): 네이비 `#162661` + 오렌지 `#EF8B1C`.** 이 두 색만 쓰지 말고 아래 확장 팔레트로 유연하게.
> 룩: **밝은 페이퍼 배경 + 컬러 블롭 위에 뜨는 글래스(유리) 카드**. 좌측 색선 붙은 박스(스트림릿st), 범용 다크+네온 룩 금지.
> 실물 기준: **`Demo_Mockup.html`**(레포 루트, 발표 덱 v10 = 기획서 참고자료 1~3의 원본)이 이 시스템의 시제품이다. 화면 만들기 전에 꼭 열어볼 것.
> `demo/Demo_Mockup.html`은 8/12 스냅샷이다 — **루트 파일이 최신본**이며, 수정은 루트에서만 한다.

## 1. 브랜드 무드

- 키워드: **oracle(신탁), evidence(근거), spark(신호)**. 네이비 = 신뢰·기록, 오렌지 = 발견된 신호의 스파크.
- 로고 파일: 원본 `logo.png`(네이비, 라이트 배경용) / `demo/logo-white.png`(다크 요소 위 사용, 오렌지 점 유지). 로고 마크를 스피너처럼 도는 애니메이션으로 쓰지 말 것 (로딩 아이콘으로 오독됨 — 팀장 피드백).
- **두 앱 모두 페이퍼 라이트** (2026-08-12 팀장 확정 — 다크 대시보드 금지). 콘솔의 실물 기준은 `Demo_Mockup.html`의 콘솔 패널: 밝은 크림 배경 + 흰 카드(보더 없음, 소프트 섀도) + 초대형 숫자(단위는 연회색) + 필(pill) 배지 + 그라데이션 인사이트 카드. (v4에 있던 산키형 Signal Flow 차트는 08/12 제거됨 — 아래 차트 규칙 참조)
- **아이콘은 직접 그리지 않는다** — [Lucide](https://lucide.dev) (ISC 라이선스, shadcn 기본) 사용. 앱에선 `lucide-react`, 정적 HTML에선 SVG 인라인. 톤: stroke 1.8, 그라데이션 칩(15px radius) 안에 흰색.
- 차트는 에셋 불필요 — 전부 SVG로 직접 제작. **차트 형태는 의미가 정한다**: 소스가 하나뿐인 데이터에 산키 금지(팀장 반려 사례). 데이터 흐름 차트를 그릴 땐 기획안의 상태 머신을 그대로 노드로(원문→CANDIDATE→APPROVED→가설), 처리(추출/검토/집계)는 연결선 라벨로. **화면 속 숫자는 서로 검산되어야 한다**(예: 후보 147 = 승인 134 + AE 5 + 반려 8, 수용률 91% ↔ KPI 90%+).
- **설명이 계속 필요한 비주얼은 제거한다**: 같은 비주얼이 두 번 의심받으면(→ 덱 S7 흐름 차트, 08/12 제거) 다듬지 말고 뺀다. 그 메시지를 이미 전달하는 다른 표면(루프 다이어그램·원칙 슬라이드·라이브 데모)이 있는지 먼저 확인.
- 주관적으로 들리는 카피 금지: "필요한 부분만" → **"위험 기반 검토"** 등 기준이 보이는 표현으로 (docs/02 §5.5).
- 지표의 증감 표시는 텍스트 화살표(↑↓) 대신 **굵은 SVG 화살표**(stroke 3.5±, 라운드 캡) + %와 간격 분리.

## 2. 컬러 토큰 (shadcn CSS 변수로 등록)

| 토큰 | 값 | 용도 |
|---|---|---|
| `--navy` | `#162661` (공식) / deep `#0E1B4D` / 70% `#3A4A85` / 45% `#7A87B4` | 잉크·헤딩·주요 버튼. 텍스트는 농도 단계로 위계 |
| `--orange` | `#EF8B1C` (공식) / deep `#D9760B` / amber `#FFB25C` / cream `#FFF3E3` | **유일한 강조**: 핵심 숫자·CTA·하이라이트 단어. 화면당 한 곳만 크게 |
| `--sky` | `#5B7CFA` / peri `#93A7FF` / ice `#EAF0FF` | 네이비의 밝은 확장 — 데이터·차트·SQL 배지 |
| 페이퍼 배경 | `#F4F6FC` + 앰비언트 블롭(orange/sky/navy 반투명 + blur 90px) | 글래스가 비칠 배경. 순백 단색 금지 |
| 글래스 카드 | `rgba(255,255,255,.5~.78)` 그라데이션 + `backdrop-filter: blur(20px) saturate(1.5)` + 흰 1px 보더 + `0 24px 60px -24px rgba(22,38,97,.22)` 그림자, radius 22px | 기본 카드. 좌측 색선·플랫 보더 박스 금지 |
| 아이콘 칩 | 44px 라운드 15px, 그라데이션(navy→`#2E4390`, orange→amber, sky→peri, green→`#4ADCA4`) + 컬러 그림자 | 카드 아이덴티티는 선이 아니라 칩으로 |
| 시맨틱: support `#1FA97C`(↑) · counter `#E4536B`(↓) · gap `#8A94B8`(◌·점선) · safety `#E4536B`+전용배지 | | gap에 amber 금지(브랜드 충돌) |

**5단계 구분 규약 (전 화면 통일, 컬러 도트+라벨로 표기 — 좌측 보더 금지):**
관찰된 사실 `#94A3C4` · 통계적 패턴 `#5B7CFA(SQL)` · AI의 해석 `#9F7FE8(AI 전용)` · 전략적 제안 `#EF8B1C` · 승인된 실행 `#1FA97C`.
→ 심사위원이 색만 보고도 "어디까지가 사실이고 어디부터 AI인지" 읽게 만드는 게 목적.

**타이포 최소 크기**: 슬라이드·히어로 제목 clamp(30~48px), 리드 16~18px, 본문 14.5px 미만 금지(제품 목업 내부 제외) — "글자가 너무 작다" 재발 방지.

## 3. 타이포그래피

- 한글: **Pretendard Variable** (CDN: jsDelivr) / 영문 디스플레이: **Avenir Next → Century Gothic 폴백** (로고의 지오메트릭 산세리프와 결) / 수치·코드·ID: **Geist Mono 또는 ui-monospace**.
- 대시보드 숫자는 반드시 `font-variant-numeric: tabular-nums` (카운트업 시 흔들림 방지).
- 스케일: 12(캡션)/13(보조)/14(본문)/16(강조)/20(카드 제목)/28(섹션)/40+(히어로·KPI).

## 4. 모션 규칙 (framer-motion 표준)

| 종류 | 시간·이징 | 예 |
|---|---|---|
| 마이크로 (hover, 토글) | 150ms, `easeOut` | 버튼, 배지 |
| 요소 등장 | 400ms, `cubic-bezier(0.16,1,0.3,1)` + `y: 12→0` + stagger 60ms | 카드 리스트 |
| 레이아웃 전환 | `layout` 프로퍼티 (spring: stiffness 260, damping 26) | 카드 확장, 탭 |
| 수치 | 카운트업 800ms (Magic UI NumberTicker) | KPI |
| AI 작동 | animated beam / 펄스 + 스트리밍 텍스트 | Screen 에이전트, Board 발언 |
| 승인 순간 | 체크 아이콘 스프링 팝 1회 (반복 금지) | claim·가설 승인 |

**금지**: 무한 반복 장식 애니메이션(히어로 배경 제외), 300ms 넘는 hover, 3개 초과 동시 stagger 그룹, `prefers-reduced-motion` 무시.
**연출 포인트 3곳** (여기에 공들이자): ① Field에서 AE 문장이 빨간 배지로 "분리되는" 순간 ② Screen 에이전트 4개가 순차 조사하는 beam ③ SCP 승인 → Field 폼에 새 항목이 나타나는 순간.

## 5. 컴포넌트 소스 — 어디서 뭘 가져올지

| 사이트 | 용도 | 이렇게 쓴다 |
|---|---|---|
| [ui.shadcn.com](https://ui.shadcn.com) + [/create](https://ui.shadcn.com/create) | 베이스 컴포넌트·프로젝트 스캐폴딩 | 두 앱 모두 여기서 시작. create에서 테마 잡고 CLI 명령 복사 → Claude에게 전달 |
| [tweakcn.com](https://tweakcn.com) | shadcn 테마 시각 편집기 | §2 토큰을 여기서 튜닝 → CSS 변수 export |
| [magicui.design](https://magicui.design) | **AnimatedBeam**(에이전트 시각화 핵심!), NumberTicker, ShimmerButton, BorderBeam | 필요한 것만 copy-paste |
| [ui.aceternity.com](https://ui.aceternity.com) | 히어로·스포트라이트·배경 효과 | 데모 페이지·발표 첫 화면용. 앱 내부엔 과함 |
| [motion-primitives.com](https://motion-primitives.com) | 텍스트 등장, TextShimmer(AI 생각 중), 트랜지션 프리미티브 | Board 발언 스트리밍 연출 |
| [reactbits.dev](https://reactbits.dev) | 마이크로 인터랙션 조각 | 승인 버튼 등 포인트 |
| [originui.com](https://originui.com) | 폼·입력 컴포넌트 대량 | Field 동적 폼 |
| [ui.shadcn.com/charts](https://ui.shadcn.com/charts) (Recharts) | 대시보드 차트 | §2 팔레트 강제 적용 |
| [21st.dev](https://21st.dev) | 커뮤니티 shadcn 컴포넌트 탐색 | "이런 거 없나?" 할 때 검색 |
| [mobbin.com](https://mobbin.com) | 실제 제품 스크린 리서치 | Field UX 참고 (모바일 승인 플로우) |
| 제품 감각 레퍼런스 | [linear.app](https://linear.app) (다크 절제) · [attio.com](https://attio.com) (AI-native 표면) · [stripe.com](https://stripe.com/dashboard) (데이터 테이블) · [vercel.com](https://vercel.com) (여백·타이포) | 스타일 방향 판단 기준 |
| [frontend-slides](https://github.com/zarazhangrui/frontend-slides) (GitHub 27k★) | 단일 HTML 발표 덱 스킬 — 우리 `Demo_Mockup.html`과 같은 계열 | 발표자료 추가 제작 시 참고 |

**Claude Code 활용 팁**: 컴포넌트를 통째로 설명하지 말고, 위 사이트의 컴포넌트 페이지 URL을 프롬프트에 붙여넣고 "이거 우리 토큰(§2)으로 이식해줘"라고 시키는 게 가장 빠르다.

## 6. 레이아웃 규칙

- Console: 좌측 아이콘 사이드바(56px) + 콘텐츠 max-w 1280 중앙. 카드 radius 12px, 얇은 1px 경계 + 미세 그림자.
- Field: 세로 1열, 하단 고정 CTA, 터치 타깃 최소 44px, safe-area 패딩. 폰 프레임 안에서 데모하므로 390px 기준 설계.
- 밀도: 대시보드는 "한 화면에 질문 하나". 첫 화면은 '모든 게 괜찮은가' → 클릭해서 파고들기 (progressive disclosure).
- 로딩: 스켈레톤 shimmer 통일 (스피너 금지). AI 대기: TextShimmer("근거 조사 중…").

## 7. 기획서 참고자료와 실제 화면의 대응 (최종 기획안 "기타. 참고자료")

기획서에 제출한 목업 3종이 곧 심사위원의 기대치다. **구현 화면이 이보다 단순해지는 것은 허용, 다른 물건이 되는 것은 금지.**

| 기획서 참고자료 | 원본 | 구현 대상 |
|---|---|---|
| 1. DELPHi Field Mock-up | `Demo_Mockup.html` Field 패널 / `docs/assets/field.png` | `apps/field` — 동의→전사→AE 분기→카드 승인 |
| 2. DELPHi Console Main Page | `Demo_Mockup.html` 콘솔 패널 / `docs/assets/console.png` | `apps/console` — 홈 KPI + 가설 카드 + Board |
| 3. DELPHi Solution 작동 구조 | `docs/assets/loop.png`(루프) · `rules.png`(원칙) | 발표 덱 + `/hypotheses/[id]`의 5단계 구분 표기 |

기획서에 **"세부 내용은 변경될 수 있음"**을 명시해 두었으므로 디테일 변경은 자유다. 단 ① 5단계 구분 표기 ② 원문 하이라이트 대조 ③ v0.2 폼 변경 장면은 목업의 약속이므로 형태를 유지한다.

## 8. 접근성·품질 체크 (화면 완성 정의)

- [ ] 텍스트 대비 4.5:1 이상 (페이퍼 배경 위 본문은 navy 70%(`#3A4A85`) 이상 농도 — 45% 톤은 캡션 전용)
- [ ] 색 + 아이콘/라벨 병행 (색맹 대비 — support/counter는 ↑↓ 아이콘 병기)
- [ ] `prefers-reduced-motion` 시 등장 애니메이션 생략
- [ ] 데모 노트북(1440px)과 실제 폰(iPhone)에서 확인
