"""TEST_SCRIPTS.md의 대본 → WAV (오너: 인혁).

P1(HYP-003 정본)은 네 곳에서 같은 파일을 재사용한다 — ① 8/24 STT 3종 비교
② 시스템 완성 후 통합 테스트(끝나면 적재 데이터 삭제) ③ 제출물 첨부 음성
④ 경연 발표 라이브 입력. 그래서 P1은 사람이 읽어 녹음한 파일이 정본이고,
여기서 만드는 WAV는 그 전까지의 배선·동작 확인용이다.

espeak-ng를 쓴다 — 무료·오프라인(설치 후 외부 호출 없음)·라이선스 제약 없음.
edge-tts(Microsoft)·piper(모델이 huggingface.co)는 사내망/프록시에서 막혀 채택하지 못했다.

**한계 — 판정 재료가 아니다.** espeak-ng는 포먼트 합성이라 발음이 규격화돼 있고,
T1의 lamotrigine·titration·DDI를 한국어 엔진이 읽으므로 실제 한국인의 영어 발음과 다르다.
이 파일로 점수가 잘 나와도 실전을 보장하지 않는다 — **사람이 대본을 읽어 녹음한 파일이 진짜 판정 재료**다
(녹음 지침: TEST_SCRIPTS.md). 여기서 만드는 음성은 배선·동작 확인용으로만 쓴다.

사용법:
    apt-get install -y espeak-ng
    python3 scripts/stt_eval/gen_test_audio.py     # → scripts/stt_eval/audio/*.wav (gitignore)

화자별로 다른 voice variant를 써서 화자 분리(diarization) 검증이 가능하게 한다.
대본을 고치면 TEST_SCRIPTS.md와 이 파일의 턴 목록을 **같이** 수정한다.

D1은 `apps/field/lib/capture-demo.ts` 의 SCRIPT와 같아야 한다 — 그 파일이 바뀌면 여기도 맞춘다.
"""
import subprocess, sys, wave
from pathlib import Path

OUT = Path(__file__).resolve().parent / "audio"
OUT.mkdir(exist_ok=True)

P1 = [  # HYP-003(PGTC) 정본 7턴 — scripts/stt_eval/P1_reference.txt 와 문장이 같아야 한다
    ("MSL", "안녕하세요 선생님, 외래 끝나고 잠시 괜찮으세요?"),
    ("HCP", "네, 오늘은 좀 일찍 끝났어요. 앉으세요."),
    ("MSL", "요즘 난치성 환자분들 중에 특히 손 쓰기 어려운 케이스가 있으세요?"),
    ("HCP", "전신 강직-간대발작 환자분들이 그래요. XCOPRI가 초점발작에는 잘 듣는 걸 아는데, "
            "전신발작은 허가 범위가 아니라서 아예 선택지가 없어요. "
            "세 번째 약까지 실패한 분이 지금 두 분 계신데 드릴 게 없으니 답답하죠."),
    ("HCP", "아, 그리고 지난달에 시작한 성인 환자 한 분은 초기에 어지러움하고 졸림이 좀 있다고 하셨어요."),
    ("HCP", "그, 전신발작 환자군 관련해서 나온 문헌이나 ClinicalTrials에 등록된 연구가 있으면 "
            "좀 보내주실 수 있을까요? 제 번호 010-4132-7789로 주셔도 되고요."),
    ("MSL", "확인해서 있는 범위 내에서 다음 방문 때 정리해 드리겠습니다. "
            "말씀 주신 이상반응은 절차대로 안전성 검토 경로로 전달하겠습니다."),
]

