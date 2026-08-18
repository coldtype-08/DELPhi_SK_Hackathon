# Contract 부트스트랩 — AI 독립 초안 (원문 보존)

> **생성 조건 (2026-08-18)**: v0.1을 전혀 모르는 격리 에이전트(제약 Medical Affairs 데이터 아키텍트 페르소나)에게
> 코퍼스 샘플 15건(유형 층화, 한국어 1건 포함)**만** 읽게 하고 스키마를 처음부터 제안하게 했다.
> 이 문서는 그 출력의 무편집 원문이다. 채택·제외·보류 판정은 사람(건태)이 했다 — DECISIONS 08/19.
> 발표 서사의 증빙: "0→1 스키마도 AI가 제안하고 사람이 확정했다."

---

# Proposed Database Schema — MSL Field-Medical Document Corpus

*Citation shorthand: `001` = `DOC-20250915-001`, `061` = `DOC-20260721-061`, etc. All 15 documents were read, including the Korean voice-interview transcript (`061`). All enum codes are English/language-neutral; verbatim evidence is stored in the source language.*

---

## 1. Entities

**1. `documents`** — One row per source record, preserving the external doc ID, type, date, language, and immutable raw text. The corpus mixes six distinct formats (multi-HCP highlights, single-HCP notes, call memos, an email summary, congress reports, a Korean voice transcript), and the ID sequence has gaps (011, 014, 016–036, 038–060 absent), so source IDs must be preserved as natural keys rather than renumbered. The raw text is the anchor for all character-offset evidence pointers and must never be mutated after ingest.

**2. `msls`** — Registry of field-medical authors (five distinct names appear: Rachel Suh, Tom Alvarez, Sam Becker, Dana Cho, Priya Menon). Needed to attribute interactions and follow-up ownership, and to avoid free-text name drift across 15+ documents.

**3. `document_authors`** — Junction table between documents and MSLs. Highlights documents carry two authors (`001`, `005`, `010`) while notes carry one, so authorship is many-to-many; critically, in two-author highlights the per-HCP block author is *not* attributable, which a single `author` column would falsely imply.

**4. `institutions`** — Site master (name, city, state, coverage code). The same institutions recur across documents and doc types (Sonoran in `010`/`012`/`015`, Copper Mesa in `005`/`010`/`037`), and congress reports (`015`, `037`) name the institution *without* city/state — so location must be resolved through a master record, not re-extracted per document. State is the only geographic rollup key the corpus supports, and it is required for "signals by region."

**5. `hcps`** — Physician master. Seven physicians appear in two or more documents (Whitcomb, Tsang, Ost, Reyes, Gallagher, Brandt, Maldonado), and the central analytic question — "how many *distinct* physicians raised this?" — is unanswerable without entity resolution to a stable `hcp_id`. Kept deliberately thin: name, credential, home institution; no specialty, no identifiers the documents don't contain.

**6. `interactions`** — One row per HCP-conversation unit. This is the pivotal design decision: a document is *not* an interaction — highlights docs contain 4–6 independent HCP blocks (`001`, `005`, `010`) and congress reports contain 3–4 conversations, sometimes on a different date than the document date (`037`: April 16 conversations in an April 17 report). Interaction-level compliance attestations (AE screening, materials requested, product discussion, scientific exchange) live here because the documents state them per conversation.

**7. `signals`** — One row per extracted, quotable observation (unmet need, barrier, burden, trend, clinical experience, information request), typed against a governed topic vocabulary. This is the aggregation unit for requirement (a): e.g., the adolescent drug-resistant-epilepsy gap appears in six documents from five distinct HCPs (`001`, `004`, `005`, `010`, `015`, `061`) and must be countable by physician, region, and month. One conversation can yield multiple signals (`061` yields an unmet-need mention *and* a data request from adjacent utterances). Unfavorable patient experiences are *never* stored here — they are screened into `ae_mentions` first.

**8. `signal_topics`** — Governed vocabulary table (not a hard-coded enum) for `topic_code`, with lifecycle status. Fifteen documents cannot anticipate every future theme (post-stroke epilepsy appeared once, in `005`, mid-corpus), so topics need controlled, human-approved extension rather than either a frozen enum (forces shoehorning) or free text (destroys countability).

