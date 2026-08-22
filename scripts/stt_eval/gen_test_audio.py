"""TEST_SCRIPTS.md의 대본 → WAV. STT 후보 배선·동작 확인용 (오너: 인혁).

espeak-ng를 쓴다 — 무료·오프라인(설치 후 외부 호출 없음)·라이선스 제약 없음.
edge-tts(Microsoft)·piper(모델이 huggingface.co)는 사내망/프록시에서 막혀 채택하지 못했다.

**한계 — 판정 재료가 아니다.** espeak-ng는 포먼트 합성이라 발음이 규격화돼 있고,
대본 B의 lamotrigine·titration·DDI를 한국어 엔진이 읽으므로 실제 한국인의 영어 발음과 다르다.
이 파일로 점수가 잘 나와도 실전을 보장하지 않는다 — **사람이 대본을 읽어 녹음한 파일이 진짜 판정 재료**다
(녹음 지침: TEST_SCRIPTS.md). 여기서 만드는 음성은 배선·동작 확인용으로만 쓴다.

사용법:
    apt-get install -y espeak-ng
    python3 scripts/stt_eval/gen_test_audio.py     # → scripts/stt_eval/audio/*.wav (gitignore)

화자별로 다른 voice variant를 써서 화자 분리(diarization) 검증이 가능하게 한다.
대본을 고치면 TEST_SCRIPTS.md와 이 파일의 턴 목록을 **같이** 수정한다.
"""
import subprocess, sys, wave
from pathlib import Path

OUT = Path(__file__).resolve().parent / "audio"
OUT.mkdir(exist_ok=True)

EN = [
    ("MSL", "Good morning, Doctor. Thanks for making time. Did you get the materials I sent last week?"),
    ("HCP", "I did, thank you. The clinic has been busy, a lot of referrals lately."),
    ("MSL", "I heard you have been seeing more adolescent cases with drug-resistant focal seizures."),
    ("HCP", "That is right. I have a seventeen-year-old who has failed two anti-seizure medications. But cenobamate is approved for adults, so there is nothing I can do until they turn eighteen."),
    ("MSL", "So that gap keeps coming up. I will log it as stated."),
    ("HCP", "Also, one adult patient reported dizziness and somnolence after starting XCOPRI."),
    ("MSL", "I will route that through the safety review pathway. The relevant team will follow up."),
    ("HCP", "Please do. And if any adolescent dosing or safety data becomes available, I would appreciate a copy."),
    ("MSL", "Understood. Anything else coming up in your practice lately?"),
    ("HCP", "Generalized tonic-clonic seizures, actually. It works well for focal onset, but I cannot use it for my generalized patients. And for Lennox-Gastaut syndrome the drop attacks are frequent and the existing options fall short."),
    ("MSL", "Understood. Should I coordinate the next visit through your office?"),
    ("HCP", "Yes, call the clinic at five five five, one two three, four five six seven."),
    ("MSL", "Thank you, Doctor."),
]

KOEN = [
    ("MSL", "선생님, 안녕하세요. 지난번에 보내드린 자료는 잘 받으셨죠?"),
    ("HCP", "네, 잘 봤어요. 요즘 외래가 많아서 정신이 없네요."),
    ("MSL", "난치성 초점발작 청소년 케이스가 늘었다고 들었습니다."),
    ("HCP", "맞아요. 2제 실패한 17세 환자가 있는데, 엑스코프리는 성인 허가라 지금은 손을 쓸 수가 없어요. 18세까지 기다리는 것 말고는 방법이 없네요."),
    ("MSL", "그런 케이스가 반복되는군요. 기록해 두겠습니다."),
    ("HCP", "그리고 고령 환자분들은 lamotrigine 같은 병용약이 많아서 DDI부터 걱정하시더라고요. titration 스케줄도 부담스럽다고 하시고요."),
    ("MSL", "병용약 상호작용 확인 부담이 크시군요."),
    ("HCP", "네. 아, 성인 환자 한 분은 세노바메이트 복용 시작하고 어지러움하고 졸림이 꽤 있다고 하셨어요."),
    ("MSL", "그 부분은 안전성 검토 경로로 전달하겠습니다."),
    ("HCP", "아 그리고, 초점발작 환자에는 잘 듣는데 전신 강직-간대발작 환자에는 쓸 수가 없어서요. PGTC 케이스가 요즘 좀 늘었습니다."),
    ("MSL", "전신발작 쪽 문헌도 같이 정리해 드릴까요?"),
    ("HCP", "네, 부탁드려요. 레녹스-가스토 증후군 아이들도 드롭발작이 잦아서 기존 약으로는 한계가 있어요."),
    ("HCP", "그렇게 해주세요. 다음 방문은 김도현 선생님 통해서 잡아주시고, 제 번호 010-4132-7789로 연락 주세요."),
    ("MSL", "네, 감사합니다 선생님."),
]

VOICES = {  # 화자별 목소리 (variant로 구분)
    "en": {"MSL": "en-us+m3", "HCP": "en-us+f2"},
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


synth(EN, "en", "stt_test_A_english")
synth(KOEN, "ko", "stt_test_B_ko_en_mixed")
