# DELPHi STT Lab — 실시간 STT 3종 비교

Soniox · Gladia · Deepgram을 **같은 음성·같은 조건**으로 나란히 돌려보고, 어느 것을 Field 앱에 쓸지 정하기 위한 로컬 전용 도구입니다.

- 배포하지 않습니다 (`railway.json` 없음)
- API 키는 화면에서 입력하고 **브라우저에만** 저장됩니다 (커밋·서버 전송 없음)
- 결과가 3탭에 각각 남으므로 비교가 됩니다

## 1. 준비 — API 키 3개

| 서비스 | 발급 |
|---|---|
| Soniox | https://console.soniox.com/ |
| Gladia | https://docs.gladia.io/chapters/introduction/getting-started |
| Deepgram | https://console.deepgram.com/ |

세 개를 다 받지 않아도 됩니다. 받은 것만 해당 탭에서 테스트하면 됩니다.

## 2. 테스트 음성 만들기

```bash
# mac
brew install espeak-ng
# linux
sudo apt-get install -y espeak-ng

python3 scripts/stt_eval/gen_test_audio.py
# → scripts/stt_eval/audio/stt_test_A_english.wav      (영어만, 67초)
# → scripts/stt_eval/audio/stt_test_B_ko_en_mixed.wav  (한국어+영어, 85초)
```

합성음은 배선 확인용입니다. **판정은 사람이 `scripts/stt_eval/TEST_SCRIPTS.md`의 대본을 2인이 읽어 녹음한 파일로** 하세요 (녹음 지침이 그 문서에 있습니다).

## 3. 실행

```bash
cd apps/stt-lab
npm install
npm run dev        # http://localhost:3002
```

백엔드가 필요하지 않습니다. 브라우저가 벤더에 직접 붙습니다.

## 4. 쓰는 순서

1. **공통 조건**에서 정합니다
   - 채점 대본: `A`(영어) 또는 `B`(한국어+영어) — 재생할 WAV와 맞춥니다
   - 언어 설정 / 화자 분리 / 부스팅 on-off
   - **WAV 파일**을 고릅니다 (3탭에 같은 파일을 흘려야 공정한 비교)
2. 탭을 고르고 **API 키**를 붙여넣습니다 (한 번 넣으면 브라우저에 저장됩니다)
3. **모델**을 고릅니다
   - Deepgram: 영어면 `nova-3-medical`(의료 특화), 한국어면 `nova-3`
4. **파일로 시작** 또는 **마이크로 시작**
5. 다른 탭으로 옮겨 같은 조건으로 실행 → 결과 비교

## 5. 화면이 보여주는 것

| 영역 | 내용 |
|---|---|
| 전사 | 화자 라벨(`0`/`1`) + 확정(진한 글씨)·잠정(흐린 이탤릭) 구분 |
| 첫 응답 / 최종 | 시작부터 첫 글자까지 ms, 마지막 확정까지 ms |
| 핵심 토큰 채점 | `TEST_SCRIPTS.md`의 토큰 히트(초록)·미스(빨강). ★는 틀리면 데모가 깨지는 항목 |
| 원시 응답 | 벤더가 보낸 JSON 그대로 — 오류 메시지 확인용 |

**전체 정확도보다 핵심 토큰이 우선입니다.** "하하"를 놓치는 건 무해하지만 "17세"를 놓치면 대표 가설 HYP-001의 근거가 사라집니다.

## 6. 확인이 안 끝난 것 — 실행하면 답이 나옵니다

| 항목 | 어떻게 판정하나 |
|---|---|
| **Soniox WebSocket 경로·`audio_format`** | 공개 문서를 열지 못해 추정값입니다. 틀리면 "원시 응답"에 서버 오류가 뜨고, **엔드포인트 칸에서 바로 고칠 수 있습니다** |
| **Gladia 실시간 화자분리** | 정본 스펙(요청 OpenAPI·응답 asyncapi) 어디에도 없는데 산문·SDK에는 나옵니다. 화자 분리를 켜면 `diarization: true`를 일부러 보냅니다 → **422면 미지원 확정, 201이면 지원** |
| 부스팅 용어 한도 | Deepgram은 500 tokens(문서 확인). Soniox·Gladia는 미확인 — 40개를 실제로 넣어보면 압니다 |

## 7. 코드 구조

```
lib/stt/types.ts      공통 인터페이스 ....... 이식 대상
lib/stt/soniox.ts     provider ............. 이식 대상
lib/stt/gladia.ts     provider ............. 이식 대상
lib/stt/deepgram.ts   provider ............. 이식 대상
lib/stt/audio.ts      마이크·WAV → 16kHz PCM16 ... 이식 대상
lib/stt/scoring.ts    핵심 토큰 채점 ........ 이식 대상
app/page.tsx          3탭 비교 화면 ......... 버릴 코드
```

비교가 끝나면 **`lib/stt/`를 `apps/field/lib/stt/`로 복사하고 고른 provider 하나만 남기면** 됩니다. Field 앱과 같은 스택·같은 페이퍼 라이트 토큰으로 짜여 있습니다.

## 8. 막힐 때

| 증상 | 원인 |
|---|---|
| 마이크가 안 잡힘 | 브라우저 권한. `localhost`는 secure context라 별도 설정 불필요 |
| `연결 실패` / `시간 초과` | API 키 오타, 또는 사내망에서 WebSocket 차단 (`docs/07` §1.7의 SSL 검사 장비) |
| 전사가 비어 있음 | 언어 설정과 WAV 언어 불일치. `nova-3-medical`에 한국어를 넣으면 이렇게 됩니다 |
| 화자 라벨이 전부 `0` | 화자 분리 미지원 또는 꺼짐. "원시 응답"에서 speaker 필드 유무 확인 |
