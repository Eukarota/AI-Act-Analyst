import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-medium tracking-tight ring-1 ring-inset",
  {
    variants: {
      tone: {
        muted: "bg-white/[0.04] text-foreground-muted ring-white/[0.06]",
        success:
          "bg-[color:var(--success)]/10 text-[color:var(--success)] ring-[color:var(--success)]/30",
        warning:
          "bg-[color:var(--warning)]/10 text-[color:var(--warning)] ring-[color:var(--warning)]/30",
        danger:
          "bg-[color:var(--danger)]/10 text-[color:var(--danger)] ring-[color:var(--danger)]/30",
        info: "bg-[color:var(--info)]/10 text-[color:var(--info)] ring-[color:var(--info)]/30",
      },
    },
    defaultVariants: { tone: "muted" },
  },
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

export function Badge({ className, tone, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ tone }), className)} {...props} />;
}
