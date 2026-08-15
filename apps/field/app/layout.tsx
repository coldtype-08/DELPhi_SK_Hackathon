import type { Metadata, Viewport } from "next";
import "./globals.css";
import Tabs from "./tabs";

export const metadata: Metadata = {
  title: "DELPHi Field",
  description: "현장 면담 수집 — 동의·전사·구조화 승인",
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko" className="h-full antialiased">
      {/* 모바일 우선 390px (docs/01 §5) — 데스크톱에서는 가운데 프레임으로 미리보기 */}
      <body className="min-h-full">
        <div className="mx-auto flex min-h-dvh max-w-[420px] flex-col border-x border-line bg-card">
          <header className="flex items-center justify-between border-b border-line px-4 py-3">
            <div>
              <div className="text-base font-extrabold tracking-tight text-navy">DELPHi Field</div>
              <div className="text-[10px] font-semibold text-muted">현장 수집 · MEDICAL_AFFAIRS</div>
            </div>
            <span className="rounded-full bg-orange-soft px-2 py-1 text-[10px] font-bold text-orange-deep">
              페이퍼 라이트
            </span>
          </header>
          <main className="flex-1 overflow-y-auto bg-paper px-4 py-5">{children}</main>
          <Tabs />
        </div>
      </body>
    </html>
  );
}
