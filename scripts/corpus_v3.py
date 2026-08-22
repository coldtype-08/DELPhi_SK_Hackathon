#!/usr/bin/env python3
"""
corpus_v3.py — 코퍼스 v3 각본 (2026-08-21)

v2(90문서/165단위)에서 v3(320문서/≈1,090단위, HCP 300인, 2021-01~2026-08)로 확장.
generate_corpus.py가 이 모듈을 import해 각본·인물·본문을 받아가고, 렌더·오프셋·검증
파이프라인은 기존 것을 그대로 쓴다 (검증된 부분은 건드리지 않는다).

왜 조합형 산문 엔진인가:
  v2까지 블록 본문은 사람이 직접 쓴 scripts/corpus_bodies/*.json이었다(165블록). v3는 ≈1,090블록이라
  손으로 쓸 수 없고, 이 환경에서는 Claude API도 쓸 수 없다(키·egress). 그래서 **손으로 쓴 문장 조각**을
  시드 고정 PRNG로 조합한다 — LLM 없이 완전 재현 가능하고, 조각이 사람 문장이므로 결과도 사람 문장이다.
  기존 165블록은 그대로 재사용한다(손으로 쓴 산문이 더 좋고, 재현성의 기록이기도 하다).

절대 지키는 것 (docs/03 §3·§5):
  - 신호 문장(verbatim)은 이 스크립트가 소유한다. 조합 엔진은 주변 문장만 만든다.
  - 성별 대명사 금지(he/she/his/her) — 가명 HCP의 성별을 이름으로 추정하지 않는다.
  - 용량 수치 금지 (docs/02 부트스트랩에서 제외된 항목 — 허위 정밀도·규제 민감).
  - Development 신호(S1·S7·S8)는 "쓸 수 없어서 생기는 공백"으로만 쓴다. 오프라벨 사용 권유·시사 금지.
  - 인물·기관은 전부 가상. 실제 학회명은 **배경(이름·연도)으로만** 쓰고 세션 내용·발표 데이터는 재현하지 않는다.
"""

import random

# ──────────────────────────────────────────────────────────────────────────────
# 0. 규모 상수 (docs/03 §1과 동기)
# ──────────────────────────────────────────────────────────────────────────────

N_HCP = 300
SPAN_START = "2021-01"
SPAN_END = "2026-08"
LAST_DAY = "2026-08-21"   # 코퍼스 최신 문서 상한 (미래 날짜 금지)

# ──────────────────────────────────────────────────────────────────────────────
# 1. MSL 12인 (전원 가상) — 5.7년 구간이라 담당자 교대가 있는 게 자연스럽다
#    active: (시작 YYYY-MM, 종료 YYYY-MM) — 이 구간의 문서만 이 작성자가 쓴다
# ──────────────────────────────────────────────────────────────────────────────

MSL_V3 = {
    "A1":  {"name": "Rachel Suh",      "style": "narrative", "active": ("2021-01", "2026-08")},
    "A2":  {"name": "Tom Alvarez",     "style": "terse",     "active": ("2021-01", "2026-08")},
    "A3":  {"name": "Priya Menon",     "style": "email",     "active": ("2021-01", "2026-08")},
    "A4":  {"name": "Sam Becker",      "style": "terse",     "active": ("2021-01", "2026-08")},
    "A5":  {"name": "Dana Cho",        "style": "narrative", "active": ("2021-01", "2026-08")},
    "A6":  {"name": "Ingrid Halvorsen","style": "narrative", "active": ("2021-01", "2023-06")},
    "A7":  {"name": "Marcus Obeng",    "style": "terse",     "active": ("2021-01", "2024-03")},
    "A8":  {"name": "Yuki Tanabe",     "style": "email",     "active": ("2022-04", "2026-08")},
    "A9":  {"name": "Ravi Chandrasek",  "style": "narrative", "active": ("2022-09", "2026-08")},
    "A10": {"name": "Nadia Belhadj",   "style": "email",     "active": ("2023-07", "2026-08")},
    "A11": {"name": "Colin Ferreira",  "style": "terse",     "active": ("2024-04", "2026-08")},
    "A12": {"name": "Sunny Okafor",    "style": "narrative", "active": ("2024-10", "2026-08")},
}

# ──────────────────────────────────────────────────────────────────────────────
# 2. HCP 명부 300인 — HCP-001~024는 v1 명부를 그대로 보존(기존 본문·데모 문서와의 정합),
#    HCP-025~300은 결정론적으로 생성한다. 기관명은 전부 가상, 도시는 실제 지명(지리 참조용).
# ──────────────────────────────────────────────────────────────────────────────

