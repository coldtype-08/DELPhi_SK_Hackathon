"""에이전트 등록부 — 페르소나·모델·API 키·출력 스키마를 한 곳에서 정의한다 (08/22 신설).

[cross] 엔진 층은 인혁 오너십 · 페르소나 프롬프트는 건태 오너십

**에이전트가 무엇인지 이 파일이 정의한다.** 코드 어디에도 "너는 ~다"가 하드코딩되어 있지 않고,
페르소나는 전부 `prompts/agent_*.md`에 있다. 에이전트를 늘리는 일 = 이 dict에 한 줄 + md 하나.

| 에이전트 | 하는 일 | 왜 사람이 아니라 AI인가 |
|---|---|---|
| `contract_architect` | 원석을 읽고 **뽑을 항목(스키마) 자체를 제안** | 무엇을 뽑을지부터 데이터가 정해야 한다 (Contract 부트스트랩, 데모 ①) |
| `hcp_attributor` | 한 문서 안에서 **누구의 발언인지** 구간을 가른다 | 원석은 의사 8~14인이 한 파일에 섞여 있다 |
| `insight_analyst` | 그 구간을 **한 줄씩** 읽고 스키마 항목으로 뽑는다 | 뇌전증 진료 맥락을 알아야 미묘한 신호가 보인다 |

세 에이전트 모두 **판단만 하고 수치는 만들지 않는다.** 문자 위치·건수·등급은 전부 파이썬이 센다
(절대 규칙 #1). 각 에이전트의 출력이 어떻게 검증되는지는 그 에이전트를 부르는 모듈에 있다.
"""

from dataclasses import dataclass, field

from ..config import MODEL_BOARD, MODEL_EXTRACT


@dataclass(frozen=True)
class AgentSpec:
    name: str                 # llm_runs.purpose 에 그대로 기록된다
    label_ko: str             # 화면 표기
    persona_file: str         # prompts/agent_*.md — "너는 ~다"는 전부 여기
    model: str
    api_key_env: str          # 이 키가 없으면 ANTHROPIC_API_KEY 로 폴백
    schema_name: str
    schema: dict = field(default_factory=dict)
    max_tokens: int = 4096


# ── ① Contract 설계자 — 원석 → 스키마 제안 (데모 ①) ─────────────────────────

CONTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "fields": {
            "type": "array",
            "description": "제안하는 스키마 항목. 원석에서 반복 관찰된 것만.",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "snake_case 영문 식별자"},
                    "label_ko": {"type": "string"},
                    "kind": {"type": "string", "enum": ["enum", "text", "bool"]},
                    "rationale_ko": {"type": "string", "description": "왜 이 항목이 필요한가 — 한 문장"},
                    "values": {
                        "type": "array",
                        "description": "kind=enum 일 때만. 원석에 실제로 나타난 값만.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "value": {"type": "string"},
                                "label_ko": {"type": "string"},
                                "evidence_quote": {"type": "string",
                                                   "description": "이 값이 나온 원문 문장 그대로"},
                            },
                            "required": ["value", "label_ko", "evidence_quote"],
                        },
                    },
                    "evidence_quotes": {
                        "type": "array",
                        "description": "이 항목이 필요하다고 판단한 근거 문장들 — 원문 그대로 복사",
                        "items": {"type": "string"},
                    },
                    "observed_in_docs": {
                        "type": "integer",
                        "description": "이 항목이 관찰된 문서 수 — **추정치이며 서버가 재계산한다**",
                    },
                },
                "required": ["key", "label_ko", "kind", "rationale_ko", "evidence_quotes"],
            },
        },
        "rejected": {
            "type": "array",
            "description": "제안하지 않기로 한 항목과 그 이유 — 무엇을 뺐는지가 스키마의 절반이다.",
            "items": {
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "reason_ko": {"type": "string"},
                },
                "required": ["key", "reason_ko"],
            },
        },
    },
    "required": ["fields", "rejected"],
}

