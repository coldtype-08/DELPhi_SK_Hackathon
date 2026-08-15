"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [
  { href: "/", label: "홈 대시보드" },
  { href: "/review", label: "Data Review" },
  { href: "/hypotheses", label: "가설 보드" },
  { href: "/contract", label: "Data Contract" },
  { href: "/safety", label: "Safety 로그" },
];

export default function Nav() {
  const path = usePathname();
  return (
    <nav className="flex flex-col gap-1">
      {ITEMS.map((it) => {
        const active = it.href === "/" ? path === "/" : path.startsWith(it.href);
        return (
          <Link
            key={it.href}
            href={it.href}
            className={`rounded-lg px-3 py-2 text-sm font-semibold transition-colors ${
              active ? "bg-orange-soft text-orange-deep" : "text-muted hover:bg-sky-soft hover:text-navy"
            }`}
          >
            {it.label}
          </Link>
        );
      })}
    </nav>
  );
}