**9. `ae_mentions`** — Quarantined pharmacovigilance intake table, physically separate from `signals` and excluded from every analytic view. Exactly one AE appears in the corpus — dizziness and somnolence in an adult patient, reported mid-dialogue in Korean (`061`) — and the MSL's documented response ("절차대로 안전성 검토 경로로 전달" / route via the safety review path) defines the requirement: capture verbatim, minimum reporter/patient/product context, and routing status only. No medical judgment fields (seriousness, causality, coding) — those belong to the PV system downstream.

**10. `follow_up_actions`** — Commitments and next steps with owner and status. Nearly every document creates or closes obligations ("confirm with Medical Information… reply before the next visit" `001`; "forward the agenda once public" `010`; two enumerated tasks in `012`), and unfulfilled commitments to HCPs are themselves a compliance exposure worth tracking. Logistical asks (e.g., a congress agenda) live here rather than polluting `signals`.

**11. `evidence_spans`** — Provenance table: every extracted row (interaction block, signal, AE mention, follow-up) links to one or more `(doc_id, char_start, char_end)` spans against the immutable raw text, satisfying requirement (b). A separate table (rather than columns) is needed because a single signal can rest on non-contiguous sentences (e.g., `001` Whitcomb: the unmet-need statement and the referral-growth context are separate lines).

---

## 2. Fields

> **Shared workflow columns** (system-generated, not document content) on `hcps`, `institutions`, `interactions`, `signals`, `ae_mentions`, `follow_up_actions`: `review_status` (enum `CANDIDATE | APPROVED | REJECTED`), `reviewed_by`, `reviewed_at`, `extracted_at`, `extractor_version`. Only `APPROVED` rows enter counts. Not repeated in the tables below.

### 2.1 `documents`

| field | type | allowed values (enum) | evidence (docs) | agg value |
|---|---|---|---|---|
| `doc_id` | text PK | — (preserve external IDs; sequence has gaps) | all 15 filenames | high (join key) |
| `doc_type` | enum | `FIELD_HIGHLIGHTS \| INTERACTION_NOTE \| CALL_MEMO \| EMAIL_SUMMARY \| CONGRESS_REPORT \| VOICE_TRANSCRIPT` | 001/005/010; 002/003/004/008/009/012; 007/013; 006; 015/037; 061 | med |
| `doc_date` | date | — | header of every doc | high (time axis) |
| `language` | enum | `EN \| KO` | 061 (KO) vs. all others (EN) | low |
| `event_name` | text, nullable | — | 015, 037 ("Annual Epilepsy Care Symposium") | low |
| `recording_consent` | enum | `VERBAL_YES \| NOT_DOCUMENTED \| NOT_APPLICABLE` | 061 ("동의 확인: 예 — 녹음 전 구두 동의"); N/A for non-recorded types | med (audit) |
| `raw_text` | text, immutable | — | all; anchor for offsets | low (provenance) |

### 2.2 `msls`

| field | type | allowed values | evidence | agg value |
|---|---|---|---|---|
| `msl_id` | int PK | — | system | med (coverage counts) |
| `full_name` | text | — | 001–061 headers ("MSL:", "From:", "Author:", "작성:") | low |

### 2.3 `document_authors`

| field | type | allowed values | evidence | agg value |
|---|---|---|---|---|
| `doc_id` | FK | — | all | med |
| `msl_id` | FK | — | two authors on 001, 005, 010; one on the rest | med |

### 2.4 `institutions`

| field | type | allowed values | evidence | agg value |
|---|---|---|---|---|
| `institution_id` | int PK | — | system | high (site counts) |
| `name` | text | — | every HCP line, e.g. "Northbrook Neurology Institute" (001, 004) | med |
| `city` | text, nullable | — | 001–013, 061; absent in congress reports 015/037 | med |
| `state_code` | text(2), nullable | open set — 18 states observed (ME, NY, CA, CT, WA, NV, WI, LA, AZ, VT, IA, KS, MS, MN, RI, TN, VA, OH) | same lines | high (region rollup) |
| `coverage_code` | enum | `AR \| RSM` — semantics not stated in corpus; **flag for business-owner confirmation before use** | AR: 001 (Ratliff), 007/009 (Brandt), 008, 010 (Nguyen-Barr); RSM: all others | high (territory rollup, once defined) |