FIRST = [
    "Adaeze","Alastair","Anjali","Arvind","Bettina","Bram","Camila","Cormac","Dagmar","Darius",
    "Delphine","Eamon","Eloise","Esperanza","Fabian","Felicity","Gaspar","Gemma","Hadley","Hamish",
    "Ilse","Imani","Jaromir","Josefina","Kenji","Kiara","Lachlan","Leonie","Lukas","Mairead",
    "Malika","Mateo","Nadine","Niamh","Nikolai","Odalys","Orla","Pallavi","Quentin","Rasmus",
    "Renata","Rohan","Rosalind","Saoirse","Selin","Silvio","Sonali","Tadeo","Thandiwe","Tobias",
    "Ulrike","Valentina","Viraj","Wilhelmina","Xiomara","Yannick","Yesenia","Zubin","Anouk","Bastian",
]
LAST = [
    "Ashgrove","Bellweather","Brannigan","Calderwood","Chastain","Corliss","Danforth","Dellacroix","Eastmond","Ellingham",
    "Fairweather","Fenwicke","Galbraith","Ghiradelli","Halloway","Harkness","Inverness","Ivanetti","Jarreau","Kettleborn",
    "Kilbride","Lammermoor","Larkspur","Merriwether","Montclaire","Nashwood","Norrington","Oakhurst","Ostrander","Pemberton",
    "Quintrell","Ravenscroft","Rothsay","Sandoval-Reyes","Silverthorne","Stanhope","Thackeray","Thistlewood","Underhill","Vandergriff",
    "Vasquez-Lund","Wetherby","Whitmore","Wycliffe","Yarborough","Zabriskie","Adeyemi-Cole","Barrowman","Castellane","Dunmore",
    "Eversholt","Fitzgibbon","Grierson","Hollingsworth","Kirkpatrick","Lindenmuth","Marchetti","Nakagawa","Oyelaran","Prendergast",
    "Rusnak","Steinmetz","Tavernier","Voskuijlen","Wainwright","Yoshimura","Zeitler","Abernathy","Beauchamp","Cavanaugh",
]
INST_HEAD = [
    "Northbrook","Riverstone","Beacon Hill","Harborlight","Lakeshore","Cedar Ridge","Silver Creek","Bayview","Fox Hollow","Windrow",
    "Palmetto","Kestrel","Alder Point","Granite Bay","Marbury","Thornfield","Sable Creek","Highmoor","Juniper Flats","Willowmere",
    "Copperfield","Bluestem","Ironwood","Quarry Hill","Saltmarsh","Vantage Park","Ember Lake","Foxglove","Northgate","Sandhill",
]
INST_KIND = [
    "Neurology Institute","Epilepsy Center","Medical Group","Neuroscience Center","Neurology Associates",
    "Regional Epilepsy Program","Neurology Partners","Comprehensive Epilepsy Clinic","Neurological Care Center","Health Neurology",
]
CITIES = {
    "NORTHEAST": [("Albany","NY"),("Hartford","CT"),("Providence","RI"),("Portland","ME"),("Buffalo","NY"),("Worcester","MA"),
                  ("Allentown","PA"),("Burlington","VT"),("Trenton","NJ"),("Manchester","NH"),("Syracuse","NY"),("Scranton","PA")],
    "SOUTH":     [("Charleston","SC"),("Chattanooga","TN"),("Mobile","AL"),("Savannah","GA"),("Lexington","KY"),("Shreveport","LA"),
                  ("Fayetteville","NC"),("Jackson","MS"),("Roanoke","VA"),("Lakeland","FL"),("Waco","TX"),("Little Rock","AR")],
    "MIDWEST":   [("Madison","WI"),("Toledo","OH"),("Des Moines","IA"),("Wichita","KS"),("Fort Wayne","IN"),("Duluth","MN"),
                  ("Peoria","IL"),("Grand Rapids","MI"),("Omaha","NE"),("Springfield","MO"),("Akron","OH"),("Sioux Falls","SD")],
    "WEST":      [("Oakland","CA"),("Boise","ID"),("Tucson","AZ"),("Eugene","OR"),("Spokane","WA"),("Reno","NV"),
                  ("Fort Collins","CO"),("Bakersfield","CA"),("Santa Fe","NM"),("Missoula","MT"),("Provo","UT"),("Tacoma","WA")],
}
ROLE_CODE_V3 = {"ACADEMIC": "RSM", "COMMUNITY": "RSM", "PRIVATE_PRACTICE": "AR", "GENERAL": "AR"}


def build_roster(legacy_hcps):
    """HCP-001~024는 legacy 그대로, 025~300은 결정론 생성. → {ref: (name, spec, region, setting, inst, city_st)}"""
    roster = dict(legacy_hcps)
    rng = random.Random(20260821)
    used_names = {v[0] for v in legacy_hcps.values()}
    combos = [(f, l) for f in FIRST for l in LAST]
    rng.shuffle(combos)
    # 지역·전문과·세팅 가중 분포 (현실적 구성 — docs/03 §1)
    regions = (["NORTHEAST"] * 28 + ["SOUTH"] * 26 + ["MIDWEST"] * 23 + ["WEST"] * 23)
    specs = (["NEUROLOGY"] * 55 + ["EPILEPTOLOGY"] * 30 + ["PSYCHIATRY"] * 8 + ["GENERAL"] * 7)
    settings = (["COMMUNITY"] * 45 + ["ACADEMIC"] * 30 + ["PRIVATE_PRACTICE"] * 25)
    ci = 0
    for n in range(len(legacy_hcps) + 1, N_HCP + 1):
        while True:
            f, l = combos[ci]; ci += 1
            name = f"{f} {l}"
            if name not in used_names:
                used_names.add(name)
                break
        region = regions[(n * 7) % len(regions)]
        spec = specs[(n * 11) % len(specs)]
        setting = settings[(n * 13) % len(settings)]
        # 전문과·세팅 정합: EPILEPTOLOGY는 개인의원 비중을 낮춘다
        if spec == "EPILEPTOLOGY" and setting == "PRIVATE_PRACTICE" and n % 3 != 0:
            setting = "ACADEMIC"
        if spec in ("PSYCHIATRY", "GENERAL") and setting == "ACADEMIC" and n % 2 == 0:
            setting = "COMMUNITY"
        inst = f"{INST_HEAD[(n * 17) % len(INST_HEAD)]} {INST_KIND[(n * 19) % len(INST_KIND)]}"
        city, st = CITIES[region][(n * 23) % len(CITIES[region])]
        roster[f"HCP-{n:03d}"] = (name, spec, region, setting, inst, f"{city}, {st}")
    return roster


# ──────────────────────────────────────────────────────────────────────────────
# 3. 학회 (실제 명칭 — 08/21 팀 결정)
#    안전 규칙: **연례 개최가 확실한 미국 학회 3곳만** 쓴다(격년 학회의 연도 짝을 틀리면 그 자체로
#    허위 기록이 된다). 이름·연도·개최 월까지만 쓰고 **개최 도시·세션 번호·발표 데이터는 쓰지 않는다.**
#    문서 내용은 우리 MSL이 현장에서 나눈 (가상) 대화뿐 — 학회가 발표한 내용을 재현하지 않는다.
# ──────────────────────────────────────────────────────────────────────────────

CONGRESS_EVENTS = [
    # (abbrev, 공식 명칭, year, month, 보고서 수)
    ("AES", "American Epilepsy Society Annual Meeting", 2021, 12, 1),
    ("AES", "American Epilepsy Society Annual Meeting", 2022, 12, 2),
    ("AES", "American Epilepsy Society Annual Meeting", 2023, 12, 2),
    ("AES", "American Epilepsy Society Annual Meeting", 2024, 12, 2),
    ("AES", "American Epilepsy Society Annual Meeting", 2025, 12, 3),
    ("AAN", "American Academy of Neurology Annual Meeting", 2021, 4, 1),
    ("AAN", "American Academy of Neurology Annual Meeting", 2022, 4, 1),
    ("AAN", "American Academy of Neurology Annual Meeting", 2023, 4, 1),
    ("AAN", "American Academy of Neurology Annual Meeting", 2024, 4, 1),
    ("AAN", "American Academy of Neurology Annual Meeting", 2025, 4, 2),
    ("AAN", "American Academy of Neurology Annual Meeting", 2026, 4, 2),
    ("ANA", "American Neurological Association Annual Meeting", 2022, 10, 1),
    ("ANA", "American Neurological Association Annual Meeting", 2023, 9, 1),
    ("ANA", "American Neurological Association Annual Meeting", 2024, 9, 1),
    ("ANA", "American Neurological Association Annual Meeting", 2025, 9, 1),
]

CONGRESS_NOTICE = (
    "[CONFERENCE REFERENCE] The meeting named above is a real, publicly announced scientific congress and is "
    "used here only as the setting of this fictional record. No session content, abstract, poster, or presented "
    "data from that meeting is reproduced or paraphrased; every person and conversation below is invented."
)

