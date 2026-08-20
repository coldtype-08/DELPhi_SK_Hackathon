# STT 후보 평가용 녹음 대본 (합성)

> **[합성 샘플]** 인물·기관·발언·번호는 모두 실재하지 않습니다. 실제 의료진 면담 기록에서 가져오거나
> 변형한 내용은 한 건도 없습니다 (`docs/06` §5).

Field 앱 STT 서비스 후보를 비교하기 위한 **녹음 대본 = 채점 정답지**입니다.
선택 기준과 후보 목록은 `docs/01` §8.5, 결정 기록은 `docs/DECISIONS.md` 08/20.

## 녹음 방법

- **반드시 2명이 번갈아 읽는다.** 혼자 읽으면 화자 분리 검증이 무의미하다 (MSL 역 / HCP 역).
- 휴대폰 녹음으로 충분하다. 평소 말하는 속도로 읽고, 또박또박 읽지 않는다 —
  과장된 발음은 실제보다 점수를 높게 만든다.
- **TTS 합성음을 쓰지 않는다.** 발음이 규격화돼 있어 "17세 → 70세" 같은 실제 오인식이 재현되지 않고,
  한·영 혼용의 핵심 난이도(한국식 영어 발음 전환)도 재현되지 않는다.
- 대본 A는 영어만 케이스(`deepgram`), 대본 B는 한국어+영어 혼용 케이스(`soniox`·`gladia`) 평가용이다.
- **배선·동작 확인용 합성 음성**은 `gen_test_audio.py`로 만들 수 있다(espeak-ng, 무료·오프라인).
  단 그것은 판정 재료가 아니다 — 위 이유 그대로다.

## 채점 방법

1. **핵심 토큰 정확도** (아래 표) — 전체 WER보다 이것이 우선이다.
   "하하"를 놓치는 것은 무해하지만 "17세"를 놓치면 대표 가설 HYP-001의 근거가 사라진다.
   전사 텍스트가 `interactions.raw_text`가 되고 모든 evidence 오프셋의 기준이므로(`docs/02` §1) 되돌릴 수 없다.
2. **화자 라벨 존재 여부** — `speaker 0` / `speaker 1` 수준으로 충분. MSL/HCP 매핑은 수집 화면 책임.
3. 전체 WER — 참고 지표.

---

## 대본 A — 영어만 (English only)

**MSL:** Good morning, Doctor. Thanks for making time. Did you get the materials I sent last week?

**HCP:** I did, thank you. The clinic has been busy — a lot of referrals lately.

**MSL:** I heard you have been seeing more adolescent cases with drug-resistant focal seizures.

**HCP:** That is right. I have a seventeen-year-old who has failed two anti-seizure medications. But cenobamate is approved for adults, so there is nothing I can do until they turn eighteen.

**MSL:** So that gap keeps coming up. I will log it as stated.

**HCP:** Also, one adult patient reported dizziness and somnolence after starting XCOPRI.

**MSL:** I will route that through the safety review pathway. The relevant team will follow up.

**HCP:** Please do. And if any adolescent dosing or safety data becomes available, I would appreciate a copy.

**MSL:** Understood. Should I coordinate the next visit through your office?

**HCP:** Yes, call the clinic at five five five, one two three, four five six seven.

**MSL:** Thank you, Doctor.

---

## 대본 B — 한국어 + 영어 혼용 (Korean base, English terms mid-sentence)

**MSL:** 선생님, 안녕하세요. 지난번에 보내드린 자료는 잘 받으셨죠?

**HCP:** 네, 잘 봤어요. 요즘 외래가 많아서 정신이 없네요.

**MSL:** 난치성 초점발작 청소년 케이스가 늘었다고 들었습니다.

**HCP:** 맞아요. 2제 실패한 17세 환자가 있는데, 엑스코프리는 성인 허가라 지금은 손을 쓸 수가 없어요. 18세까지 기다리는 것 말고는 방법이 없네요.

**MSL:** 그런 케이스가 반복되는군요. 기록해 두겠습니다.

**HCP:** 그리고 고령 환자분들은 lamotrigine 같은 병용약이 많아서 DDI부터 걱정하시더라고요. titration 스케줄도 부담스럽다고 하시고요.

**MSL:** 병용약 상호작용 확인 부담이 크시군요.

**HCP:** 네. 아, 성인 환자 한 분은 세노바메이트 복용 시작하고 어지러움하고 졸림이 꽤 있다고 하셨어요.

**MSL:** 그 부분은 안전성 검토 경로로 전달하겠습니다.

**HCP:** 그렇게 해주세요. 다음 방문은 김도현 선생님 통해서 잡아주시고, 제 번호 010-4132-7789로 연락 주세요.

**MSL:** 네, 감사합니다 선생님.

---

## 채점 대상 핵심 토큰

| 분류 | 대본 A (EN) | 대본 B (KO+EN) | 틀리면 무슨 일이 나는가 |
|---|---|---|---|
| **연령 (치명적)** | `seventeen-year-old`, `eighteen` | `17세`, `18세` | S1 신호 소멸 → HYP-001 근거 붕괴 |
| **실패 약물 수** | `two` (anti-seizure medications) | `2제` | `DRE_2PLUS` 판정 실패 |
| **제품명** | `cenobamate`, `XCOPRI` | `엑스코프리`, `세노바메이트` | 제품 실명 언급 여부(`product_named`) 판정 실패 |
| **병용 약물** | — | `lamotrigine` | `concomitant_drugs` 누락 |
| **영어 전문용어 (혼용 난이도)** | — | `DDI`, `titration` | 코드스위칭 실패 시 vocab 매핑 실패 → 검토등급 하락 |
| **도메인 용어** | `drug-resistant focal seizures` | `난치성 초점발작`, `병용약`, `상호작용` | canonical 정규화 실패 |
| **AE 용어** | `dizziness`, `somnolence` | `어지러움`, `졸림` | S2 안전성 분기 실패 |
| **오프라벨 신호** | `approved for adults`, `until they turn eighteen` | `성인 허가`, `18세까지 기다` | `label_scope=OUT_OF_LABEL` 판정 근거 소실 |
| **PII (마스킹 테스트)** | `555 123 4567` | `010-4132-7789`, `김도현` | `masked_spans` 정규식이 걸리지 않음 |

## 참고 — 코퍼스와의 관계

기존 코퍼스의 한국어 음성 전사 3건(`DOC-20260721-061` ~ `063`)에는 **영어 단어가 하나도 없다.**
`docs/03` §3 규칙 2가 요구하는 영한 혼용(`titration`, XCOPRI/엑스코프리/세노바메이트 혼용)이 미반영 상태다.
대본 B는 그 요구를 반영해 새로 쓴 것이며, **코퍼스를 수정한 것이 아니다** — 코퍼스 변경은 도메인 오너 판단 사항.