### 2.5 `hcps`

| field | type | allowed values | evidence | agg value |
|---|---|---|---|---|
| `hcp_id` | int PK | — | repeat HCPs across docs: Whitcomb 001+004, Ost 010+012+015, Reyes 005+010+037, Gallagher 005+015+037, Tsang 001+010+037, Brandt 007+009, Maldonado 005+037 | high (distinct-HCP counts) |
| `full_name` | text | — | all HCP lines | low |
| `credential` | text | only "MD" observed — keep text, not enum, until variety appears | all HCP lines | low |
| `primary_institution_id` | FK | — | all HCP lines; resolves congress mentions lacking city/state (015, 037) | high (via institution → region) |

### 2.6 `interactions`

| field | type | allowed values | evidence | agg value |
|---|---|---|---|---|
| `interaction_id` | int PK | — | multi-HCP docs force this grain: 001 (4 blocks), 005 (5), 010 (6), 015 (3), 037 (4) | high |
| `doc_id` | FK | — | all | high (provenance) |
| `hcp_id` | FK | — | every block names exactly one HCP | high |
| `interaction_date` | date, nullable | — (fallback: `doc_date`) | 037: April 16 conversations inside an April 17 report; 015: relative days only | high (time axis) |
| `time_detail_as_stated` | text, nullable | — (never normalized) | 012 "8:40 a.m."; 037 "approximately 11:40"; 015 "Thursday afternoon" | low |
| `channel` | enum | `IN_PERSON \| PHONE \| EMAIL \| CONGRESS_ONSITE \| UNKNOWN` | in person: 002–004, 008, 009, 012; phone: 007, 013, 010 (Reyes "by phone"); email: 006; congress: 015, 037 | med |
| `duration_minutes` | int, nullable | — (as stated, approximate) | "forty minutes" 001; ~15 003; ~20 004; ~6 007; 12 009; ~8 013; "half hour" 010 | med |
| `visit_basis` | enum | `SCHEDULED \| DROP_IN \| COURTESY \| UNKNOWN` | "Drop-in" 003; drop-in window notes 008; "courtesy visit/stop" 012, 010 (Nguyen-Barr); rescheduled-then-held 009 | low |
| `product_discussion` | enum | `NONE \| CLASS_LEVEL \| PRODUCT_SPECIFIC` | NONE: 002, 003, 008, 012; CLASS_LEVEL: 007 ("ASM landscape"), 010 (Okafor), 037 (Tsang); PRODUCT_SPECIFIC: 001, 010 (Ost), 037 (Gallagher), 015 (Salas), 061 | high (compliance monitoring) |
| `scientific_exchange_occurred` | bool, nullable | — | explicit no: 008 ("no scientific exchange occured"), 012, 010 (Nguyen-Barr); explicit yes: 037 (Tsang "logged as a general scientific exchange") | med |
| `materials_requested` | enum | `REQUESTED \| NONE_STATED \| NOT_DOCUMENTED` | REQUESTED: 001 (Ratliff condensed reference), 061 (adolescent data); NONE_STATED: 002, 003, 004, 005, 008, 010, 012 | med |
| `ae_screening` | enum | `AE_MENTIONED \| NO_AE_STATED \| NOT_DOCUMENTED` | AE_MENTIONED: 061; NO_AE_STATED: 003, 004, 008, 009 ("asked and confirmed none"); NOT_DOCUMENTED: 001, 002, 005, 006, 007, 010, 012, 013, 015, 037 | high (PV audit: silence ≠ screened) |

### 2.7 `signals`

