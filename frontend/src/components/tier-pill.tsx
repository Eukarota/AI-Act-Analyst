"use client";

import type { Tier } from "@/lib/types";
import { useTranslation } from "@/lib/language";
import { cn } from "@/lib/utils";

const TONE_CLASS: Record<string, string> = {
  danger:
    "bg-[color:var(--danger)]/12 text-[color:var(--danger)] ring-[color:var(--danger)]/30",
  warning:
    "bg-[color:var(--warning)]/12 text-[color:var(--warning)] ring-[color:var(--warning)]/30",
  info: "bg-[color:var(--info)]/12 text-[color:var(--info)] ring-[color:var(--info)]/30",
  success:
    "bg-[color:var(--success)]/12 text-[color:var(--success)] ring-[color:var(--success)]/30",
  muted: "bg-white/[0.04] text-foreground-muted ring-white/[0.06]",
};

export function TierPill({ tier, className }: { tier: Tier; className?: string }) {
  const { t, raw } = useTranslation();
  const meta = raw<{ label: string; tone: string }>(`tiers.${tier}`);
  const tone = meta?.tone ?? "muted";
  const label = meta?.label ?? t(`tiers.${tier}.label`);
  return (
    <span
      className={cn(
        "inline-flex items-center gap-2 rounded-full px-3 py-1 text-[12px] font-medium tracking-tight ring-1 ring-inset",
        TONE_CLASS[tone],
        className,
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {label}
    </span>
  );
}