# ──────────────────────────────────────────────────────────────────────────────
# 4. 신호 문장 풀 — frame × detail 조합. 조각은 전부 손으로 썼다.
#    성별 대명사 없음 / 용량 수치 없음 / Development는 "공백"으로만.
# ──────────────────────────────────────────────────────────────────────────────

S1_FRAMES = [
    "Raised, without any prompting, {d}",
    "Came back again to {d}",
    "Described {d}",
    "Spent most of the conversation on {d}",
    "Volunteered {d}",
    "Asked me to carry back internally {d}",
    "Kept returning to {d}",
    "Framed the biggest gap in this panel as {d}",
    "Brought up, unprompted, {d}",
    "Said the hardest conversations in clinic are about {d}",
    "Flagged {d}",
    "Noted with some frustration {d}",
    "Wanted it on the record that {d}",
    "Opened the visit with {d}",
]
S1_DETAILS = [
    "the adolescents with drug-resistant focal seizures who simply wait until 18 before cenobamate is an option",
    "a 16-year-old who failed two medications and has nothing new available until adulthood",
    "the transition-age group, where the adult-only label leaves families without an on-label answer",
    "a running list of 15- and 16-year-olds with refractory focal seizures and no approved path",
    "the 12-to-17 population, described as the place where the treatment gap is widest",
    "two teenage patients still seizing after multiple medications, with the label closing the door until 18",
    "how uncomfortable it feels to park adolescent refractory cases until a birthday",
    "families asking why data below 18 does not exist yet",
    "a 17-year-old whose regimen is clearly failing while the approved options are exhausted",
    "the steady trickle of drug-resistant teenagers for whom nothing on label has changed",
    "adolescent refractory focal epilepsy as an unmet need that keeps appearing in this clinic",
    "the wait-until-18 pattern, called an uncomfortable way to practice",
    "referrals of teenagers with drug-resistant seizures arriving faster than the options do",
    "the gap between what these adolescent patients need and what the label permits",
]
S7_FRAMES = [
    "Raised, unprompted, {d}",
    "Described {d}",
    "Kept coming back to {d}",
    "Said the clearest limitation right now is {d}",
    "Volunteered {d}",
    "Asked that internal teams hear about {d}",
    "Noted {d}",
    "Framed it as {d}",
    "Brought up {d}",
    "Wanted to register {d}",
    "Spent the last part of the visit on {d}",
    "Flagged, more than once, {d}",
]
S7_DETAILS = [
    "the patients with generalized tonic-clonic seizures for whom this option is simply not available",
    "how well it works in focal epilepsy and how little that helps the generalized patients in this panel",
    "a group of primary generalized patients with nothing comparable to offer",
    "the absence of an approved route for generalized tonic-clonic seizures despite similar refractoriness",
    "several patients whose seizures are generalized rather than focal, and therefore out of scope",
    "the frustration of having a well-tolerated option that the generalized population cannot access",
    "convulsive generalized seizures as the population left out of the current indication",
    "patients with generalized tonic-clonic seizures who cycle through the same medications with the same result",
    "the mismatch between the focal-only indication and the generalized cases filling this clinic",
    "a subset of generalized epilepsy patients for whom the shelf is effectively empty",
    "how often the generalized tonic-clonic group comes up with no approved answer",
    "the generalized patients who would be candidates on every criterion except the indication",
]
S8_FRAMES = [
    "Raised {d}",
    "Described {d}",
    "Brought up, unprompted, {d}",
    "Noted {d}",
    "Asked whether anything is moving for {d}",
    "Spent time on {d}",
    "Flagged {d}",
    "Said the hardest population in this practice is {d}",
    "Wanted to record {d}",
    "Returned to {d}",
]
S8_DETAILS = [
    "the Lennox-Gastaut patients whose drop attacks continue on every combination tried",
    "Lennox-Gastaut syndrome, where the available regimens have plainly run out",
    "a Lennox-Gastaut case with multiple seizure types and no remaining approved option",
    "the drop-attack burden in Lennox-Gastaut patients and how little the current shelf offers",
    "Lennox-Gastaut syndrome as the population where this clinic has the least to work with",
    "several Lennox-Gastaut patients on four or more medications with unchanged seizure counts",
    "the multi-seizure-type patients under a Lennox-Gastaut diagnosis for whom nothing is approved here",
    "how families of Lennox-Gastaut patients keep asking what else exists",
    "Lennox-Gastaut cases where every approved combination has already been exhausted",
    "the gap for Lennox-Gastaut patients, described as the most difficult conversation in this clinic",
]
S6_FRAMES = [
    "The main hesitation is {d}",
    "Said the barrier in older adults is {d}",
    "Described {d}",
    "Explained that {d}",
    "Keeps coming back to {d}",
    "Noted {d}",
    "Raised {d}",
    "Called it {d}",
    "The reluctance here is {d}",
    "Spent the visit on {d}",
]
S6_DETAILS = [
    "drug-drug interactions on top of already long medication lists in patients over 65",
    "the interaction checks required before starting anyone elderly, which slow the decision down",
    "the burden of slow titration for older patients and their caregivers",
    "concomitant medication review in geriatric patients as the step that stalls every start",
    "waiting for a pharmacist to clear the full medication list in patients over 65",
    "titration in geriatric patients as a second job for caregivers",
    "polypharmacy in older adults as the reason starts get deferred rather than declined",
    "interaction concerns in the elderly panel, which is most of this practice",
    "the time cost of interaction review in older patients, rather than any doubt about efficacy",
    "how the medication list in patients over 65 makes the whole decision feel heavier",
]
S3_FRAMES = [
    "Asked whether anyone is looking at {d}",
    "Brought up {d}",
    "Described {d}",
    "Raised {d}",
    "Noted {d}",
    "Wanted to know about {d}",
    "Keeps seeing {d}",
    "Flagged {d}",
]
S3_DETAILS = [
    "post-stroke epilepsy, since referrals for seizures after stroke keep rising here",
    "a growing cluster of post-stroke epilepsy patients who fit none of the usual categories",
    "post-stroke seizures as an overlooked population in every registry reviewed so far",
    "seizures after stroke, and what evidence exists for this population",
    "post-stroke epilepsy patients, now a visible share of new referrals",
    "the post-stroke epilepsy group, described as sitting outside the usual buckets",
    "epilepsy following stroke, and whether it is being studied separately at all",
    "post-stroke epilepsy, which this clinic sees more of every year",
]
S4_FRAMES = [
    "Asked for {d}",
    "Requested {d}",
    "Closed by asking for {d}",
    "Action item: {d}",
    "Wants {d}",
    "Asked me to send {d}",
    "Follow-up requested — {d}",
    "Would like {d}",
    "Open request from this visit: {d}",
    "Asked whether I could bring {d}",
]
S4_DETAILS_Y = [
    "whatever adolescent dosing or safety material exists, published or pending",
    "a literature package on patients under 18, even early-phase work",
    "confirmation of whether any adolescent safety data is available yet",
    "anything shareable on the under-18 population",
    "published pharmacokinetic work in adolescents, if any exists",
]
S4_DETAILS_E = [
    "a concise interaction summary for elderly patients on several concomitant medications",
    "interaction and titration guidance for patients over 65",
    "the drug-drug interaction table for geriatric polypharmacy cases",
    "caregiver-facing education material for older patients",
    "a shorter interaction reference that intake staff could work from",
    "something the clinic pharmacist could use when clearing older patients",
    "a one-page interaction reference for the geriatric panel",
    "titration guidance written for caregivers rather than clinicians",
    "whatever exists on managing long medication lists in older adults",
    "material the nursing staff could hand to families of older patients",
    "a summary of interaction considerations for the over-65 group",
]
S4_DETAILS_G = [
    "whatever literature exists on generalized tonic-clonic populations",
    "any published material covering generalized seizure types",
    "references on the generalized tonic-clonic population, if available",
]
S5_FRAMES = [
    "Shared that {d}",
    "Volunteered that {d}",
    "Mentioned {d}",
    "Reported {d}",
    "Wanted to pass along that {d}",
    "Noted {d}",
    "Took a moment to say that {d}",
    "Offered, unprompted, that {d}",
    "Was pleased to report that {d}",
    "Passed along that {d}",
]
S5_DETAILS = [
    "two refractory adults who had failed several medications are now months into markedly fewer seizures",
    "the longest-standing refractory patient in this panel has had the quietest stretch in years",
    "several drug-resistant adults finally responded after years of cycling medications",
    "a treatment-resistant adult went from weekly seizures to rare breakthroughs",
    "another refractory adult is holding steady on the current regimen",
    "a drug-resistant adult has stayed seizure-free longer than at any point in the chart",
    "a long-refractory adult has been able to return to driving after a sustained quiet period",
    "one adult who had exhausted the usual combinations is now doing markedly better",
    "a patient with years of uncontrolled seizures has had a genuinely uneventful quarter",
    "two adults in the refractory group are reporting fewer breakthrough events than before",
    "a difficult adult case has been stable long enough that the family noticed first",
]
S2_FRAMES = [
    "Also mentioned {d}",
    "Raised {d}",
    "Noted {d}",
    "Reported {d}",
    "Brought up {d}",
]
S2_DETAILS = [
    "an adult patient describing persistent dizziness after the last titration step",
    "one adult reporting daytime somnolence heavy enough to affect the commute",
    "an adult who stopped unprompted after a week of feeling foggy and unusually sleepy",
    "a patient with a rash-like eruption that is being watched",
    "an adult complaining of unsteadiness since the dose increase",
    "one patient reporting fatigue that has not settled",
    "an adult describing double vision on the current step",
    "a patient with nausea since starting, now under observation",
]

