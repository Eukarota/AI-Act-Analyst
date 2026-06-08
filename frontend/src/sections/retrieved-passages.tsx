"use client";

import { useTranslation } from "@/lib/language";
import type { RetrievedPassage } from "@/lib/types";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { CitationChip } from "@/components/citation-chip";

export function RetrievedPassagesList({
  passages,
}: {
  passages: RetrievedPassage[];
}) {
  const { t } = useTranslation();

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {t("report.retrieved.heading")}
          <span className="ml-2 text-foreground-dim">{passages.length}</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {passages.length === 0 ? (
          <p className="text-sm text-foreground-muted">{t("report.retrieved.empty")}</p>
        ) : (
          <ul className="space-y-3">
            {passages.map((p, i) => (
              <li
                key={i}
                className="rounded-xl bg-white/[0.02] ring-1 ring-inset ring-white/[0.05] px-4 py-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                  <CitationChip citation={p.citation} />
                  <span className="text-[11px] text-foreground-dim">
                    {t("report.retrieved.score")} {p.score.toFixed(3)}
                    {p.retrieval_scope ? ` · ${p.retrieval_scope}` : ""}
                  </span>
                </div>
                <p className="text-[12px] text-foreground-muted leading-relaxed whitespace-pre-wrap">
                  {p.text}
                </p>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
