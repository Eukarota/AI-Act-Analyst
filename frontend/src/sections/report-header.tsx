"use client";

import { useTranslation } from "@/lib/language";
import type { AssessmentReport } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { TierPill } from "@/components/tier-pill";

interface Props {
  report: AssessmentReport;
}

export function ReportHeader({ report }: Props) {
  const { t } = useTranslation();
  const status = t(`report.header_status.${report.status}`);

  return (
    <div className="rounded-3xl bg-card/60 ring-1 ring-inset ring-white/[0.06] p-8 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div>
          <span className="text-[11px] text-foreground-dim">
            {t("report.header_eyebrow")}
          </span>
          <h2 className="mt-2 text-3xl sm:text-4xl font-semibold tracking-tight">
            {status}
          </h2>
          {report.classification && (
            <div className="mt-4">
              <TierPill tier={report.classification.tier} />
            </div>
          )}
        </div>
        <Badge tone={report.grounding_passed ? "success" : "danger"}>
          {report.grounding_passed
            ? t("report.grounding_pass")
            : t("report.grounding_fail")}
        </Badge>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-x-8 gap-y-3 text-[12px] sm:grid-cols-2 lg:grid-cols-3">
        <ManifestRow label={t("report.manifest_fields.run_id")} value={report.manifest.run_id} mono />
        <ManifestRow label={t("report.manifest_fields.model_id")} value={report.manifest.model_id} />
        <ManifestRow
          label={t("report.manifest_fields.corpus_version")}
          value={report.manifest.corpus_version}
        />
        <ManifestRow
          label={t("report.manifest_fields.prompt_set_version")}
          value={report.manifest.prompt_set_version}
        />
        <ManifestRow
          label={t("report.manifest_fields.rules_version")}
          value={report.manifest.rules_version}
        />
        <ManifestRow
          label={t("report.manifest_fields.timestamp")}
          value={new Date(report.manifest.timestamp).toLocaleString()}
        />
      </div>

      <p className="mt-8 text-[12px] text-foreground-dim leading-relaxed max-w-3xl">
        {report.pre_assessment_notice}
      </p>
    </div>
  );
}

function ManifestRow({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-foreground-dim">{label}</span>
      <span className={mono ? "text-foreground-muted truncate" : "text-foreground-muted"}>
        {value}
      </span>
    </div>
  );
}
