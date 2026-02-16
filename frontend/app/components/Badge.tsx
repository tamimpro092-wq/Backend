import { clsx } from "../lib/util";

export default function Badge({
  children,
  variant = "neutral"
}: {
  children: React.ReactNode;
  variant?: "neutral" | "ok" | "warn" | "danger";
}) {
  const base = "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium border";
  const styles =
    variant === "ok"
      ? "bg-emerald-900/30 border-emerald-700 text-emerald-200"
      : variant === "warn"
      ? "bg-amber-900/30 border-amber-700 text-amber-200"
      : variant === "danger"
      ? "bg-rose-900/30 border-rose-700 text-rose-200"
      : "bg-slate-900/30 border-slate-700 text-slate-200";
  return <span className={clsx(base, styles)}>{children}</span>;
}
