"use client";

import { useTranslation } from "@/lib/language";
import type { TypedFailure } from "@/lib/types";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function FailuresList({ failures }: { failures: TypedFailure[] }) {
  const { t } = useTranslation();
  if (failures.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("report.failures.heading")}</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-3">
          {failures.map((f, i) => (
            <li
              key={i}
              className="rounded-xl bg-[color:var(--danger)]/[0.06] ring-1 ring-inset ring-[color:var(--danger)]/[0.25] px-4 py-3"
            >
              <div className="flex flex-wrap items-center gap-2 mb-1">
                <Badge tone="danger">{f.code}</Badge>
                {f.node && (
                  <span className="text-[11px] text-foreground-dim">{f.node}</span>
                )}
              </div>
              <p className="text-sm text-foreground-muted">{f.message}</p>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