# ──────────────────────────────────────────────────────────────────────────────
# 5. 노이즈 산문 엔진 — 조각 조합 (신호 없는 대부분의 블록을 채운다)
# ──────────────────────────────────────────────────────────────────────────────

SLOTS = {
    "dur": ["a short", "a rushed", "an unhurried", "a brief", "a full", "a compressed", "a twenty-minute",
            "an unexpectedly long", "a clipped", "a half-hour", "a fragmented", "a productive"],
    "place": ["in the back office", "in the corridor", "between clinic blocks", "in the reading room",
              "at the nurses' station", "over a quick coffee", "in the conference room", "in the workroom",
              "outside the EEG suite", "at the end of the clinic list", "in the shared office", "by the scheduling desk"],
    "sys": ["the scheduling system", "the referral intake process", "the new charting templates",
            "the prior-authorization workflow", "the phone triage line", "the patient portal"],
    "staff": ["two medical assistants", "a front-desk coordinator", "one of the nurse practitioners",
              "the epilepsy fellow", "a rotating resident", "the clinic pharmacist"],
    "admin_state": ["is still being sorted out", "changed again last month", "has not settled",
                    "is being piloted this quarter", "went live without much warning"],
    "backlog": ["the new-patient backlog", "routine follow-up slots", "the referral queue", "clinic throughput"],
    "trend": ["has stretched out", "is slowly recovering", "keeps slipping", "looks better than last year"],
    "panel": ["the older half of the panel", "the refractory group", "newly referred patients",
              "the pediatric-to-adult transfers", "long-standing patients", "the surgical workup list"],
    "topic_lit": ["a review that circulated on the service", "a session summary from a colleague",
                  "a guideline update discussed at journal club", "a case series someone forwarded"],
    "vague": ["nothing that needed follow-up", "no specific request", "nothing actionable this visit",
              "no materials requested", "no product discussion"],
    "meet": ["the next visit", "a call later this month", "the following quarter", "a follow-up appointment"],
    "cover": ["coverage paperwork", "formulary questions", "benefit checks", "the appeals process"],
    "cover_state": ["takes longer than the clinical decision", "varies by payer", "is handled by one person here",
                    "has improved somewhat", "remains the slowest step"],
}

TEMPLATES = {
    "open": [
        "{dur} conversation {place}, mostly logistics.",
        "{dur} visit {place}; the schedule was tight.",
        "Caught {dur} window {place} between patients.",
        "{dur} meeting {place}, first one this quarter.",
        "Stopped by {place} for {dur} conversation.",
    ],
    "admin": [
        "{sys} {admin_state}, and that took up the first part of the conversation.",
        "The practice lost {staff} and has not backfilled, so {backlog} {trend}.",
        "{backlog} {trend} since the summer, which shapes how much time there is for anything else.",
        "Most of the discussion was about {sys}, which {admin_state}.",
        "Onboarding {staff} is the current preoccupation here.",
        "Asked about my travel schedule, since visits keep landing on the busiest clinic days.",
    ],
    "clinical_general": [
        "Talked through {panel} in general terms, without any specific case.",
        "The composition of {panel} has shifted over the last year or two.",
        "Described how {panel} is triaged now compared with before.",
        "Referral patterns into this clinic have changed, and {panel} is a bigger share than it was.",
        "Spent some time on {panel} and how workup decisions get sequenced.",
    ],
    "titration": [
        "Titration habits came up in general terms; no specifics were discussed and none were offered.",
        "Described a preference for slower titration in general, unrelated to any particular patient.",
        "Monitoring intervals during titration are set by clinic routine here rather than by protocol.",
        "Titration scheduling is handled by nursing staff, which the practice finds workable.",
    ],
    "access": [
        "{cover} {cover_state}, which came up as a general frustration.",
        "Noted that {cover} {cover_state} and that this is not specific to any one product.",
        "Benefit verification is the step that most often delays a start here.",
    ],
    "lit": [
        "Mentioned {topic_lit} but did not raise any specific finding.",
        "Referenced {topic_lit} in passing.",
        "Asked whether I had seen {topic_lit}; I had not, and offered nothing in return.",
    ],
    "congress_talk": [
        "Asked whether I would be at the meeting later this year.",
        "Compared notes on which sessions were worth the time.",
        "The travel schedule this year came up, and little else.",
        "Mostly small talk about the program and the venue.",
    ],
    "congress_floor": [
        "Caught between sessions in the poster hall; the conversation was short and entirely unprompted.",
        "Stopped to talk on the way out of a session block, with no agenda on either side.",
        "A hallway conversation during the afternoon break.",
        "Approached me rather than the other way around, which is worth noting.",
        "We spoke standing near the exhibit aisles, briefly.",
        "The conversation happened while waiting for a session room to clear.",
        "Introduced by a colleague from the same region and talked for a few minutes.",
        "A short exchange over the coffee queue.",
    ],
    "early_product": [
        "This practice is still building familiarity with the product and had no clinical points to raise.",
        "Described the practice as early in its experience here, with nothing to report yet.",
        "Formulary placement was the only product-adjacent topic, and only in general terms.",
    ],
    "close": [
        "Agreed to reconnect at {meet}; {vague}.",
        "{vague}. Safety items asked about and confirmed none.",
        "Closed there — {vague}.",
        "Left it at that, with {meet} to be scheduled.",
        "{vague} this time. Asked about safety and confirmed nothing to report.",
    ],
}