| field | type | allowed values | evidence | agg value |
|---|---|---|---|---|
| `signal_id` | int PK | — | system | high |
| `interaction_id` | FK | — | all signal-bearing blocks | high |
| `signal_type` | enum | `UNMET_NEED \| TREATMENT_BARRIER \| ACCESS_BURDEN \| OPERATIONAL_BURDEN \| PRACTICE_TREND \| CLINICAL_EXPERIENCE \| INFO_REQUEST` | UNMET_NEED: 001, 004, 005 (Boudreaux), 010 (Haddad), 015 (Salas), 061; TREATMENT_BARRIER: 001 (Ratliff DDI); ACCESS_BURDEN: 003, 005 (Gallagher); OPERATIONAL_BURDEN: 009, 013, 037 (Maldonado), 005 (Reyes), 008, 010 (Reyes); PRACTICE_TREND: 005 (Maldonado, Kowalczyk), 006, 009, 001 (referral growth), 010 (Okafor); CLINICAL_EXPERIENCE: 010 (Ost), 037 (Gallagher); INFO_REQUEST: 001 (Ratliff, Lindqvist), 005 (Kowalczyk), 015 (Salas), 061 | high (primary counting axis) |
| `topic_code` | FK → `signal_topics` | seed vocabulary below | see 2.8 | high (the dedup/counting key) |
| `label_scope` | enum | `IN_LABEL \| OFF_LABEL_DEVELOPMENT \| NOT_PRODUCT_RELATED` | OFF_LABEL_DEVELOPMENT: adolescent cluster 001/004/005/010/015/061 (adult-only approval stated in 001, 005, 010, 037, 061); IN_LABEL: 001 (elderly DDI), 010 (Ost), 037 (Gallagher); NOT_PRODUCT_RELATED: 003, 008, 009, 013 | high (routing gate: development-scope signals go to medical review only, never commercial) |
| `patient_population` | enum | `ADOLESCENT \| ELDERLY \| ADULT_DRE \| POST_STROKE \| NOT_POPULATION_SPECIFIC` | ADOLESCENT ("15- and 16-year-olds" 001; "seventeen-year-old" 005; "17-year-old" 015; "17세" 061; 004, 010); ELDERLY (001, "skewing older" 009, 005 Maldonado); ADULT_DRE (010 Ost, 037 Gallagher); POST_STROKE (005 Kowalczyk) | high |
| `solicitation` | enum | `UNSOLICITED \| SOLICITED_BY_MSL \| UNCLEAR` | UNSOLICITED: 001 ("without any prompting"), 005 ("unprompted"), 010 ("before I had asked anything"), 037 ("unsolicited comment"), 015 (header); SOLICITED_BY_MSL: 004 (MSL "asked what the gaps look like"), 061 (MSL raised the adolescent topic first) | high (changes compliance meaning of off-label topics) |
| `msl_response` | enum | `LABEL_SCOPE_RESTATED \| LOGGED_AS_STATED \| ROUTED_TO_MED_INFO \| ROUTED_TO_SAFETY \| DECLINED_OUT_OF_SCOPE \| LITERATURE_CHECK_COMMITTED \| NONE_DOCUMENTED` | LABEL_SCOPE_RESTATED: 001 (Lindqvist), 005, 010, 015, 037; LOGGED_AS_STATED: 001 (Whitcomb), 004, 061; ROUTED_TO_MED_INFO: 001, 015; ROUTED_TO_SAFETY: 061; DECLINED_OUT_OF_SCOPE: 002 (curriculum), 009 (EHR advice); LITERATURE_CHECK_COMMITTED: 005 (Kowalczyk) | med (compliance audit trail) |
| `verbatim_quote` | text (source language) | — | required for every row; e.g. 005 direct quote "my hardest clinic days are telling parents of a seventeen-year-old…"; 061 Korean quotes | low (evidence, not aggregated) |

### 2.8 `signal_topics` (governed vocabulary — seeded from this corpus only)

| field | type | allowed values / seeds | evidence | agg value |
|---|---|---|---|---|
| `topic_code` | text PK | seeds: `ADOLESCENT_DRE_GAP` (001, 004, 005, 010, 015, 061) · `ELDERLY_DDI_POLYPHARMACY` (001) · `PRIOR_AUTH_BURDEN` (003, 005) · `EHR_SEIZURE_DATA_CAPTURE` (009, 013, 037) · `STAFFING_SHORTAGE` (004, 005, 037) · `APPOINTMENT_BACKLOG` (004, 005, 006, 009, 037) · `TELEHEALTH_OPERATIONS` (010) · `POST_STROKE_EPILEPSY_INTEREST` (005) · `PANEL_AGING` (005, 009) · `PEDIATRIC_REFERRAL_GROWTH` (001) · `POSITIVE_DRE_OUTCOME` (010, 037) · `FORMULARY_CLASS_REVIEW` (010) | per seed | high |
| `label` / `definition` | text | — | human-authored | low |
| `status` | enum | `ACTIVE \| DEPRECATED` | corpus shows mid-stream topic emergence (post-stroke first appears in 005) | med |

