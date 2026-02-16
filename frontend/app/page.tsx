import Link from "next/link";

const modules = [
  { href: "/jarvis", title: "Jarvis", desc: "Voice + command center", tag: "CORE" },
  { href: "/shopify", title: "Shopify", desc: "Draft → Pricing → Publish", tag: "STORE" },
  { href: "/facebook", title: "Facebook", desc: "Posts, comments, DMs", tag: "SOCIAL" },
  { href: "/whatsapp", title: "WhatsApp", desc: "Customer replies + triage", tag: "SUPPORT" },
  { href: "/approvals", title: "Approvals", desc: "Approve risky actions", tag: "SAFETY" },
  { href: "/logs", title: "Logs", desc: "Audit + debug history", tag: "OPS" },
  { href: "/status", title: "Status", desc: "Health checks", tag: "OPS" },
];

export default function Home() {
  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="neon-card rounded-2xl p-6">
        <div className="text-[11px] uppercase tracking-[0.22em] text-[color:var(--muted)]">
          AI CONTROL DECK
        </div>
        <div className="mt-2 text-3xl font-semibold">
          Overnight E-commerce Autopilot{" "}
          <span className="text-[color:var(--cyan)]">— JARVIS Mode</span>
        </div>
        <p className="mt-2 text-sm text-[color:var(--muted)]">
          Click any module below to open its full page.
        </p>

        <div className="mt-4 flex flex-wrap gap-2">
          <span className="text-xs px-3 py-1 rounded-full border border-white/10 bg-white/5">
            DRY_RUN supported
          </span>
          <span className="text-xs px-3 py-1 rounded-full border border-white/10 bg-white/5">
            Approvals required for risky actions
          </span>
          <span className="text-xs px-3 py-1 rounded-full border border-white/10 bg-white/5">
            Neon UI mode
          </span>
        </div>
      </div>

      {/* Modules grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {modules.map((m) => (
          <Link
            key={m.href}
            href={m.href}
            className="neon-card rounded-2xl p-5 hover:neon-glow transition"
          >
            <div className="flex items-center justify-between">
              <div className="text-lg font-semibold">{m.title}</div>
              <div className="text-[10px] px-2 py-1 rounded-full border border-white/10 bg-white/5 text-[color:var(--muted)]">
                {m.tag}
              </div>
            </div>
            <div className="mt-2 text-sm text-[color:var(--muted)]">{m.desc}</div>
            <div className="mt-4 text-sm text-[color:var(--cyan)]">Open →</div>
          </Link>
        ))}
      </div>

      {/* Quick command hint */}
      <div className="neon-card rounded-2xl p-5">
        <div className="text-sm font-semibold">Quick start</div>
        <div className="mt-2 text-sm text-[color:var(--muted)]">
          Go to <span className="text-[color:var(--cyan)]">Jarvis</span> and try:
        </div>
        <pre className="mt-3 text-xs overflow-auto rounded-xl border border-white/10 bg-black/30 p-3">
Add a winning product and prepare it to sell
        </pre>
      </div>
    </div>
  );
}