TERSE_SUB = [(" the ", " "), (" a ", " "), ("patients", "pts"), ("patient", "pt"),
             ("follow-up", "f/u"), ("appointment", "appt"), ("conversation", "convo")]
TYPOS = [("the", "teh"), ("and", "adn"), ("with", "wtih"), ("going", "goign"), ("forward", "foward"),
         ("because", "becuase"), ("received", "recieved")]


def _fill(t, rng):
    out = t
    for k, opts in SLOTS.items():
        tok = "{" + k + "}"
        while tok in out:
            out = out.replace(tok, rng.choice(opts), 1)
    return out[0].upper() + out[1:] if out else out


def _era(date):
    y = int(date[:4])
    if y <= 2022:
        return "early"
    return "mid" if y <= 2024 else "recent"


def noise_sentences(rng, date, n, style, congress=False):
    """신호 없는 문장 n개. 시기에 따라 주제 풀이 달라지고(초기엔 제품 익숙해지는 얘기),
    오프너는 60%만 붙인다 — 모든 블록이 같은 형태로 시작하면 생성물처럼 보인다."""
    era = _era(date)
    pools = ["admin", "clinical_general", "access", "lit", "close"]
    if congress:
        pools += ["congress_talk", "lit", "clinical_general"]
    else:
        pools += ["congress_talk", "admin"]
    if era == "early":
        pools += ["early_product", "titration"]
    else:
        pools += ["titration", "clinical_general"]
    picks = []
    used = set()
    head = ["congress_floor"] if congress else (["open"] if rng.random() < 0.6 else [])
    k = min(len(pools), max(1, n - len(head)))
    order = head + rng.sample(pools, k=k)
    for topic in order[:n]:
        cand = [t for t in TEMPLATES[topic] if t not in used]
        if not cand:
            cand = TEMPLATES[topic]
        t = rng.choice(cand)
        used.add(t)
        picks.append(_fill(t, rng))
    if style == "terse":
        picks = [_terse(s, rng) for s in picks]
    if rng.random() < 0.05:
        picks = [_typo(s, rng) for s in picks]
    return picks


def _terse(s, rng):
    for a, b in TERSE_SUB:
        if rng.random() < 0.5:
            s = s.replace(a, b)
    return s


def _typo(s, rng):
    for a, b in TYPOS:
        if f" {a} " in s:
            return s.replace(f" {a} ", f" {b} ", 1)
    return s


# ──────────────────────────────────────────────────────────────────────────────
# 6. 각본 조립 — 문서 골격 → 신호 수요 → HCP·신호 배정 → 본문 생성
# ──────────────────────────────────────────────────────────────────────────────

def _mk(sid, stype, seg, barrier, text):
    return {"signal_id": sid, "signal_type": stype, "patient_segment": seg,
            "barrier_type": barrier, "verbatim": text}


_SEEN = set()   # 모든 신호 풀이 공유하는 중복 방지 집합 (verbatim 전역 유일)


def _variants(frames, details, n, rng, mk, seen=None):
    """frame × detail 조합에서 서로 다른 문장 n개.
    seen을 공유하면 여러 풀(S2·S2_co 등)이 같은 조각을 써도 문장이 겹치지 않는다 — verbatim 전역 유일."""
    combos = [(f, d) for f in frames for d in details]
    rng.shuffle(combos)
    seen = seen if seen is not None else _SEEN
    out = []
    for f, d in combos:
        t = f.replace("{d}", d)
        t = t if t.endswith(".") else t + "."
        if t in seen:
            continue
        seen.add(t)
        out.append(mk(t))
        if len(out) == n:
            break
    assert len(out) == n, f"조합 부족: {len(out)}/{n} (조합 {len(combos)}개)"
    return out


# 동거 신호 수 — S1 단위에 얹는 S4(청소년 자료요청) 9건·S2(AE) 5건, S7 단위에 얹는 S4(PGTC 문헌) 6건.
# 이 건수는 아래 TARGETS의 총량에 포함되므로 신규 배정 시 차감한다.
CO_LOCATED = {"S2": 5, "S4": 15}

# 목표 분포 (docs/03 §2 v3) — (신호, 건수, 독립 HCP, 최소 권역)
# S2·S4는 동거 배치 때문에 독립 HCP가 목표 이상이 된다 → 검증기는 "이상"으로 확인한다.
TARGETS = {
    "S1": (52, 34, 4),
    "S6": (41, 27, 4),
    "S7": (34, 23, 4),
    "S8": (21, 15, 3),
    "S3": (19, 14, 4),
    "S5": (38, 24, 4),
    "S2": (27, 22, 4),
    "S4": (47, 30, 4),
}

MONTHS = []
_y, _m = 2021, 1
while (_y, _m) <= (2026, 8):
    MONTHS.append(f"{_y:04d}-{_m:02d}")
    _m += 1
    if _m == 13:
        _y, _m = _y + 1, 1


