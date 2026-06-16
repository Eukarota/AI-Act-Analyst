"use client";

import { useTranslation } from "@/lib/language";
import type { ClassificationResult } from "@/lib/types";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { CitationChip } from "@/components/citation-chip";

interface Props {
  classification: ClassificationResult;
}

export function ClassificationCard({ classification }: Props) {
  const { t } = useTranslation();
  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("report.classification.heading")}</CardTitle>
        <p className="mt-1 text-[12px] text-foreground-dim leading-relaxed">
          {t("report.classification.subhead")}
        </p>
      </CardHeader>
      <CardContent className="space-y-5">
        <div>
          <span className="block text-[11px] text-foreground-dim mb-1">
            {t("report.classification.fired_rule")}
          </span>
          <span className="text-sm text-foreground-muted">{classification.fired_rule}</span>
        </div>
        {classification.rationale && (
          <div>
            <span className="block text-[11px] text-foreground-dim mb-1">
              {t("report.classification.rationale")}
            </span>
            <p className="text-sm text-foreground-muted leading-relaxed">
              {classification.rationale}
            </p>
          </div>
        )}
        {classification.supporting_refs.length > 0 && (
          <div>
            <span className="block text-[11px] text-foreground-dim mb-2">
              {t("report.classification.supporting_refs")}
            </span>
            <div className="flex flex-wrap gap-1.5">
              {classification.supporting_refs.map((ref, i) => (
                <CitationChip key={`${ref.celex_id}-${i}`} citation={ref} />
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
