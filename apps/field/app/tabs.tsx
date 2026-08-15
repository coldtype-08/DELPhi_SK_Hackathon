"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/", label: "오늘" },
  { href: "/capture", label: "면담 기록" },
  { href: "/history", label: "내 기록" },
];

export default function Tabs() {
  const path = usePathname();
  return (
    <nav className="sticky bottom-0 z-10 flex border-t border-line bg-card">
      {TABS.map((t) => {
        const active = t.href === "/" ? path === "/" : path.startsWith(t.href);
        return (
          <Link
            key={t.href}
            href={t.href}
            className={`flex-1 py-3 text-center text-xs font-bold transition-colors ${
              active ? "text-orange-deep" : "text-muted"
            }`}
          >
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}
