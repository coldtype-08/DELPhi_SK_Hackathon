"use client";

/**
 * STT 3종 비교 랩 — Soniox · Gladia · Deepgram
 *
 * 로컬 전용. API 키는 화면에서 입력하고 브라우저 localStorage 에만 둔다 (커밋·전송 없음).
 * 채점 정답지는 scripts/stt_eval/TEST_SCRIPTS.md, 음성은 gen_test_audio.py 로 만든다.
 * 결과가 3탭에 남으므로 같은 입력으로 세 서비스를 나란히 비교할 수 있다.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  PROVIDERS,
  TARGET_SAMPLE_RATE,
  fileToPcm16,
  providerById,
  scoreSummary,
  scoreTranscript,
  startMic,
  streamPcmRealtime,
  type MicHandle,
  type ProviderId,
  type ScriptId,
  type Segment,
  type SttSession,
} from "@/lib/stt";

/** 부스팅 기본 용어 — backend/app/seed.py VOCAB_SEED + 데모 대본 고유명사 (docs/02 §3) */
const DEFAULT_BOOST = [
  "XCOPRI", "엑스코프리", "세노바메이트", "cenobamate", "lamotrigine", "라모트리진",
  "titration", "타이트레이션", "DDI", "난치성", "초점발작", "병용약", "상호작용",
  "적정", "청소년", "고령", "어지러움", "졸림", "약물난치성", "뇌전증",
  "drug-resistant", "refractory", "focal seizures", "adolescent", "somnolence",
].join(", ");

type RunState = {
  status: "idle" | "connecting" | "running" | "done" | "error";
  segments: Segment[];
  raw: unknown[];
  error: string | null;
  firstTokenMs: number | null;
  finalMs: number | null;
};

const EMPTY: RunState = {
  status: "idle", segments: [], raw: [], error: null, firstTokenMs: null, finalMs: null,
};

type Settings = { apiKey: string; model: string; endpoint: string };

