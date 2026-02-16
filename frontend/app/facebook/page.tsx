"use client";

import { useMemo, useState } from "react";
import Card from "../components/Card";
import Badge from "../components/Badge";
import StepList from "../components/StepList";
import { sendCommand } from "../lib/api";
import type { CommandResponse } from "../lib/types";

function NeonInput(props: React.InputHTMLAttributes<HTMLInputElement>) {
  const { className = "", ...rest } = props;
  return (
    <input
      {...rest}
      className={[
        "w-full rounded-2xl border border-white/10 bg-black/30",
        "px-4 py-3 text-sm outline-none",
        "focus:border-cyan-400/40 focus:ring-2 focus:ring-cyan-400/10",
        "placeholder:text-white/30",
        className,
      ].join(" ")}
    />
  );
}

function NeonButton(props: React.ButtonHTMLAttributes<HTMLButtonElement> & { tone?: "cyan" | "violet" | "pink" | "lime" }) {
  const { className = "", tone = "cyan", ...rest } = props;

  const toneClass =
    tone === "cyan"
      ? "border-cyan-300/20 hover:border-cyan-300/35 hover:shadow-[0_0_28px_rgba(34,211,238,0.18)]"
      : tone === "violet"
      ? "border-violet-300/20 hover:border-violet-300/35 hover:shadow-[0_0_28px_rgba(167,139,250,0.18)]"
      : tone === "pink"
      ? "border-pink-300/20 hover:border-pink-300/35 hover:shadow-[0_0_28px_rgba(251,113,133,0.18)]"
      : "border-lime-300/20 hover:border-lime-300/35 hover:shadow-[0_0_28px_rgba(163,230,53,0.18)]";

  return (
    <button
      {...rest}
      className={[
        "rounded-2xl border bg-white/5 px-4 py-3 text-sm transition",
        "hover:bg-white/8 active:scale-[0.99]",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        toneClass,
        className,
      ].join(" ")}
    />
  );
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-[10px] px-2 py-1 rounded-full border border-white/10 bg-white/5 text-white/70">
      {children}
    </span>
  );
}

