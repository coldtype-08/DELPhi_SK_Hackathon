import type { Metadata } from "next";
import "./globals.css";
import Nav from "./nav";

export const metadata: Metadata = {
  title: "DELPHi Console",
  description: "Growth Intelligence for XCOPRI — 검토·가설·심의 대시보드",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ko" className="h-full antialiased">
      <body className="min-h-full">
        <div className="flex min-h-dvh">
          <aside className="hidden w-56 shrink-0 flex-col border-r border-line bg-card px-4 py-6 md:flex">
            <div className="mb-8 px-2">
              <div className="text-lg font-extrabold tracking-tight text-navy">DELPHi</div>
              <div className="text-[11px] font-semibold text-muted">Growth Intelligence · Console</div>
            </div>
            <Nav />
            <div className="mt-auto rounded-lg bg-paper px-3 py-2 text-[11px] leading-relaxed text-muted">
              롤: <b className="text-navy">CLINICAL_STRATEGY</b>
              <br />롤 전환 스위처는 P1 [오너: 건태]
            </div>
          </aside>
          <main className="min-w-0 flex-1 px-6 py-8 md:px-10">{children}</main>
        </div>
      </body>
    </html>
  );
}