export default function Page() {
  const [tab, setTab] = useState<ProviderId>("soniox");
  const [script, setScript] = useState<ScriptId>("B");
  const [langMode, setLangMode] = useState<"ko" | "en" | "koen">("koen");
  const [diarize, setDiarize] = useState(true);
  const [useBoost, setUseBoost] = useState(true);
  const [boostText, setBoostText] = useState(DEFAULT_BOOST);
  const [file, setFile] = useState<File | null>(null);
  const [settings, setSettings] = useState<Record<ProviderId, Settings>>(() => {
    const base: Record<string, Settings> = {};
    for (const p of PROVIDERS) base[p.id] = { apiKey: "", model: p.models[0].value, endpoint: p.defaultEndpoint };
    return base as Record<ProviderId, Settings>;
  });
  const [runs, setRuns] = useState<Record<ProviderId, RunState>>(() => {
    const base: Record<string, RunState> = {};
    for (const p of PROVIDERS) base[p.id] = EMPTY;
    return base as Record<ProviderId, RunState>;
  });

  const sessionRef = useRef<SttSession | null>(null);
  const micRef = useRef<MicHandle | null>(null);
  const stopRef = useRef(false);

  // 키·모델·엔드포인트는 브라우저 localStorage 에만 보관 (커밋·서버 전송 없음).
  // 마운트 시 1회 복원 — 외부 시스템(localStorage) 구독이라 effect 가 맞는 자리다.
  useEffect(() => {
    const saved = localStorage.getItem("delphi-stt-lab");
    if (!saved) return;
    try {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- 마운트 시 1회 복원
      setSettings(JSON.parse(saved));
    } catch {
      /* 손상된 값은 무시 */
    }
  }, []);
  useEffect(() => {
    localStorage.setItem("delphi-stt-lab", JSON.stringify(settings));
  }, [settings]);

  const languages = useMemo(
    () => (langMode === "koen" ? ["ko", "en"] : [langMode]),
    [langMode],
  );
  const boostTerms = useMemo(
    () => (useBoost ? boostText.split(",").map((t) => t.trim()).filter(Boolean) : []),
    [useBoost, boostText],
  );

  const patch = (id: ProviderId, p: Partial<RunState>) =>
    setRuns((prev) => ({ ...prev, [id]: { ...prev[id], ...p } }));

  const stopAll = useCallback(() => {
    stopRef.current = true;
    micRef.current?.stop();
    micRef.current = null;
    sessionRef.current?.finish();
    setTimeout(() => { sessionRef.current?.close(); sessionRef.current = null; }, 1200);
  }, []);

  const run = useCallback(
    async (id: ProviderId, source: "mic" | "file") => {
      const cfg = settings[id];
      if (!cfg.apiKey) { patch(id, { status: "error", error: "API 키를 입력하세요" }); return; }
      if (source === "file" && !file) { patch(id, { status: "error", error: "WAV 파일을 선택하세요" }); return; }

      stopAll();
      stopRef.current = false;
      patch(id, { ...EMPTY, status: "connecting" });
      const t0 = performance.now();
      let firstSeen = false;

      try {
        const session = await providerById(id).connect(
          {
            apiKey: cfg.apiKey, model: cfg.model, endpoint: cfg.endpoint,
            languages, boostTerms, diarize, sampleRate: TARGET_SAMPLE_RATE,
          },
          {
            onSegment: (s) => {
              if (!firstSeen && s.text.trim()) {
                firstSeen = true;
                patch(id, { firstTokenMs: Math.round(performance.now() - t0) });
              }
              setRuns((prev) => ({ ...prev, [id]: { ...prev[id], segments: [...prev[id].segments, s] } }));
              if (s.isFinal) patch(id, { finalMs: Math.round(performance.now() - t0) });
            },
            onRaw: (j) => setRuns((prev) => ({ ...prev, [id]: { ...prev[id], raw: [...prev[id].raw.slice(-120), j] } })),
            onError: (e) => patch(id, { status: "error", error: e.message }),
            onClose: () => patch(id, { status: "done" }),
          },
        );
        sessionRef.current = session;
        patch(id, { status: "running" });

        if (source === "mic") {
          micRef.current = await startMic((pcm) => session.send(pcm));
        } else {
          const pcm = await fileToPcm16(file as File);
          await streamPcmRealtime(pcm, (c) => session.send(c), { shouldStop: () => stopRef.current });
          session.finish();
          setTimeout(() => { session.close(); sessionRef.current = null; }, 1500);
        }
      } catch (e) {
        patch(id, { status: "error", error: e instanceof Error ? e.message : String(e) });
      }
    },
    [settings, file, languages, boostTerms, diarize, stopAll],
  );

  return (
    <div className="space-y-5">
      <SharedControls
        {...{ script, setScript, langMode, setLangMode, diarize, setDiarize, useBoost, setUseBoost, boostText, setBoostText, file, setFile, boostCount: boostTerms.length }}
      />

      <div className="flex gap-2">
        {PROVIDERS.map((p) => {
          const st = runs[p.id];
          return (
            <button
              key={p.id}
              onClick={() => setTab(p.id)}
              className={`flex-1 rounded-xl border px-4 py-3 text-left transition ${
                tab === p.id ? "border-navy bg-card shadow-sm" : "border-line bg-card/60 hover:bg-card"
              }`}
            >
              <div className="text-sm font-bold text-navy">{p.label}</div>
              <div className="mt-0.5 text-[11px] font-semibold text-muted">
                <StatusDot status={st.status} />
                {st.firstTokenMs != null ? ` 첫 응답 ${st.firstTokenMs}ms` : " 미실행"}
              </div>
            </button>
          );
        })}
      </div>

      {PROVIDERS.filter((p) => p.id === tab).map((p) => (
        <ProviderPanel
          key={p.id}
          provider={p}
          settings={settings[p.id]}
          onSettings={(s) => setSettings((prev) => ({ ...prev, [p.id]: { ...prev[p.id], ...s } }))}
          state={runs[p.id]}
          script={script}
          hasFile={!!file}
          onRun={(src) => void run(p.id, src)}
          onStop={stopAll}
        />
      ))}
    </div>
  );
}

function StatusDot({ status }: { status: RunState["status"] }) {
  const map: Record<RunState["status"], [string, string]> = {
    idle: ["bg-line", "대기"],
    connecting: ["bg-orange", "연결 중"],
    running: ["bg-green", "수신 중"],
    done: ["bg-sky", "종료"],
    error: ["bg-rust", "오류"],
  };
  const [color, label] = map[status];
  return (
    <span className="inline-flex items-center gap-1">
      <span className={`inline-block size-1.5 rounded-full ${color}`} />
      {label}
    </span>
  );
}

type SharedProps = {
  script: ScriptId; setScript: (s: ScriptId) => void;
  langMode: "ko" | "en" | "koen"; setLangMode: (m: "ko" | "en" | "koen") => void;
  diarize: boolean; setDiarize: (b: boolean) => void;
  useBoost: boolean; setUseBoost: (b: boolean) => void;
  boostText: string; setBoostText: (s: string) => void;
  file: File | null; setFile: (f: File | null) => void;
  boostCount: number;
};