# ── ② HCP 귀속자 — 한 문서 → 발언 구간 분할 ─────────────────────────────────
# 문자 오프셋을 LLM에게 세게 하지 않는다 (절대 규칙 #1). 경계 문자열을 그대로 인용시키고
# 파이썬이 `str.find`로 위치를 찾는다 — 인용이 틀리면 그 블록은 버려진다.

ATTRIBUTION_SCHEMA = {
    "type": "object",
    "properties": {
        "blocks": {
            "type": "array",
            "description": "문서에 등장한 순서대로. 의료진 발언이 아닌 구간(머리말·행정)은 넣지 않는다.",
            "items": {
                "type": "object",
                "properties": {
                    "hcp_surface": {"type": "string",
                                    "description": "문서가 그 의료진을 가리킨 표기 그대로 (이름·직함 포함)"},
                    "start_quote": {"type": "string",
                                    "description": "이 구간이 시작되는 지점의 원문 문자열을 그대로 복사 (한 줄 이상, 문서 안에서 유일해야 한다)"},
                    "end_quote": {"type": "string",
                                  "description": "이 구간의 마지막 원문 문자열을 그대로 복사"},
                    "specialty_surface": {"type": ["string", "null"],
                                          "description": "문서에 적힌 전문과 표기. 없으면 null — 짐작 금지"},
                    "institution_surface": {"type": ["string", "null"]},
                    "confidence": {"type": "string", "enum": ["CLEAR", "INFERRED", "UNCERTAIN"],
                                   "description": "CLEAR=문서가 명시 · INFERRED=문맥으로 이어붙임 · UNCERTAIN=경계가 모호"},
                    "boundary_note_ko": {"type": ["string", "null"],
                                         "description": "경계를 그렇게 잡은 근거. UNCERTAIN이면 필수"},
                },
                "required": ["hcp_surface", "start_quote", "end_quote", "confidence"],
            },
        },
        "unattributed_note_ko": {
            "type": ["string", "null"],
            "description": "어느 의료진에게도 귀속시킬 수 없는 구간이 있으면 무엇인지. 없으면 null",
        },
    },
    "required": ["blocks"],
}

# ── ③ 인사이트 분석가 — 구간 → claim 후보 ───────────────────────────────────
# 스키마 본체는 sense.py 가 소유한다(계약 enum과 함께 움직이므로). 여기서는 참조만 한다.


def _sense_schema() -> dict:
    from ..sense import SENSE_SCHEMA
    return SENSE_SCHEMA


AGENTS: dict[str, AgentSpec] = {
    "contract_architect": AgentSpec(
        name="contract_architect",
        label_ko="Contract 설계자",
        persona_file="agent_contract_architect.md",
        model=MODEL_BOARD,          # 스키마 설계는 한 번뿐이고 되돌리기 비싸다 → 가장 좋은 모델
        api_key_env="ANTHROPIC_API_KEY_CONTRACT",
        schema_name="contract_proposal_v1",
        schema=CONTRACT_SCHEMA,
        max_tokens=8192,
    ),
    "hcp_attributor": AgentSpec(
        name="hcp_attributor",
        label_ko="발언 귀속자",
        persona_file="agent_hcp_attributor.md",
        model=MODEL_EXTRACT,
        api_key_env="ANTHROPIC_API_KEY_ATTRIBUTION",
        schema_name="hcp_attribution_v1",
        schema=ATTRIBUTION_SCHEMA,
        max_tokens=8192,            # 하이라이트 문서는 의사 14인까지 나온다
    ),
    "insight_analyst": AgentSpec(
        name="insight_analyst",
        label_ko="인사이트 분석가",
        persona_file="agent_insight_analyst.md",
        model=MODEL_EXTRACT,
        api_key_env="ANTHROPIC_API_KEY_EXTRACT",
        schema_name="sense_extract_v1",
        max_tokens=4096,
    ),
}


def get_agent(name: str) -> AgentSpec:
    if name not in AGENTS:
        raise KeyError(f"등록되지 않은 에이전트: {name} (있는 것: {', '.join(AGENTS)})")
    spec = AGENTS[name]
    if not spec.schema and name == "insight_analyst":
        return AgentSpec(**{**spec.__dict__, "schema": _sense_schema()})
    return spec
