import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DELPHi STT Lab",
  description: "STT 서비스 3종 비교 — Soniox · Gladia · Deepgram",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko" className="h-full antialiased">
      {/* 로컬 전용 비교 도구. 데스크톱 우선 — Field/Console과 같은 페이퍼 라이트 토큰 (docs/05) */}
      <body className="min-h-full">
        <div className="mx-auto flex min-h-dvh max-w-[1180px] flex-col">
          <header className="flex items-center justify-between border-b border-line px-6 py-4">
            <div>
              <div className="text-lg font-extrabold tracking-tight text-navy">DELPHi STT Lab</div>
              <div className="text-[11px] font-semibold text-muted">
                실시간 STT 3종 비교 · 로컬 전용 · 배포하지 않음
              </div>
            </div>
            <span className="rounded-full bg-orange-soft px-2.5 py-1 text-[10px] font-bold text-orange-deep">
              비교 테스트
            </span>
          </header>
          <main className="flex-1 bg-paper px-6 py-6">{children}</main>
        </div>
      </body>
    </html>
  );
}
