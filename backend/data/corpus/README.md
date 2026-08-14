# 합성 코퍼스 — 전부 가상 데이터입니다

> **이 폴더의 모든 문서는 실재하지 않습니다.** 인물·기관·발언·날짜 전부 스크립트가 만들어낸 허구이며,
> 실제 의료진 면담 기록이나 사내 문서에서 가져오거나 변형한 내용은 **한 건도 없습니다.**
> 문서 양식은 업계에서 흔한 현장 기록(field medical) 형식을 **흉내 낸 것**이고, 특정 조직의 실제 문서를 복제한 것이 아닙니다.
> 각 파일의 첫 줄에도 같은 고지가 들어 있습니다.

DELPHi 프로토타입(2026 SK AI 해커톤)의 데모·개발용 데이터셋입니다. 설계 근거는 [`docs/03_SYNTHETIC_DATA.md`](../../../docs/03_SYNTHETIC_DATA.md).

## 구성

| 유형 | 문서 | 인사이트 단위 | 언어 | 포장 |
|---|---|---|---|---|
| `HIGHLIGHT_DOC` 하이라이트 묶음 | 12 | 60 | EN | txt + docx |
| `CONGRESS_REPORT` 학회 참관 보고서 | 3 | 10 | EN | txt + pdf |
| `MEETING_NOTE` 면담 기록 | 25 | 25 | EN | txt (8건 docx) |
| `CALL_NOTE` 전화 메모 | 10 | 10 | EN | txt |
| `EMAIL_SUMMARY` 이메일 요약 | 10 | 10 | EN | txt |
| `VOICE_TRANSCRIPT` 음성 전사 | 3 | 3 | KO | txt |
| **합계** | **63** | **118** | | docx 20 · pdf 3 |

- **정본은 `.txt`** — 모든 evidence pointer(문자 위치)의 기준이다. docx/pdf는 같은 원문의 포장이며, 렌더 후 재추출해 정본과 일치하는지 검증한다.
- 1개 문서에 여러 HCP가 담기는 유형(`HIGHLIGHT_DOC`·`CONGRESS_REPORT`)은 추출이 **HCP 블록 단위로 interaction을 분리**한다.

## 파일

- `DOC-{YYYYMMDD}-{seq}.txt|docx|pdf` — 문서 원문과 포장본
- `manifest.jsonl` — 한 줄 = 한 인사이트 단위(interaction). Data Contract 필드 + 블록 범위 + 마스킹 위치
- `ground_truth.jsonl` — **채점용 정답지**. 심어둔 신호의 문장·문자 위치. 서비스 로직은 이 파일을 절대 읽지 않는다
- `REVIEW.html` — 사람 검수용 페이지 (신호 하이라이트 포함). 브라우저로 열면 된다

## 재생성

```bash
python3 scripts/check_bodies.py    # 본문 전수 검증
bash scripts/generate.sh           # 63건 재생성 (API 키 불필요 — 본문은 scripts/corpus_bodies/에 커밋되어 있다)
python3 scripts/review_corpus.py   # 검수 페이지 갱신
```

같은 입력에서 항상 같은 코퍼스가 나온다 (문서 텍스트·문자 오프셋·정답지 전부 결정론적).

## 의도적으로 심어둔 것

데모가 실패하지 않도록 신호를 각본대로 배치했다 (`docs/03 §2`). 신호 문장은 생성기가 직접 소유하므로 위치가 흔들리지 않는다.

- 치료 공백(청소년) 14건 / 독립 HCP 9인 / 3권역 — 대표 가설의 근거
- 이상사례 시사 5건 — 안전성 경로로 분리되는지 증명
- 스키마에 없는 개념(post-stroke) 6건 — 스키마 변경 제안(SCP) 유도
- 자료 요청 8건 · 긍정 신호 7건 · 노인 병용 장벽 10건
- **Critic이 차단해야 하는 문장 2건** — 허가 범위를 벗어난 단정과 과일반화를 일부러 넣어, 시스템이 막는 장면을 보여준다

또한 마스킹 시연용으로 가상 이름·전화번호가 3건에 들어 있다 (역시 실재하지 않는 값).