function SharedControls(p: SharedProps) {
  return (
    <section className="rounded-2xl border border-line bg-card p-5">
      <h2 className="text-sm font-bold text-navy">공통 조건</h2>
      <p className="mt-1 text-[11px] text-muted">
        세 탭이 같은 조건을 씁니다. 같은 WAV 파일로 돌려야 공정한 비교가 됩니다.
      </p>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <Field label="채점 대본">
          <Seg options={[["A", "A · 영어만"], ["B", "B · 한국어+영어"]]} value={p.script} onChange={(v) => p.setScript(v as ScriptId)} />
        </Field>
        <Field label="언어 설정">
          <Seg options={[["ko", "한국어"], ["en", "영어"], ["koen", "한국어+영어"]]} value={p.langMode} onChange={(v) => p.setLangMode(v as "ko" | "en" | "koen")} />
        </Field>
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-5">
        <Check label="화자 분리" checked={p.diarize} onChange={p.setDiarize} />
        <Check label={`부스팅 (${p.boostCount}개)`} checked={p.useBoost} onChange={p.setUseBoost} />
        <label className="flex items-center gap-2 text-xs font-semibold text-ink">
          WAV 파일
          <input
            type="file"
            accept="audio/*"
            onChange={(e) => p.setFile(e.target.files?.[0] ?? null)}
            className="text-[11px] font-normal text-muted file:mr-2 file:rounded-lg file:border-0 file:bg-navy file:px-3 file:py-1.5 file:text-[11px] file:font-bold file:text-white"
          />
        </label>
        {p.file && <span className="text-[11px] font-semibold text-green">{p.file.name}</span>}
      </div>

      {p.useBoost && (
        <Field label="부스팅 용어 (쉼표 구분)" className="mt-4">
          <textarea
            value={p.boostText}
            onChange={(e) => p.setBoostText(e.target.value)}
            rows={3}
            className="w-full rounded-xl border border-line bg-paper px-3 py-2 font-mono text-[11px] leading-relaxed text-ink"
          />
        </Field>
      )}
    </section>
  );
}

