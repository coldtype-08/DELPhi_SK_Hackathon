"use client";

/**
 * 실시간 전사 재생 (전사 스크립트 폴백 경로 — docs/03 §6) [cross] 오너: 소정
 * 대화가 한 줄씩 흐르고, 신호가 담긴 구간이 아래 감지 칩과 같은 색으로 하이라이트된다.
 * 부작용 의심 발언은 그 자리에서 안전성 경로 분리 배지가 뜬다 (연출 포인트 ①, docs/05 §4).
 * 라이브 감지는 연출이며 정본 추출은 제출 시 1회 — 재생이 끝나면 전사 전문이 입력란으로 넘어간다.
 */

import { useEffect, useRef, useState } from "react";
import { CAT_LABEL, SCRIPT, fullTranscript, type EvCat, type Line } from "@/lib/capture-demo";

const CHIP_CLASS: Record<EvCat, string> = {
  segment: "bg-orange-soft text-orange-deep",
  signal: "bg-sky-soft text-sky",
  ae: "bg-rust-soft text-rust",
  info: "bg-green-soft text-green",
  meta: "bg-paper text-muted",
};

/** 발언 텍스트를 spans 기준으로 쪼개 구간 하이라이트를 입힌다. lit=false면 아직 투명. */
function LineText({ line, lit }: { line: Line; lit: boolean }) {
  if (!line.spans?.length) return <>{line.t}</>;
  const parts: React.ReactNode[] = [];
  let rest = line.t;
  line.spans.forEach((s, i) => {
    const at = rest.indexOf(s.q);
    if (at < 0) return;
    parts.push(rest.slice(0, at));
    parts.push(
      <mark key={i} className={`ev ev-${s.cat}${lit ? " on" : ""}`}>
        {s.q}
      </mark>,
    );
    rest = rest.slice(at + s.q.length);
  });
  parts.push(rest);
  return <>{parts}</>;
}

export default function LiveTranscript({ onComplete }: { onComplete: (rawText: string) => void }) {
  const [shown, setShown] = useState(0); // 화면에 나온 줄 수
  const [lit, setLit] = useState(0); // 하이라이트·칩까지 켜진 줄 수
  const [playing, setPlaying] = useState(false);
  const [finished, setFinished] = useState(false);
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => () => timers.current.forEach(clearTimeout), []);
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [shown, lit]);

  function reset() {
    timers.current.forEach(clearTimeout);
    timers.current = [];
    setShown(0);
    setLit(0);
    setPlaying(false);
    setFinished(false);
  }

  function play() {
    reset();
    setPlaying(true);
    const instant =
      typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (instant) {
      setShown(SCRIPT.length);
      setLit(SCRIPT.length);
      setPlaying(false);
      setFinished(true);
      onComplete(fullTranscript());
      return;
    }
    SCRIPT.forEach((_, i) => {
      timers.current.push(setTimeout(() => setShown(i + 1), i * 1500));
      timers.current.push(setTimeout(() => setLit(i + 1), i * 1500 + 550));
    });
    timers.current.push(
      setTimeout(() => {
        setPlaying(false);
        setFinished(true);
        onComplete(fullTranscript());
      }, SCRIPT.length * 1500 + 700),
    );
  }

  const catches = SCRIPT.slice(0, lit).flatMap((l) => l.catches ?? []);

  return (
    <div className="rounded-2xl border border-line bg-card p-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-bold text-navy">
          실시간 전사
          {playing && (
            <span className="ml-2 inline-block size-2 animate-pulse rounded-full bg-rust align-middle" />
          )}
        </h2>
        <span className="text-[10px] font-semibold text-muted">대본 재생 폴백 · ko-KR</span>
      </div>

      {/* 하이라이트 범례 — 견본이 곧 안내: 전사 속 구간과 감지 칩이 이 색으로 짝지어진다 */}
      <div className="mt-1.5 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-[9.5px] font-semibold text-muted">
        <span>하이라이트</span>
        <mark className="ev on ev-segment">환자군</mark>
        <mark className="ev on ev-signal">신호</mark>
        <mark className="ev on ev-ae">안전성 분리</mark>
        <mark className="ev on ev-info">자료 요청</mark>
      </div>

      <div ref={scrollRef} className="mt-2 max-h-56 space-y-1.5 overflow-y-auto pr-1">
        {shown === 0 && (
          <p className="py-4 text-center text-[11px] text-muted">
            ▶ 전사 재생을 누르면 면담 대화가 흐르고, 신호 구간이 아래 칩과 같은 색으로 잡힙니다.
          </p>
        )}
        {SCRIPT.slice(0, shown).map((l, i) => (
          <div key={i} className="flex items-start gap-1.5">
            <span
              className={`mt-0.5 shrink-0 rounded px-1.5 py-0.5 text-[9px] font-extrabold ${
                l.sp === "MSL" ? "bg-sky-soft text-sky" : "bg-paper text-navy"
              }`}
            >
              {l.sp}
            </span>
            <p className="rounded-lg border border-line bg-paper px-2.5 py-1.5 text-xs leading-relaxed">
              <LineText line={l} lit={i < lit} />
            </p>
          </div>
        ))}
      </div>

      <div className="mt-2 border-t border-line pt-2">
        <div className="text-[9.5px] font-extrabold tracking-wider text-muted">실시간 감지 — 스키마 캐치</div>
        <div className="mt-1.5 flex flex-wrap gap-1">
          {catches.length === 0 ? (
            <span className="text-[10.5px] text-muted">아직 감지된 신호 없음</span>
          ) : (
            catches.map((c, i) => (
              <span
                key={i}
                title={CAT_LABEL[c.cat]}
                className={`rounded-full px-2 py-0.5 text-[10px] font-extrabold ${CHIP_CLASS[c.cat]}`}
              >
                {c.label}
              </span>
            ))
          )}
          {finished && (
            <span className="rounded-full bg-orange-soft px-2 py-0.5 text-[10px] font-extrabold text-orange-deep">
              전사 완료 → 아래 입력란에 담김
            </span>
          )}
        </div>
      </div>

      <div className="mt-3 flex gap-2">
        <button
          onClick={play}
          disabled={playing}
          className="flex-1 rounded-xl bg-navy py-2.5 text-xs font-bold text-white disabled:opacity-50"
        >
          {playing ? "재생 중…" : finished ? "↺ 다시 재생" : "▶ 전사 재생"}
        </button>
        {(playing || finished) && (
          <button onClick={reset} className="rounded-xl border border-line px-4 text-xs font-bold text-muted">
            초기화
          </button>
        )}
      </div>
      <p className="mt-2 text-[9.5px] leading-relaxed text-muted">
        라이브 감지·하이라이트는 연출이며 정본 추출은 제출 시 1회(재현성). 부작용 의심 발언은 카드로
        나오지 않고 안전성 경로로만 저장된다(절대 규칙 #6). 음성 인식(Web Speech)은 P1 — 실패 시 이
        대본 재생으로 시연.
      </p>
    </div>
  );
}
