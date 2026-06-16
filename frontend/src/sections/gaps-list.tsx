"use client";

import { useTranslation } from "@/lib/language";
import type { GapFinding } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

const STATUS_TONE: Record<string, "success" | "warning" | "danger" | "muted"> = {
  met: "success",
  partial: "warning",
  missing: "danger",
  unclear: "muted",
};

interface Props {
  gaps: GapFinding[];
}

export function GapsList({ gaps }: Props) {
  const { t } = useTranslation();
  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {t("report.gaps.heading")}
          <span className="ml-2 text-foreground-dim">{gaps.length}</span>
        </CardTitle>
        <p className="mt-1 text-[12px] text-foreground-dim leading-relaxed">
          {t("report.gaps.subhead")}
        </p>
      </CardHeader>
      <CardContent>
        {gaps.length === 0 ? (
          <p className="text-sm text-foreground-muted">{t("report.gaps.empty")}</p>
        ) : (
          <ul className="space-y-3">
            {gaps.map((g) => (
              <li
                key={g.obligation_id}
                className="rounded-xl bg-white/[0.02] ring-1 ring-inset ring-white/[0.05] px-4 py-3"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <span className="block text-[11px] text-foreground-dim mb-0.5">
                      {g.obligation_id}
                    </span>
                    {g.notes && (
                      <p className="text-sm text-foreground-muted leading-snug">
                        {g.notes}
                      </p>
                    )}
                    {g.declared_evidence && (
                      <p className="mt-2 text-[12px] text-foreground-dim">
                        ↳ {g.declared_evidence}
                      </p>
                    )}
                  </div>
                  <Badge tone={STATUS_TONE[g.status] ?? "muted"}>
                    {t(`report.gaps.status.${g.status}`, g.status)}
                  </Badge>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
