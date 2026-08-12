<p align="center">
  <img src="./Assets/logo.png" alt="DELPHi Logo" width="300">
</p>

<h1 align="center">DELPHi</h1>

<p align="center">
  <b>Adaptive Data Foundation for Growth Intelligence — XCOPRI®</b><br>
  <i>신탁은 해석을 남겼습니다. DELPHi는 근거를 남깁니다.</i>
</p>

---

DELPHi는 흩어진 **비정형 내부 데이터를 원문 근거가 연결된 AI-readable 데이터로 전환**하고, 그 위에서 **내부 신호와 외부 과학 근거를 교차검증**하는 XCOPRI 매출 성장 플랫폼입니다.

핵심 차별점은 문서를 한 번 잘 분석하는 데 있지 않습니다. 과거 데이터에서 발견한 반복 개념을 사람이 검토할 수 있는 **스키마 변경안**으로 만들고, 승인된 구조를 다시 현장 데이터 수집에 반영하는 **폐쇄형 학습 루프**에 있습니다.

## 목차

- [이름의 유래](#이름의-유래)
- [문제 정의 — Insight Latency](#문제-정의--insight-latency)
- [작동 구조](#작동-구조)
- [기대 효과](#기대-효과)
- [설계 원칙](#설계-원칙)
- [화면 미리보기](#화면-미리보기)

## 이름의 유래

고대 델포이는 중요한 결정을 앞둔 사람들이 질문을 가져오던 장소였습니다. 현대의 **Delphi method**는 익명성 · 반복 · 통제된 피드백을 통해, 불확실성이 큰 문제에서 여러 전문가의 판단을 하나의 합의로 구조화합니다.

DELPHi는 여기서 이름을 가져왔습니다. 다만 신탁과 달리 **결론만 남기지 않습니다.** 흩어진 신호와 서로 다른 관점을 구조화하되, 그 근거와 이견까지 추적 가능한 형태로 보존합니다.

## 문제 정의 — Insight Latency

우리의 핵심 Pain Point는 데이터 부족이 아닙니다. 현장에서 생성된 의미 있는 신호가 조직의 판단으로 전환되기까지 걸리는 **긴 잠복기간**입니다.

> **Insight Latency**<br>
> 기록이 생성된 시점부터, 반복성 · 근거 · 우선순위를 갖춘 의사결정 정보로 조직이 인지하는 시점까지의 간격.

데이터는 계속 쌓이지만 비정형 · 자유서술 형태로 분산되어 있어, 중요한 신호 하나가 발견되고 검증되기까지 많은 시간이 필요합니다. 문제의 본질은 **정보의 부재가 아니라, 축적된 비정형 정보가 검증 · 집계 · 재사용 가능한 근거로 전환되지 않는다는 것**입니다.

> XCOPRI의 다음 성장 신호는 이미 대화 · 문서 · 논문 · 임상 데이터 속에 있습니다.<br>
> 문제는 그것들이 서로 연결되지 않는다는 것입니다.

## 작동 구조

<p align="center">
  <img src="./Assets/delphi_작동구조_readme.png" alt="DELPHi 작동 구조 — Sense · Screen · Board · Field가 하나의 Data Contract를 공유한다">
</p>

네 개의 모듈은 하나의 **Data Contract**를 공유합니다.

```
Field ⇄ Sense → Screen → Board
  ↑                        │
  └──── 승인된 구조·결정 재반영 ────┘
```

| 모듈 | 역할 | 한 줄 설명 |
| :--- | :--- | :--- |
| **Sense** | 정제 · 구조화 | 비정형 데이터를 evidence pointer가 연결된 의미 단위로 전환하고 가설 후보를 도출 |
| **Field** | 수집 · 재반영 | Sense의 Ontology로 현장 데이터를 실시간 수집하고 다시 Sense로 환류 |
| **Screen** | 다중 에이전트 근거 검증 | 전문가 Agent들이 공개 근거를 조회해 support · counter evidence와 gap을 구조화 |
| **Board** | AI 심의와 사람의 승인 | BoardAgent가 종합 심의하고, 최종 승인과 실행 결정은 사람이 수행 |

### 1. DELPHi Sense — 정제 · 구조화

비정형 문서와 동의 · 승인이 전제된 interaction을 의미 단위 · Ontology 구조로 정제하고, **모든 값에 원문 evidence pointer와 extraction version을 연결**합니다.

승인된 데이터를 집계해 반복성과 추이를 계산하고 성장 가설 후보를 도출합니다. 기존 schema로 표현되지 않는 반복 개념은 자동 적용하지 않고 **Schema Change Proposal**로 제안합니다.

### 2. DELPHi Field — 수집 · 데이터 재반영

DELPHi Sense가 확립한 **의미 단위 · Ontology 구조로 신규 현장 데이터를 수집**합니다.

동의를 전제로 한 실시간 녹음에서 의미를 캐치하고, 적응증 확장 · safety issue 같은 주요 사항을 실시간으로 마크한 뒤, 수집된 신규 데이터를 다시 Sense로 보냅니다.

### 3. DELPHi Screen — 다중 에이전트 근거 검증

Sense가 도출한 가설 후보와 인사이트를 **전문가 Agent들이 각자 Research로 교차검증**합니다.

각 에이전트는 PubMed, ClinicalTrials.gov, 공식 허가 · 안전성 자료 등 공개 근거를 조회해 support · counter evidence와 evidence gap을 구조화합니다.

### 4. DELPHi Board — AI 심의와 사람의 승인

**BoardAgent**들이 모든 정보를 종합 심의해 후속 action item을 제안하고, **CEO Agent**가 최종 권고 의견을 제시합니다.

사실 · 패턴 · AI 해석 · 전략 제안을 구분해 표시하되, **최종 승인과 실행 결정은 권한을 가진 사람이 함께 수행**합니다.

## 기대 효과

| 지표 | 목표 | 작동 방식 |
| :--- | :---: | :--- |
| **Data Latency** | 70% 이상 단축 | 사람이 매번 다시 읽고 분류하는 대신, AI가 Data Contract에 따라 구조화 후보를 생성하고 사용자는 필요한 부분만 검토 · 승인 |
| **Insight Latency** | 50% 이상 단축 | 구조화된 내부 신호와 외부 근거를 연결해, 지지 근거 · 반대 근거 · 근거 공백이 포함된 Board-ready Growth Hypothesis를 준비 |
| **반복 정리 · 재분류 업무** | 70% 이상 감소 | 한 번 승인된 데이터를 재사용하고, 신규 데이터도 동일한 Data Contract에 따라 축적 |

특히 정기 보고, 추가 분석, 회의 준비 때 반복되던 자료 취합과 재가공 시간을 직접적으로 절감합니다.

## 설계 원칙

- **Evidence-linked by default** — 모든 구조화 값은 원문 위치(evidence pointer)와 extraction version에 연결됩니다. 근거 없는 값은 존재할 수 없습니다.
- **Human-in-the-loop** — AI는 후보와 권고를 제안하고, 최종 승인은 사람이 합니다. 승인되지 않은 값은 분석에 반영되지 않습니다.
- **Schema는 자동으로 바뀌지 않습니다** — 새로운 반복 개념은 Schema Change Proposal → 검토 → 승인을 거쳐야 Data Contract에 반영됩니다.
- **이견도 자산입니다** — counter evidence, evidence gap, 보류 · 기각 사유는 모두 이력으로 보존됩니다.

## 화면 미리보기

<!-- 목업 이미지 파일명을 실제 파일에 맞게 수정해 주세요 -->

| | |
| :---: | :---: |
| <img src="./Assets/mockup_sense.png" alt="DELPHi Sense" width="420"> | <img src="./Assets/mockup_field.png" alt="DELPHi Field" width="420"> |
| **DELPHi Sense** — 구조화 후보 검토 · 승인 | **DELPHi Field** — 실시간 수집과 주요 사항 마크 |
| <img src="./Assets/mockup_screen.png" alt="DELPHi Screen" width="420"> | <img src="./Assets/mockup_board.png" alt="DELPHi Board" width="420"> |
| **DELPHi Screen** — 에이전트 교차검증 결과 | **DELPHi Board** — 심의 요약과 승인 화면 |