def build_plan(roster, legacy_docs, legacy_planted, legacy_voice_sigs):
    """
    legacy_docs: v1 DOC_PLAN (63건) — 키·날짜·기존 블록 HCP·손으로 쓴 본문을 보존한다.
    legacy_voice_sigs: [(doc_key, signal_id)] — 고정 KO 대본에 심긴 신호 (PLANTED 밖에서 관리됨)
    legacy 신호는 목표 총량에서 **차감**한다 — 최종 건수·독립 HCP가 docs/03 §2의 값과 정확히 맞아야 한다.
    반환: (doc_plan, planted, gen_bodies, congress_meta, stats)
    """
    rng = random.Random(20210101)

    # legacy 신호 집계 (건수 + 독립 HCP)
    legacy_hcp_of = {}
    for k, plist in legacy_planted.items():
        dk, bi = k
        d = next((x for x in legacy_docs if x[0] == dk), None)
        if d and bi <= len(d[4]):
            legacy_hcp_of[k] = d[4][bi - 1]
    leg_cnt, leg_hcps = {}, {}
    for k, plist in legacy_planted.items():
        for p in plist:
            sid = p["signal_id"] if p["signal_id"] in TARGETS else ("X" if p["signal_id"].startswith("X") else p["signal_id"])
            leg_cnt[sid] = leg_cnt.get(sid, 0) + 1
            if k in legacy_hcp_of:
                leg_hcps.setdefault(sid, set()).add(legacy_hcp_of[k])
    for dk, sid in legacy_voice_sigs:
        leg_cnt[sid] = leg_cnt.get(sid, 0) + 1
        d = next((x for x in legacy_docs if x[0] == dk), None)
        if d:
            leg_hcps.setdefault(sid, set()).add(d[4][0])

    # ── 6.1 문서 골격 ────────────────────────────────────────────────────────
    docs = []          # {key, source_type, date, authors, n_blocks, hcps[], body_alias}
    legacy_by_key = {d[0]: d for d in legacy_docs}

    def author_for(date, style_pref=None):
        cand = [a for a, v in MSL_V3.items() if v["active"][0] <= date[:7] <= v["active"][1]]
        if style_pref:
            pref = [a for a in cand if MSL_V3[a]["style"] == style_pref]
            if pref:
                cand = pref
        return rng.choice(cand)

    # (a) 하이라이트 60건 — 기존 12건 유지(블록 8~14로 확장) + 신규 48건
    hl_months = [m for m in MONTHS if m not in ("2021-01", "2021-07", "2022-08", "2023-08", "2024-07", "2025-08")]
    legacy_hl = [k for k in legacy_by_key if k.startswith("H")]
    used_months = {legacy_by_key[k][2][:7] for k in legacy_hl}
    free_months = [m for m in hl_months if m not in used_months]
    rng.shuffle(free_months)
    for k in sorted(legacy_hl):
        _, st, date, authors, hcps = legacy_by_key[k]
        docs.append({"key": k, "source_type": st, "date": date, "authors": authors,
                     "n_blocks": rng.randint(9, 14), "fixed_hcps": list(hcps), "body_alias": k})
    for i, m in enumerate(sorted(free_months[:48]), start=1):
        d = f"{m}-{rng.choice(['09','10','11','12','13','14','15'])}"
        docs.append({"key": f"HX{i:02d}", "source_type": "HIGHLIGHT_DOC", "date": d,
                     "authors": [author_for(d), author_for(d)],
                     "n_blocks": rng.randint(8, 14), "fixed_hcps": [], "body_alias": None})

    # (b) 학회 22건 — 실제 학회 이벤트에 배정. 기존 C01~C03은 날짜가 맞는 실제 학회로 재지정.
    slots = []
    for ab, full, y, mo, cnt in CONGRESS_EVENTS:
        for j in range(cnt):
            slots.append((ab, full, y, mo, j))
    legacy_cong = {"C01": ("AES", 2025, 12), "C02": ("AAN", 2026, 4), "C03": ("AAN", 2026, 4)}
    congress_meta = {}
    taken = set()
    for k, (ab, y, mo) in legacy_cong.items():
        idx = next(i for i, s in enumerate(slots) if s[0] == ab and s[2] == y and s[3] == mo and i not in taken)
        taken.add(idx)
        ab_, full, y_, mo_, _ = slots[idx]
        date = f"{y_:04d}-{mo_:02d}-{rng.choice(['05','06','12','17','19'])}"
        docs.append({"key": k, "source_type": "CONGRESS_REPORT", "date": date,
                     "authors": legacy_by_key[k][3], "n_blocks": rng.randint(6, 12),
                     "fixed_hcps": list(legacy_by_key[k][4]), "body_alias": k})
        congress_meta[k] = (ab_, full, y_, mo_)
    ci = 0
    for i, s in enumerate(slots):
        if i in taken:
            continue
        ci += 1
        ab, full, y, mo, _ = s
        date = f"{y:04d}-{mo:02d}-{rng.choice(['04','05','06','11','12','13','18','19'])}"
        key = f"CX{ci:02d}"
        docs.append({"key": key, "source_type": "CONGRESS_REPORT", "date": date,
                     "authors": [author_for(date)], "n_blocks": rng.randint(6, 12),
                     "fixed_hcps": [], "body_alias": None})
        congress_meta[key] = (ab, full, y, mo)

    # (c) 단일 면담형 — 기존 유지 + 신규. 최근 구간에 약간 더 무게를 준다.
    def scatter(n, prefix, stype, existing, lang_ko=False):
        for k in sorted(existing):
            _, st, date, authors, hcps = legacy_by_key[k]
            docs.append({"key": k, "source_type": st, "date": date, "authors": authors,
                         "n_blocks": 1, "fixed_hcps": list(hcps), "body_alias": k})
        pool = MONTHS + MONTHS[-24:]          # 최근 2년 가중
        for i in range(1, n + 1):
            m = pool[(i * 37) % len(pool)]
            d = f"{m}-{rng.choice(['02','05','08','11','14','17','20','23','26'])}"
            docs.append({"key": f"{prefix}{i:03d}", "source_type": stype, "date": d,
                         "authors": [author_for(d)], "n_blocks": 1, "fixed_hcps": [], "body_alias": None})

    scatter(95, "MX", "MEETING_NOTE", [k for k in legacy_by_key if k.startswith("M")])
    scatter(45, "PX", "CALL_NOTE", [k for k in legacy_by_key if k.startswith("P")])
    scatter(35, "EX", "EMAIL_SUMMARY", [k for k in legacy_by_key if k.startswith("E")])
    scatter(15, "VX", "VOICE_TRANSCRIPT", [k for k in legacy_by_key if k.startswith("V")], lang_ko=True)

    # 미래 날짜 금지 — 마지막 달(2026-08)은 오늘(21일) 이전으로 고정한다
    for i, d in enumerate(docs):
        if d["date"] > LAST_DAY:
            d["date"] = f"2026-08-{[3, 5, 7, 10, 12, 14, 17, 18][i % 8]:02d}"
    docs.sort(key=lambda d: (d["date"], d["key"]))

    # ── 6.2 신호 수요 만들기 (코호트 → 건수 배분) ──────────────────────────
    by_region = {}
    for ref, v in roster.items():
        by_region.setdefault(v[2], []).append(ref)
    for r in by_region:
        by_region[r].sort()

    LEGACY_REFS = {f"HCP-{i:03d}" for i in range(1, 25)}

    def cohort(size, min_regions, seed_off, exclude):
        """legacy HCP와 이미 쓴 HCP를 제외하고 권역을 돌아가며 뽑는다."""
        r = random.Random(777 + seed_off)
        regions = sorted(by_region)
        picked = []
        i = 0
        guard = 0
        while len(picked) < size and guard < 100000:
            guard += 1
            reg = regions[i % len(regions)]
            pool = [h for h in by_region[reg] if h not in picked and h not in exclude and h not in LEGACY_REFS]
            if pool:
                picked.append(r.choice(pool))
            i += 1
        assert len(picked) == size, f"코호트 부족: {len(picked)}/{size}"
        return picked

    demands = []   # (hcp_ref, signal_id, recency_bias)
    cohorts = {}
    for off, (sid, (cnt, dhcp, minreg)) in enumerate(TARGETS.items()):
        need_cnt = cnt - leg_cnt.get(sid, 0) - CO_LOCATED.get(sid, 0)
        need_hcp = dhcp - len(leg_hcps.get(sid, set()))
        assert need_cnt >= need_hcp >= 1, f"{sid}: legacy 차감 후 목표 불가 ({need_cnt}/{need_hcp})"
        co = cohort(need_hcp, minreg, off, exclude=set())
        cohorts[sid] = co
        alloc = [1] * need_hcp
        for j in range(need_cnt - need_hcp):
            alloc[j % need_hcp] += 1
        bias = 0.75 if sid in ("S7", "S8") else (0.6 if sid == "S1" else 0.4)
        for h, a in zip(co, alloc):
            for _ in range(a):
                demands.append((h, sid, bias))
    n_x = 4 - leg_cnt.get("X", 0)
    for i in range(max(0, n_x)):
        demands.append((cohorts["S5"][i], "X", 0.5))

    # ── 6.3 슬롯에 HCP·신호 배정 ────────────────────────────────────────────
    slots_all = []
    for d in docs:
        for bi in range(1, d["n_blocks"] + 1):
            fixed = d["fixed_hcps"][bi - 1] if bi <= len(d["fixed_hcps"]) else None
            slots_all.append({"doc": d, "bi": bi, "hcp": fixed, "sig": []})
    total_slots = len(slots_all)

    # 신호는 legacy 고정 블록에 얹지 않는다 (손으로 쓴 본문에 이미 신호가 있거나 없다)
    open_slots = [s for s in slots_all if s["hcp"] is None]
    recent_idx = {id(s): (MONTHS.index(s["doc"]["date"][:7]) / (len(MONTHS) - 1)) for s in open_slots}
    doc_hcps = {}
    for s in slots_all:
        if s["hcp"]:
            doc_hcps.setdefault(s["doc"]["key"], set()).add(s["hcp"])

    rng2 = random.Random(999)
    rng2.shuffle(open_slots)
    for hcp, sid, bias in demands:
        # 최근 가중: bias가 높으면 후반 구간 슬롯을 먼저 고른다
        cand = [s for s in open_slots
                if s["hcp"] is None and hcp not in doc_hcps.get(s["doc"]["key"], set())]
        if not cand:
            continue
        cand.sort(key=lambda s: -(recent_idx[id(s)] * bias + rng2.random() * (1 - bias)))
        s = cand[0]
        s["hcp"] = hcp
        s["sig"].append(sid)
        doc_hcps.setdefault(s["doc"]["key"], set()).add(hcp)

    # 동거 신호: S1 단위 일부에 S4(청소년 자료요청)·S2(AE)를 얹어 현실감을 준다
    s1_slots = [s for s in slots_all if "S1" in s["sig"]]
    for s in s1_slots[:9]:
        s["sig"].append("S4y_co")
    for s in s1_slots[9:14]:
        s["sig"].append("S2_co")
    s7_slots = [s for s in slots_all if "S7" in s["sig"]]
    for s in s7_slots[:6]:
        s["sig"].append("S4g_co")

    # 남은 슬롯에 HCP 배정 (신호 없는 노이즈 블록)
    all_refs = sorted(roster)
    doc_firsts = {}
    for s in slots_all:
        if s["hcp"]:
            doc_firsts.setdefault(s["doc"]["key"], set()).add(roster[s["hcp"]][0].split()[0])
    for s in slots_all:
        if s["hcp"]:
            continue
        used = doc_hcps.setdefault(s["doc"]["key"], set())
        firsts = doc_firsts.setdefault(s["doc"]["key"], set())
        for _ in range(120):
            h = all_refs[rng2.randrange(len(all_refs))]
            if h not in used and roster[h][0].split()[0] not in firsts:
                s["hcp"] = h
                break
        else:
            s["hcp"] = next(h for h in all_refs if h not in used)
        used.add(s["hcp"])
        firsts.add(roster[s["hcp"]][0].split()[0])

    # ── 6.4 신호 문장 실체화 ────────────────────────────────────────────────
    rs = random.Random(24680)
    _SEEN.clear()
    pools = {
        "S1": _variants(S1_FRAMES, S1_DETAILS, sum(1 for s in slots_all if "S1" in s["sig"]), rs,
                        lambda t: _mk("S1", "UNMET_NEED", "PEDIATRIC_TRANSITION", None, t)),
        "S7": _variants(S7_FRAMES, S7_DETAILS, sum(1 for s in slots_all if "S7" in s["sig"]), rs,
                        lambda t: _mk("S7", "UNMET_NEED", "GENERALIZED_PGTC", None, t)),
        "S8": _variants(S8_FRAMES, S8_DETAILS, sum(1 for s in slots_all if "S8" in s["sig"]), rs,
                        lambda t: _mk("S8", "UNMET_NEED", "LGS", None, t)),
        "S6": _variants(S6_FRAMES, S6_DETAILS, sum(1 for s in slots_all if "S6" in s["sig"]), rs,
                        lambda t: _mk("S6", "TREATMENT_BARRIER", "ELDERLY_65_PLUS", "DDI_CONCERN", t)),
        "S3": _variants(S3_FRAMES, S3_DETAILS, sum(1 for s in slots_all if "S3" in s["sig"]), rs,
                        lambda t: _mk("S3", "UNMET_NEED", "UNSPECIFIED", None, t)),
        "S5": _variants(S5_FRAMES, S5_DETAILS, sum(1 for s in slots_all if "S5" in s["sig"]), rs,
                        lambda t: _mk("S5", "POSITIVE_OUTCOME", "DRE_2PLUS", None, t)),
        "S2": _variants(S2_FRAMES, S2_DETAILS, sum(1 for s in slots_all if "S2" in s["sig"]), rs,
                        lambda t: _mk("S2", "SAFETY_CANDIDATE", "UNSPECIFIED", None, t)),
        "S2_co": _variants(S2_FRAMES, S2_DETAILS, 5, rs,
                           lambda t: _mk("S2", "SAFETY_CANDIDATE", "UNSPECIFIED", None, t)),
        "S4": _variants(S4_FRAMES, S4_DETAILS_E, sum(1 for s in slots_all if "S4" in s["sig"]), rs,
                        lambda t: _mk("S4", "INFO_REQUEST", "ELDERLY_65_PLUS", None, t)),
        "S4y_co": _variants(S4_FRAMES, S4_DETAILS_Y, 9, rs,
                            lambda t: _mk("S4", "INFO_REQUEST", "PEDIATRIC_TRANSITION", None, t)),
        "S4g_co": _variants(S4_FRAMES, S4_DETAILS_G, 6, rs,
                            lambda t: _mk("S4", "INFO_REQUEST", "GENERALIZED_PGTC", None, t)),
        "X": [_mk("X3", "CRITIC_BAIT", None, None,
                  "Put it as strongly as saying the age limit is the only thing standing in the way for these families."),
              _mk("X4", "CRITIC_BAIT", None, None,
                  "Said flatly that there is no patient group this would not help."),
              ],
    }
    cursor = {k: 0 for k in pools}
    planted = {}
    for s in slots_all:
        if not s["sig"]:
            continue
        out = []
        for sid in s["sig"]:
            p = pools[sid][cursor[sid]]
            cursor[sid] += 1
            out.append(p)
        planted[(s["doc"]["key"], s["bi"])] = out

    # legacy PLANTED 병합 (손으로 쓴 본문에 이미 들어있는 신호 문장)
    for k, v in legacy_planted.items():
        planted.setdefault(k, [])
        planted[k] = list(v) + planted.get(k, [])

    # ── 6.5 문서 최종형 + 생성 본문 ────────────────────────────────────────
    doc_plan, gen_bodies = [], {}
    for d in docs:
        hcps = [s["hcp"] for s in sorted([s for s in slots_all if s["doc"] is d], key=lambda x: x["bi"])]
        doc_plan.append((d["key"], d["source_type"], d["date"], d["authors"], hcps))
        alias = d["body_alias"]
        for bi in range(1, d["n_blocks"] + 1):
            has_legacy = alias and bi <= len(legacy_by_key.get(alias, ("", "", "", "", []))[4])
            if has_legacy:
                continue      # 손으로 쓴 본문을 그대로 쓴다
            key_p = planted.get((d["key"], bi), [])
            gen_bodies.setdefault(d["key"], {})[bi] = _compose(
                d, bi, key_p, random.Random(hash((d["key"], bi)) & 0xFFFFFFFF))

    stats = {
        "docs": len(doc_plan), "units": total_slots,
        "signal_units": sum(1 for s in slots_all if s["sig"]),
        "legacy_counts": leg_cnt,
    }
    return doc_plan, planted, gen_bodies, congress_meta, stats


