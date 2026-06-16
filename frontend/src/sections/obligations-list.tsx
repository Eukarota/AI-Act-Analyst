"use client";

import { useTranslation } from "@/lib/language";
import type { Obligation } from "@/lib/types";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { CitationChip } from "@/components/citation-chip";

interface Props {
  obligations: Obligation[];
}

export function ObligationsList({ obligations }: Props) {
  const { t } = useTranslation();
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {t("report.obligations.heading")}
          <span className="ml-2 text-foreground-dim">{obligations.length}</span>
        </CardTitle>
        <p className="mt-1 text-[12px] text-foreground-dim leading-relaxed">
          {t("report.obligations.subhead")}
        </p>
      </CardHeader>
      <CardContent>
        {obligations.length === 0 ? (
          <p className="text-sm text-foreground-muted">{t("report.obligations.empty")}</p>
        ) : (
          <ul className="space-y-3">
            {obligations.map((o) => (
              <li
                key={o.obligation_id}
                className="rounded-xl bg-white/[0.02] ring-1 ring-inset ring-white/[0.05] px-4 py-3"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <span className="block text-[11px] text-foreground-dim mb-0.5">
                      {o.article_ref}
                    </span>
                    <p className="text-sm text-foreground-muted leading-snug">
                      {o.summary}
                    </p>
                  </div>
                  <CitationChip citation={o.citation} />
                </div>
                {o.applies_to.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {o.applies_to.map((role) => (
                      <span
                        key={role}
                        className="text-[11px] text-foreground-dim"
                      >
                        · {role}
                      </span>
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
