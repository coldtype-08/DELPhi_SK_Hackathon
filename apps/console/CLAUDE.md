@AGENTS.md

---

# DELPHi Console 앱 규칙 [오너: 건태]

- 포트 3000 · **페이퍼 라이트 고정(다크 금지)** — 토큰은 `app/globals.css`, 상세 규칙은 루트 `docs/05_DESIGN_SYSTEM.md`.
- 백엔드 호출은 반드시 `lib/api.ts` 경유 (X-Delphi-Role 헤더 포함). 응답 모양의 계약은 `docs/04_API_SPEC.md` — 다르면 스펙부터 고친다.
- 아이콘은 lucide-react, 컴포넌트는 shadcn/ui (`npx shadcn@latest add ...`). 직접 그리지 말 것.
- 루트 CLAUDE.md의 절대 규칙 8개 준수 — 특히 화면의 판단 정보 5단계 구분 표시(#8), 수치는 서버 SQL 값만 표시(#1).
- 이 앱의 화면 맵: `docs/01 §5`. 지금 상태는 스캐폴딩 셸 — stub을 교체하며 채운다 (`docs/06 §2.5`).