### 2.9 `ae_mentions` (quarantined; excluded from all analytic views)

| field | type | allowed values | evidence | agg value |
|---|---|---|---|---|
| `ae_id` | int PK | — | system | high (PV SLA counts) |
| `interaction_id` / `reporter_hcp_id` | FK | — | 061 (Dr. Feldman) | high |
| `verbatim_text` | text (source language) | — | 061: "성인 환자 한 분은 복용 시작하고 나서 어지러움하고 졸림이 꽤 있다고 하셨어요" | low (evidence) |
| `reported_terms_as_stated` | text | — (no MedDRA coding here) | 061: dizziness (어지러움), somnolence (졸림) | med |
| `patient_descriptor_as_stated` | text | — | 061: "one adult patient" — supports identifiable-patient element only | low |
| `suspected_product_as_stated` | text, nullable | — | 061: product **not named**, implied by context | med |
| `product_explicitly_named` | bool | — | 061: false — forces human confirmation before PV handoff content is finalized | med |
| `routing_status` | enum | `PENDING_PV \| SENT_TO_PV \| PV_ACKNOWLEDGED` | 061: MSL commits to route via the safety path | high (handoff SLA monitoring) |
| `sent_to_pv_at` | timestamp, nullable | — | workflow | high |

### 2.10 `follow_up_actions`

| field | type | allowed values | evidence | agg value |
|---|---|---|---|---|
| `action_id` | int PK | — | system | med |
| `interaction_id` / `owner_msl_id` | FK | — | all cited below | med |
| `action_type` | enum | `INFO_FULFILLMENT \| SCHEDULING \| INTERNAL_ESCALATION \| OTHER` | INFO_FULFILLMENT: 001 ("confirm with Medical Information… reply before the next visit"), 005 (lit check), 010 (forward agenda), 015 (registration deadline), 061 (share data within allowed scope); SCHEDULING: 002 (mid-Nov), 006, 007, 012 (two tasks), 013, 061; INTERNAL_ESCALATION: 004 ("will flag the adolescent comment internally") | med |
| `description_as_stated` | text | — | same | low |
| `due_hint_as_stated` | text, nullable | — (kept verbatim: "before the next visit" 001, "mid-January" 012, "next quarter, probably Jan" 004) | 001, 004, 012 | low |
| `due_date` | date, nullable | — (human-normalized only) | workflow | med |
| `status` | enum | `OPEN \| DONE \| CANCELLED` | 006/003 show explicit "nothing pending" states; 015 "follow-ups have been logged" | med (open-commitment tracking) |

### 2.11 `evidence_spans`

| field | type | allowed values | evidence | agg value |
|---|---|---|---|---|
| `span_id` | int PK | — | system | low |
| `entity_type` | enum | `INTERACTION \| SIGNAL \| AE_MENTION \| FOLLOW_UP_ACTION` | every extracted row must carry ≥1 span | low |
| `entity_id` | int | — | — | low |
| `doc_id` | FK | — | all | high (traceability joins) |
| `char_start` / `char_end` | int | — offsets into immutable `documents.raw_text` | all; multi-span need shown by 001 (Whitcomb: need statement + referral context on separate lines) | low |
| `quoted_text` | text | — (redundant copy for human review; offsets remain authoritative) | all | low |

---

## 3. Deliberately NOT structured

