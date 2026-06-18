"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown } from "lucide-react";

import { useTranslation } from "@/lib/language";
import type { AssessmentReport, GapFinding, Tier } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { TierPill } from "@/components/tier-pill";

interface Props {
  report: AssessmentReport;
}

type HeadlineKey =
  | "prohibited"
  | "undetermined"
  | "minimal"
  | "no_declared_controls"
  | "compliant"
  | "partial"
  | "non_compliant";

type HeadlineTone = "danger" | "warning" | "success" | "info" | "muted";

interface Headline {
  key: HeadlineKey;
  tone: HeadlineTone;
  /** Filled into a `{n}` placeholder where present in the i18n string. */
  count?: number;
}

function deriveHeadline(report: AssessmentReport): Headline {
  const tier: Tier | undefined = report.classification?.tier;

  if (tier === "prohibited") {
    return { key: "prohibited", tone: "danger" };
  }
  if (tier === "minimal") {
    return { key: "minimal", tone: "success" };
  }
  if (!tier || tier === "undetermined") {
    return { key: "undetermined", tone: "muted" };
  }

  const gaps: GapFinding[] = report.gaps ?? [];
  const obligations = report.obligations ?? [];

  // No declared controls = nothing to gap against. Don't claim compliance.
  if (
    obligations.length > 0 &&
    (report.system_profile.declared_controls?.length ?? 0) === 0
  ) {
    return { key: "no_declared_controls", tone: "warning" };
  }

  const missing = gaps.filter((g) => g.status === "missing").length;
  const partial = gaps.filter((g) => g.status === "partial").length;
  const unclear = gaps.filter((g) => g.status === "unclear").length;

  if (missing > 0) {
    return { key: "non_compliant", tone: "danger", count: missing };
  }
  if (partial > 0 || unclear > 0) {
    return { key: "partial", tone: "warning", count: partial + unclear };
  }
  return { key: "compliant", tone: "success", count: gaps.length };
}

const TONE_TO_TEXT_CLASS: Record<HeadlineTone, string> = {
  danger: "text-[color:var(--danger)]",
  warning: "text-[color:var(--warning)]",
  success: "text-[color:var(--success)]",
  info: "text-foreground",
  muted: "text-foreground-muted",
};

export function ReportHeader({ report }: Props) {
  const { t } = useTranslation();
  const [showManifest, setShowManifest] = useState(false);
  const status = t(`report.header_status.${report.status}`);

  const headline = deriveHeadline(report);
  const headlineText = t(`report.headline.${headline.key}`).replace(
    "{n}",
    String(headline.count ?? ""),
  );

  return (
    <div className="rounded-3xl bg-card/60 ring-1 ring-inset ring-white/[0.06] p-8 backdrop-blur-xl">
      <div className="flex flex-wrap items-start justify-between gap-6">
        <div className="min-w-0">
          <div className="flex items-center gap-2 mb-3">
            <span className="text-[11px] text-foreground-dim">
              {t("report.header_eyebrow")}
            </span>
            <span className="text-[11px] text-foreground-dim">·</span>
            <span className="text-[11px] text-foreground-dim">{status}</span>
          </div>
          <h2
            className={`text-3xl sm:text-4xl font-semibold tracking-tight leading-[1.1] ${TONE_TO_TEXT_CLASS[headline.tone]}`}
          >
            {headlineText}
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

      <div className="mt-6">
        <button
          type="button"
          onClick={() => setShowManifest((v) => !v)}
          className="inline-flex items-center gap-1.5 text-[11px] text-foreground-dim hover:text-foreground-muted transition-colors"
        >
          <ChevronDown
            className={`h-3.5 w-3.5 transition-transform duration-300 ${
              showManifest ? "rotate-180" : ""
            }`}
          />
          {showManifest ? t("report.manifest_hide") : t("report.manifest_show")}
        </button>
        <AnimatePresence initial={false}>
          {showManifest && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
              className="overflow-hidden"
            >
              <div className="mt-4 grid grid-cols-1 gap-x-8 gap-y-3 text-[12px] sm:grid-cols-2 lg:grid-cols-3">
                <ManifestRow
                  label={t("report.manifest_fields.run_id")}
                  value={report.manifest.run_id}
                  mono
                />
                <ManifestRow
                  label={t("report.manifest_fields.model_id")}
                  value={report.manifest.model_id}
                />
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
              <p className="mt-6 text-[12px] text-foreground-dim leading-relaxed max-w-3xl">
                {report.pre_assessment_notice}
              </p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
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