function ProviderPanel({
  provider, settings, onSettings, state, script, hasFile, onRun, onStop,
}: {
  provider: (typeof PROVIDERS)[number];
  settings: Settings;
  onSettings: (s: Partial<Settings>) => void;
  state: RunState;
  script: ScriptId;
  hasFile: boolean;
  onRun: (src: "mic" | "file") => void;
  onStop: () => void;
}) {
  const finals = state.segments.filter((s) => s.isFinal);
  const transcript = finals.map((s) => s.text).join(" ");
  const rows = useMemo(() => scoreTranscript(transcript, script), [transcript, script]);
  const sum = scoreSummary(rows);
  const busy = state.status === "connecting" || state.status === "running";

  return (
    <section className="space-y-4">
      <div className="rounded-2xl border border-line bg-card p-5">
        <div className="flex flex-wrap items-end gap-3">
          <Field label="API 키" className="min-w-[260px] flex-1">
            <input
              type="password" value={settings.apiKey} placeholder="여기에 붙여넣기"
              onChange={(e) => onSettings({ apiKey: e.target.value })}
              className="w-full rounded-xl border border-line bg-paper px-3 py-2 font-mono text-xs text-ink"
            />
          </Field>
          <Field label="모델">
            <select
              value={settings.model} onChange={(e) => onSettings({ model: e.target.value })}
              className="rounded-xl border border-line bg-paper px-3 py-2 text-xs font-semibold text-ink"
            >
              {provider.models.map((m) => <option key={m.value} value={m.value}>{m.label}</option>)}
            </select>
          </Field>
          <div className="flex gap-2">
            <button onClick={() => onRun("mic")} disabled={busy}
              className="rounded-xl bg-navy px-4 py-2 text-xs font-bold text-white disabled:opacity-40">마이크로 시작</button>
            <button onClick={() => onRun("file")} disabled={busy || !hasFile}
              className="rounded-xl bg-orange px-4 py-2 text-xs font-bold text-white disabled:opacity-40">파일로 시작</button>
            <button onClick={onStop} disabled={!busy}
              className="rounded-xl border border-line px-4 py-2 text-xs font-bold text-ink disabled:opacity-40">정지</button>
          </div>
        </div>

        <Field label="엔드포인트 (문서와 다르면 여기서 교정)" className="mt-4">
          <input
            value={settings.endpoint} onChange={(e) => onSettings({ endpoint: e.target.value })}
            className="w-full rounded-xl border border-line bg-paper px-3 py-2 font-mono text-[11px] text-muted"
          />
        </Field>

        <ul className="mt-4 space-y-1">
          {provider.models.find((m) => m.value === settings.model)?.note && (
            <li className="text-[11px] font-semibold text-orange-deep">
              · {provider.models.find((m) => m.value === settings.model)?.note}
            </li>
          )}
          {provider.notes.map((n) => <li key={n} className="text-[11px] text-muted">· {n}</li>)}
        </ul>

        {state.error && (
          <p className="mt-3 rounded-xl bg-rust-soft px-3 py-2 text-[11px] font-semibold text-rust">{state.error}</p>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-line bg-card p-5">
          <div className="flex items-baseline justify-between">
            <h3 className="text-sm font-bold text-navy">전사</h3>
            <span className="text-[11px] font-semibold text-muted">
              첫 응답 {state.firstTokenMs ?? "–"}ms · 최종 {state.finalMs ?? "–"}ms
            </span>
          </div>
          <div className="mt-3 max-h-80 space-y-1.5 overflow-y-auto">
            {state.segments.length === 0 && <p className="text-xs text-muted">아직 없음</p>}
            {state.segments.map((s, i) => (
              <p key={i} className={`text-xs leading-relaxed ${s.isFinal ? "text-ink" : "text-muted italic"}`}>
                <span className="mr-1.5 rounded bg-sky-soft px-1.5 py-0.5 font-mono text-[10px] font-bold text-sky">
                  {s.speaker}
                </span>
                {s.text}
              </p>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-line bg-card p-5">
          <div className="flex items-baseline justify-between">
            <h3 className="text-sm font-bold text-navy">핵심 토큰 채점</h3>
            <span className="text-[11px] font-bold text-navy">
              {sum.hit}/{sum.total} · 치명 {sum.criticalHit}/{sum.criticalTotal}
            </span>
          </div>
          <div className="mt-3 max-h-80 overflow-y-auto">
            <table className="w-full text-left">
              <tbody>
                {rows.map((r) => (
                  <tr key={r.spec.label} className="border-b border-line/60 last:border-0">
                    <td className="py-1.5 pr-2 align-top">
                      <span className={`inline-block size-1.5 rounded-full ${r.hit ? "bg-green" : "bg-rust"}`} />
                    </td>
                    <td className="py-1.5 pr-2 align-top">
                      <div className={`text-[11px] font-bold ${r.hit ? "text-ink" : "text-rust"}`}>
                        {r.spec.label}{r.spec.critical && <span className="ml-1 text-orange-deep">★</span>}
                      </div>
                      <div className="text-[10px] text-muted">{r.spec.category} · {r.spec.why}</div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <details className="rounded-2xl border border-line bg-card p-5">
        <summary className="cursor-pointer text-sm font-bold text-navy">
          원시 응답 ({state.raw.length})
        </summary>
        <pre className="mt-3 max-h-96 overflow-auto rounded-xl bg-paper p-3 font-mono text-[10px] leading-relaxed text-muted">
          {state.raw.map((r) => JSON.stringify(r)).join("\n") || "아직 없음"}
        </pre>
      </details>
    </section>
  );
}

function Field({ label, children, className = "" }: { label: string; children: React.ReactNode; className?: string }) {
  return (
    <label className={`block ${className}`}>
      <span className="mb-1.5 block text-[11px] font-bold text-muted">{label}</span>
      {children}
    </label>
  );
}

function Seg({ options, value, onChange }: { options: [string, string][]; value: string; onChange: (v: string) => void }) {
  return (
    <div className="inline-flex rounded-xl border border-line bg-paper p-0.5">
      {options.map(([v, l]) => (
        <button key={v} onClick={() => onChange(v)}
          className={`rounded-lg px-3 py-1.5 text-[11px] font-bold transition ${
            value === v ? "bg-navy text-white" : "text-muted hover:text-ink"
          }`}>{l}</button>
      ))}
    </div>
  );
}

function Check({ label, checked, onChange }: { label: string; checked: boolean; onChange: (b: boolean) => void }) {
  return (
    <label className="flex items-center gap-2 text-xs font-semibold text-ink">
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} className="size-4 accent-navy" />
      {label}
    </label>
  );
}