def _insert(lines, sig_lines, rng):
    """신호 문장을 앞·뒤 어디에도 몰리지 않게 끼운다(항상 2번째면 패턴이 보인다)."""
    for s2 in sig_lines:
        pos = rng.randint(1, max(1, len(lines))) if len(lines) > 1 else len(lines)
        lines.insert(pos, s2)


def _compose(doc, bi, planted, rng):
    """블록 본문 생성 — 신호 문장을 노이즈 문장 사이에 끼운다."""
    st = doc["source_type"]
    style = MSL_V3.get(doc["authors"][0], {"style": "narrative"})["style"]
    sig_lines = [p["verbatim"] for p in planted]
    if st == "HIGHLIGHT_DOC":
        n = rng.randint(2, 4) if sig_lines else rng.randint(3, 5)
        lines = noise_sentences(rng, doc["date"], n, style)
        _insert(lines, sig_lines, rng)
        return "\n".join("> " + l for l in lines)
    if st == "CONGRESS_REPORT":
        n = rng.randint(2, 3) if sig_lines else rng.randint(3, 4)
        lines = noise_sentences(rng, doc["date"], n, style, congress=True)
        _insert(lines, sig_lines, rng)
        return " ".join(lines)
    if st == "VOICE_TRANSCRIPT":
        return _compose_ko(doc, sig_lines, rng)
    if st == "EMAIL_SUMMARY":
        body = noise_sentences(rng, doc["date"], rng.randint(2, 3), style)
        items = sig_lines + [body.pop()] if body else sig_lines
        head = " ".join(body) if body else "Recap of the exchange below."
        return head + "\n" + "\n".join(f"{i}. {t}" for i, t in enumerate(items, 1))
    n = rng.randint(3, 5) if st == "MEETING_NOTE" else rng.randint(2, 3)
    lines = noise_sentences(rng, doc["date"], n, style)
    _insert(lines, sig_lines, rng)
    sep = "\n\n" if st == "MEETING_NOTE" else " "
    return sep.join(lines)


