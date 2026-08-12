# DELPHi 
<p align="center">
  <img src="./Assets/logo.png" alt="DELPHI Logo" width="300">
</p>

> Adaptive Data Foundation for Growth Intelligence for XCOPRI®

고대 델포이는 중요한 결정을 앞둔 사람들이 질문을 가져오던 장소였습니다. 
현대의 Delphi method는 불확실성이 큰 문제에서 여러 전문가의 의견을 익명·반복적으로 수집하고 통제된 피드백을 통해 판단을 구조화합니다. 
익명성, 반복, 통제된 피드백과 집단 반응을 Delphi method의 핵심 특성으로 설명합니다.
DELPHi는 여기서 영감을 받아, 흩어진 신호와 서로 다른 관점을 구조화하되 결론만 남기지 않고 근거와 이견까지 추적 가능하게 남깁니다.
> 신탁은 해석을 남겼습니다. DELPHi는 근거를 남깁니다.

DELPHi는 비정형 내부 데이터를 원문 근거가 연결된 AI-readable 데이터로 전환하고, 그 위에서 내부 신호와 외부 과학 근거를 교차검증하는 XCOPRI 매출 성장 플랫폼입니다.

핵심 차별점은 문서를 한 번 분석하는 데 있지 않습니다. 과거 데이터에서 발견한 반복 개념을 사람이 검토할 수 있는 스키마 변경안으로 만들고, 승인된 구조를 향후 현장 데이터 수집에 다시 반영하는 폐쇄형 학습 루프에 있습니다.

## 문제 정의

우리의 핵심 Pain Point는 데이터 부족이 아니라, 현장에서 생성된 의미 있는 신호가 조직의 판단으로 전환되기까지 걸리는 긴 ‘Insight Latency(인사이트 잠복기간)’입니다.

Insight Latency는 기록이 생성된 시점부터 반복성 · 근거 · 우선순위를 갖춘 의사결정 정보로 조직이 인지하는 시점까지의 간격입니다. 

현재는 데이터가 계속 쌓여도 비정형 · 자유서술 형태로 분산되어 있어, 중요한 신호가 발견되고 검증되기까지 많은 시간이 필요합니다.

문제의 핵심은 정보 부족이 아니라, 축적된 비정형 정보가 검증·집계·재사용 가능한 근거로 전환되지 않는다는 데 있습니다. XCOPRI의 다음 성장 신호는 이미 대화·문서·논문·임상 데이터 속에 있습니다. 문제는 그것들이 서로 연결되지 않는다는 것입니다.

## 핵심 구조

<img src="Assets/delphi_작동구조_readme.png" alt="DELPHi 작동 구조 — Sense · Screen · Board · Field가 하나의 Data Contract를 공유한다">

1. **DELPHi Sense — 정제 · 구조화**<br>
   비정형 문서와 동의 · 승인이 전제된 interaction을 현재 schema에 따라 구조화하고, 모든 값에 원문 evidence pointer와 extraction version을 연결합니다. 승인된 데이터를 SQL로 집계해 반복성과 추이를 계산하고, 그 안에서 새로운 성장 가능성을 시사하는 신호와 가설 후보를 도출합니다. 기존 schema로 표현되지 않는 반복 개념은 자동 적용하지 않고 Schema Change Proposal로 제안합니다.

2. **DELPHi Screen — 근거 스크리닝**<br>
   승인된 내부 반복 신호를 PubMed, ClinicalTrials.gov, 현재 적용 가능한 공식 라벨 등 외부 근거와 연결합니다. 전문 AI 역할이 support · counter evidence와 evidence gap을 구조화하며, 근거 없는 주장과 허가 범위를 벗어난 단정은 Critic 역할이 차단하고 그 이력을 남깁니다.

3. **DELPHi Board — 판단 · 실행**<br>
   사실 · 패턴 · AI 해석 · 전략 제안을 분리해 제시하고, 관점별 AI 역할의 심의 내용과 최종 권고를 회의록으로 기록합니다. 권한을 가진 사람이 가설 유형에 맞는 후속 액션과 owner · KPI · due date를 승인하며, 승인 · 보류 · 기각의 사유는 이력으로 보존됩니다.

4. **DELPHi Field — 수집 · 환류 인터페이스**<br>
   DELPHi Field는 Sense와 Board를 연결하는 상시 학습 인터페이스입니다. 시장별 정책과 필요한 동의를 전제로 interaction을 구조화 항목과 자유서술로 기록하고, 현재 Data Contract에 따라 AI가 구조화 후보를 제안합니다. 사용자가 수정 · 승인한 값만 분석에 반영하며, 미해결 자료 요청과 역할에 맞는 승인 정보를 다음 interaction 전에 제공합니다.
   
4. **DELPHi Board — 판단·실행**  
   사실·패턴·AI 해석·전략 제안을 분리해 제시하고, 권한을 가진 사람이 가설 유형에 맞는 후속 액션과 owner·KPI·due date를 승인합니다.
   