- **Personal small talk and life details** — weddings, storms, driving fatigue, monsoon flight delays, the resident lounge (010 Nguyen-Barr, 012, 002). Zero analytic value and privacy-adjacent; remains only in raw text.
- **Phone numbers and staff contact details** — the coordinator's direct line in 012, the HCP's personal mobile and the named scheduling contact in 061, entrance/badge/parking logistics in 008 and 003. Data-minimization: contact PII must not enter analytics tables; if operationally needed it belongs in an access-controlled CRM, not this schema. Raw documents containing it get restricted read access.
- **HCP-quoted quantities as numeric fields** — "about a third more" (009), "two such pts this month" (005), "5 or 6 in the last yr" (005), "nine weeks out" (005, 037), "every few months" (004), "half of follow-ups virtual… nobody has measured it properly" (010). These are unverified impressions; converting them to integers invites false precision and anecdote-summing. They stay inside `verbatim_quote`; all counts are computed over APPROVED signal rows only.
- **Sentiment, tone, and personality judgments** — "tone noticeably positive" (010), "accepted without pushback" (001), "politely" (001, 002). Subjective, extractor-unstable, and adjacent to HCP profiling.
- **Per-HCP prescriber/adoption status** — 010 (Ost) and 037 (Gallagher) reveal that specific physicians have patients on the product. A "prescriber flag" on `hcps` would directly enable prescribing-behavior profiling, which is prohibited; the observation is kept only as a `CLINICAL_EXPERIENCE` signal with no physician-level rollup attribute.
- **AE medical judgment fields** — seriousness, causality, expectedness, MedDRA coding, outcome (061). These are the pharmacovigilance system's jurisdiction; duplicating them here creates conflicting records of regulated data.
- **HCP specialty and demographics** — never stated anywhere in the corpus (epilepsy focus is only implied by institution names); inferring it would violate the no-invention rule.
- **Congress session content and clinic-internal workflow detail** — the session summary in 015, the nursing spreadsheet in 009, the dual templates in 037. Captured only as topic-coded burden signals with quotes; modeling other organizations' internals is low value. Likewise a **product master table is deferred**: only one focal product appears (XCOPRI/cenobamate/CNB), with other ASMs named solely as failed prior therapies inside quotes (010).

---

## 4. Top 5 risks

1. **AE leakage into general analytics.** The corpus's only adverse event sits mid-dialogue, in Korean, with the product never explicitly named (061) — the exact shape an extractor misses or misfiles as a "negative experience signal." Compounding this, only 4 of 15 documents carry explicit "no AE" attestations (003, 004, 008, 009); the rest are silent, and silence must not be recorded as "screened clean." Mitigation: mandatory AE-screening pass on every interaction, the three-valued `ae_screening` attestation, and a physically separate quarantine table with routing SLAs.

2. **The strongest signal is inherently off-label, and mishandling it becomes promotional risk.** The adolescent DRE gap is the corpus's dominant repeated signal (6 documents, 5 distinct HCPs), and every mention concerns use outside the adult-only approval. If `label_scope` tagging fails, or aggregate views reach commercial audiences, a compliant set of logged observations turns into evidence of off-label promotion. `OFF_LABEL_DEVELOPMENT` rows must route exclusively to medical/development review, with access separation enforced at the view layer.

3. **Counting integrity: duplicates, anecdotes, and topic fragmentation.** The same physician repeats the same theme across documents (Whitcomb in 001 and 004), field notes and congress reports overlap the same people (Gallagher, Ost, Reyes), congress documents omit city/state so entity resolution can silently split one HCP into two, and quoted patient counts tempt summation. Reports must distinguish mentions vs. distinct interactions vs. distinct HCPs; equally, a sloppy topic vocabulary undercounts (one theme coded two ways) or drowns signal in an `OTHER` dump — hence the governed, human-approved `signal_topics` table.

4. **Speaker, stance, and solicitation misattribution by the extractor.** The documents' compliance meaning hinges on who said what and why: HCPs repeatedly "framed this as a limit of what is approved rather than a request to work around it" (001, 005), MSLs' own boundary statements sit adjacent to HCP asks, and solicitation flips matter — 004 and 061 were MSL-prompted while 001/005/010/037 were unprompted. Typos ("recieved," "yaer"), heavy shorthand (003, 007), and Korean dialogue turns (061) all raise the misread rate. Every such field stays `CANDIDATE` until a human reviewer confirms against the evidence span.

5. **Privacy and profiling creep.** Raw text contains personal mobile numbers, named support staff, travel plans, and visit-pattern intelligence; structuring or indexing it would assemble a de facto surveillance file on physicians and their staff, and clinical-experience fields sit one join away from a prohibited prescribing profile. Mitigations are structural: PII never leaves restricted raw storage, no per-HCP behavioral attributes exist in the schema, and aggregation views expose physician *counts*, not physician *dossiers*.