KO_OPEN = ["MSL: 선생님 안녕하세요, 오늘 시간 내주셔서 감사합니다.",
           "MSL: 안녕하세요 선생님, 외래 끝나고 잠시 괜찮으세요?",
           "MSL: 선생님, 지난번 말씀 나눈 부분 여쭤보려고 왔습니다."]
KO_NOISE = ["HCP: 요즘 외래가 밀려서 정신이 없네요.",
            "HCP: 예약 시스템이 바뀌어서 그게 더 골치예요.",
            "HCP: 전공의가 두 명 새로 들어와서 적응 기간이에요.",
            "MSL: 다음 방문은 언제가 편하실까요?",
            "HCP: 다음 달 학회는 가시죠? 세션이 괜찮아 보이던데요.",
            "MSL: 네, 참석 예정입니다. 학회에서 뵙겠습니다."]
KO_SIG = {
    "S1": "HCP: 2제 실패한 청소년 환자가 있는데 성인 허가라 지금은 손을 쓸 수가 없어요.",
    "S7": "HCP: 전신발작 환자분들은 아예 선택지가 없어서 답답할 때가 많습니다.",
    "S6": "HCP: 어르신들은 드시는 약이 많아서 상호작용부터 확인하다 보면 시작이 늦어져요.",
    "S5": "HCP: 약을 몇 번 바꿔도 안 잡히던 성인 환자분이 발작이 눈에 띄게 줄었어요.",
}


def _compose_ko(doc, sig_lines, rng):
    lines = [rng.choice(KO_OPEN)]
    lines += rng.sample(KO_NOISE, k=rng.randint(2, 4))
    for s in sig_lines:
        lines.insert(2, s)
    lines.append("MSL: 말씀 주신 내용은 기록해 두겠습니다. 감사합니다 선생님.")
    return "\n".join(lines)