D1 = [  # apps/field/lib/capture-demo.ts 의 SCRIPT 7턴 — 문장을 바꾸지 않는다
    ("MSL", "안녕하세요 선생님, 지난 학회는 잘 다녀오셨어요?"),
    ("HCP", "네, 다녀오고 나니 외래가 밀려서 정신이 없네요."),
    ("MSL", "요즘 약물난치성 환자분들은 좀 어떠세요?"),
    ("HCP", "2제 실패한 17세 환자가 있는데, 성인 허가라 손을 쓸 수가 없어요. 18세까지 기다리는 수밖에요."),
    ("HCP", "아, 그리고 성인 환자 한 분은 복용 시작하고 어지러움하고 졸림이 꽤 있다고 하셨어요."),
    ("HCP", "혹시 청소년 용량이나 안전성 자료가 있으면 보내주실 수 있어요?"),
    ("MSL", "확인해서 다음 방문 때 정리해 드리겠습니다."),
]

T1 = [  # D1 + 영어 용어 혼용 + PII (테스트 전용)
    ("MSL", "안녕하세요 선생님, 지난 학회는 잘 다녀오셨어요?"),
    ("HCP", "네, 다녀오고 나니 외래가 밀려서 정신이 없네요."),
    ("MSL", "요즘 약물난치성 환자분들은 좀 어떠세요?"),
    ("HCP", "2제 실패한 17세 환자가 있는데, XCOPRI는 성인 허가라 손을 쓸 수가 없어요. 18세까지 기다리는 수밖에요."),
    ("HCP", "고령 환자분들은 lamotrigine 같은 병용약이 많아서 DDI부터 걱정하시고, titration 스케줄도 부담스럽다고 하세요."),
    ("HCP", "아, 그리고 성인 환자 한 분은 복용 시작하고 어지러움하고 졸림이 꽤 있다고 하셨어요."),
    ("HCP", "혹시 청소년 용량이나 안전성 자료가 있으면 보내주실 수 있어요? 제 번호 010-4132-7789로 주셔도 되고요."),
    ("MSL", "확인해서 다음 방문 때 정리해 드리겠습니다."),
]

VOICES = {  # 화자별 목소리 (variant로 구분 → 화자 분리 검증 가능)
    "ko": {"MSL": "ko+m3", "HCP": "ko+f2"},
}


def synth(turns, lang, out_name):
    tmp = OUT / "_parts"; tmp.mkdir(exist_ok=True)
    parts = []
    for i, (spk, text) in enumerate(turns):
        p = tmp / f"{out_name}_{i:02d}.wav"
        subprocess.run(
            ["espeak-ng", "-v", VOICES[lang][spk], "-s", "155", "-w", str(p), text],
            check=True,
        )
        parts.append(p)

    with wave.open(str(parts[0]), "rb") as w0:
        params = w0.getparams()
    silence = b"\x00" * (params.framerate * params.sampwidth * params.nchannels // 3)  # 0.33초

    dest = OUT / f"{out_name}.wav"
    with wave.open(str(dest), "wb") as out:
        out.setparams(params)
        for p in parts:
            with wave.open(str(p), "rb") as w:
                out.writeframes(w.readframes(w.getnframes()))
            out.writeframes(silence)
    for p in parts:
        p.unlink()
    tmp.rmdir()

    with wave.open(str(dest), "rb") as w:
        sec = w.getnframes() / w.getframerate()
    print(f"{dest.name}  {sec:.1f}초  {dest.stat().st_size/1024:.0f}KB  ({len(turns)}턴, 화자 2인)")


def assert_p1_matches_reference():
    ref = (Path(__file__).resolve().parent / "P1_reference.txt").read_text(encoding="utf-8")
    want = [f"{spk}: {text}" for spk, text in P1]
    have = [l.strip() for l in ref.splitlines() if l.startswith(("MSL:", "HCP:"))]
    if want != have:
        for i, (w, h) in enumerate(zip(want, have)):
            if w != h:
                sys.exit(f"P1 대본이 P1_reference.txt와 다릅니다 (턴 {i+1}):\n  py : {w}\n  txt: {h}")
        sys.exit(f"P1 턴 수 불일치: py {len(want)}턴 vs txt {len(have)}턴")


assert_p1_matches_reference()
synth(P1, "ko", "P1_hyp003_pgtc")
synth(D1, "ko", "D1_korean")
synth(T1, "ko", "T1_ko_en_mixed")