export default function FacebookPage() {
  const [product, setProduct] = useState("AirBrush Pro Mini Compressor");
  const [commentId, setCommentId] = useState("123");
  const [commentText, setCommentText] = useState("Sure—please share your order number so we can check.");
  const [userId, setUserId] = useState("999");
  const [dmText, setDmText] = useState("Please share your order number and the email used at checkout.");
  const [resp, setResp] = useState<CommandResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const lastRunBadge = useMemo(() => {
    if (!resp) return null;
    const ok = resp.status === "completed";
    return <Badge variant={ok ? "ok" : "warn"}>{resp.status}</Badge>;
  }, [resp]);

  async function run(text: string) {
    setErr(null);
    setResp(null);
    setBusy(true);
    try {
      const r = await sendCommand(text);
      setResp(r);
    } catch (e: any) {
      setErr(String(e?.message || e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      {/* Top neon header */}
      <div className="neon-card rounded-2xl p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-[0.22em] text-white/55">Social Automation</div>
            <div className="mt-1 text-2xl font-semibold">
              Facebook <span className="text-[color:var(--cyan)]">Ops Console</span>
            </div>
            <div className="mt-2 text-sm text-white/60">
              Create posts + reply to comments/DMs. Risky actions are <span className="text-[color:var(--pink)]">queued for approval</span>.
            </div>
          </div>

          <div className="flex flex-wrap gap-2 items-center">
            <Chip>DRY_RUN supported</Chip>
            <Chip>Posts/Replies need approval</Chip>
            <div className="h-10 w-10 rounded-xl border border-white/10 bg-white/5 grid place-items-center">
              ✦
            </div>
          </div>
        </div>
      </div>

      <Card
        title="Facebook Automation"
        right={<Badge variant="warn">post/replies require approval</Badge>}
      >
        {/* Neon grid */}
        <div className="grid lg:grid-cols-2 gap-4">
          {/* Create post */}
          <div className="neon-card rounded-2xl p-4">
            <div className="flex items-center justify-between gap-2">
              <div>
                <div className="text-sm font-semibold">Post Creator</div>
                <div className="text-xs text-white/55 mt-1">Generate a product post and queue it for approval.</div>
              </div>
              <Chip>SOCIAL</Chip>
            </div>

            <div className="mt-4 space-y-2">
              <NeonInput
                value={product}
                onChange={(e) => setProduct(e.target.value)}
                placeholder="Product name..."
              />
              <NeonButton
                disabled={busy}
                onClick={() => run(`Create a Facebook post about product ${product}`)}
                tone="cyan"
                className="w-full"
              >
                {busy ? "Running..." : "Generate + Queue approval"}
              </NeonButton>
            </div>
          </div>

          {/* Reply to comment */}
          <div className="neon-card rounded-2xl p-4">
            <div className="flex items-center justify-between gap-2">
              <div>
                <div className="text-sm font-semibold">Comment Reply</div>
                <div className="text-xs text-white/55 mt-1">Queue a reply to a specific comment ID.</div>
              </div>
              <Chip>SUPPORT</Chip>
            </div>

            <div className="mt-4 grid grid-cols-1 sm:grid-cols-[120px_1fr] gap-2">
              <NeonInput
                value={commentId}
                onChange={(e) => setCommentId(e.target.value)}
                placeholder="Comment ID"
              />
              <NeonInput
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                placeholder="Reply text..."
              />
            </div>

            <NeonButton
              disabled={busy}
              onClick={() => run(`Reply to comment ${commentId} with ${commentText}`)}
              tone="violet"
              className="w-full mt-2"
            >
              {busy ? "Running..." : "Queue approval"}
            </NeonButton>
          </div>

          {/* Reply to DM */}
          <div className="neon-card rounded-2xl p-4 lg:col-span-2">
            <div className="flex items-center justify-between gap-2">
              <div>
                <div className="text-sm font-semibold">DM Reply</div>
                <div className="text-xs text-white/55 mt-1">Queue a reply to a user message (DM).</div>
              </div>
              <Chip>INBOX</Chip>
            </div>

            <div className="mt-4 grid grid-cols-1 sm:grid-cols-[140px_1fr] gap-2">
              <NeonInput
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="User ID"
              />
              <NeonInput
                value={dmText}
                onChange={(e) => setDmText(e.target.value)}
                placeholder="DM reply text..."
              />
            </div>

            <NeonButton
              disabled={busy}
              onClick={() => run(`Reply to message from user ${userId} ${dmText}`)}
              tone="pink"
              className="w-full mt-2"
            >
              {busy ? "Running..." : "Queue approval"}
            </NeonButton>
          </div>

          {/* Generate batch */}
          <div className="neon-card rounded-2xl p-4 lg:col-span-2">
            <div className="flex items-center justify-between gap-2">
              <div>
                <div className="text-sm font-semibold">Batch Generator</div>
                <div className="text-xs text-white/55 mt-1">Generate 7 posts and queue them for approval.</div>
              </div>
              <Chip>7 POSTS</Chip>
            </div>

            <div className="mt-3 flex flex-col sm:flex-row gap-2">
              <NeonButton
                disabled={busy}
                onClick={() => run("Generate 7 posts and queue for approval")}
                tone="lime"
                className="w-full"
              >
                {busy ? "Running..." : "Generate + Queue"}
              </NeonButton>
              <div className="text-xs text-white/55 sm:w-[320px] self-center">
                Tip: Approve queued actions in <span className="text-[color:var(--cyan)]">Approvals</span>.
              </div>
            </div>
          </div>
        </div>

        {err ? (
          <div className="mt-3 neon-card rounded-2xl p-3 border border-pink-400/20">
            <div className="text-xs text-pink-200">{err}</div>
          </div>
        ) : null}
      </Card>

      {resp ? (
        <Card title={`Run #${resp.run_id}`} right={lastRunBadge}>
          <p className="text-sm text-white/80">{resp.summary}</p>
        </Card>
      ) : null}

      {resp?.steps ? <StepList steps={resp.steps} /> : null}
    </div>
  );
}
