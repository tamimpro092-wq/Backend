"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const items = [
  { href: "/", label: "Dashboard", hint: "Control deck", accent: "from-cyan-400/40 to-violet-400/15" },
  { href: "/jarvis", label: "Mira", hint: "Command center", accent: "from-violet-400/40 to-pink-400/15" },
  { href: "/shopify", label: "Shopify", hint: "Products", accent: "from-lime-400/35 to-cyan-400/12" },

  // ✅ Facebook opens external URL
  {
    href: "https://ui-rosy-rho.vercel.app/admin",
    label: "Facebook",
    hint: "Posts + DMs",
    accent: "from-cyan-400/35 to-blue-400/12",
    external: true
  },

  { href: "/whatsapp", label: "WhatsApp", hint: "Inbox", accent: "from-lime-400/30 to-emerald-400/12" },
  { href: "/approvals", label: "Approvals", hint: "Safety gate", accent: "from-pink-400/35 to-violet-400/12" },
  { href: "/logs", label: "Logs", hint: "Audit trail", accent: "from-cyan-400/25 to-violet-400/10" },
  { href: "/status", label: "Status", hint: "Health", accent: "from-violet-400/25 to-cyan-400/10" }
];

export default function Nav() {
  const path = usePathname();

  return (
    <aside className="w-[280px] min-h-screen p-4 hidden md:block">
      <div className="neon-card neon-glow rounded-2xl p-4 h-full flex flex-col">
        <div className="flex items-center justify-between">
          <div>
            <div className="text-[11px] uppercase tracking-[0.28em] text-[color:var(--muted)]">
              MULTI AGENT MODULE
            </div>
            <div className="text-xl font-semibold">
              MIRA<span className="text-[color:var(--cyan)]">.AI</span>
            </div>
          </div>
          <div className="h-10 w-10 rounded-xl border border-white/10 bg-white/5 grid place-items-center">
            ✦
          </div>
        </div>

        <div className="my-4 neon-divider" />

        <nav className="flex-1 space-y-2">
          {items.map((it) => {
            const active = !it.external && path === it.href;

            const commonClassName = [
              "group relative block rounded-xl px-3 py-3 transition",
              "border border-white/5 bg-white/0 hover:bg-white/5",
              active ? "bg-white/6 border-white/10" : ""
            ].join(" ");

            const Inner = (
              <>
                <div
                  className={[
                    "absolute inset-0 rounded-xl opacity-0 group-hover:opacity-100 transition",
                    "bg-gradient-to-r",
                    it.accent
                  ].join(" ")}
                />
                <div className="relative">
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{it.label}</span>
                    <span className="text-[10px] text-[color:var(--muted)]">
                      {it.external ? "external" : active ? "active" : "open"}
                    </span>
                  </div>
                  <div className="text-[11px] mt-1 text-[color:var(--muted)]">
                    {it.hint}
                  </div>
                </div>
              </>
            );

            // ✅ If external: use <a> so it opens URL
            if (it.external) {
              return (
                <a
                  key={it.label}
                  href={it.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className={commonClassName}
                >
                  {Inner}
                </a>
              );
            }

            // ✅ Otherwise internal navigation
            return (
              <Link key={it.href} href={it.href} className={commonClassName}>
                {Inner}
              </Link>
            );
          })}
        </nav>

        <div className="neon-divider my-4" />

        <div className="text-xs text-[color:var(--muted)]">
          Risky actions go to <span className="text-[color:var(--cyan)]">Approvals</span>.
        </div>
      </div>
    </aside>
  );
}
