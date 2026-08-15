@AGENTS.md

---

# DELPHi Field 앱 규칙 [오너: 소정]

- 포트 3001 (`npm run dev`) · **페이퍼 라이트 고정** · 모바일 우선 390px — 토큰은 `app/globals.css`, 상세는 루트 `docs/05_DESIGN_SYSTEM.md`.
- 백엔드 호출은 `lib/api.ts` 경유, 기본 롤 MEDICAL_AFFAIRS. 계약은 `docs/04_API_SPEC.md`.
- **입력 폼 하드코딩 금지** — 반드시 `GET /field/form-config` 기반 렌더 (v0.2 전환 데모가 여기서 터진다, docs/01 §5).
- 음성은 Web Speech API ko-KR (P1) + 전사 스크립트 재생 폴백. AE 분기·마스킹은 서버 파이프라인과 함께 8/25~.
- 루트 CLAUDE.md 절대 규칙 8개 준수. 지금 상태는 스캐폴딩 셸 — stub을 교체하며 채운다 (`docs/06 §2.5`).
