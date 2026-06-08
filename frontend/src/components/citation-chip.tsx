"use client";

import { citationToShort, eurLexUrl } from "@/lib/api";
import type { Citation } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  citation: Citation;
  className?: string;
}

export function CitationChip({ citation, className }: Props) {
  const href = citation.url ?? eurLexUrl();
  return (
    <a
      href={href}
      target="_blank"
      rel="noreferrer noopener"
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full bg-white/[0.04] px-2.5 py-1",
        "text-[12px] font-medium text-foreground-muted tracking-tight",
        "ring-1 ring-inset ring-white/[0.08]",
        "hover:bg-white/[0.08] hover:text-foreground hover:ring-white/[0.16] transition-colors",
        className,
      )}
    >
      <span className="text-[color:var(--accent)]">§</span>
      {citationToShort(citation)}
    </a>
  );
}
