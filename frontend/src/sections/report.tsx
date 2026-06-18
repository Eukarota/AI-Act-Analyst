"use client";

import { motion } from "framer-motion";
import { Download, FileText } from "lucide-react";

import { useTranslation } from "@/lib/language";
import type { AssessmentReport } from "@/lib/types";
import { assessExportUrl } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { ReportHeader } from "@/sections/report-header";
import { ClassificationCard } from "@/sections/classification-card";
import { ObligationsList } from "@/sections/obligations-list";
import { GapsList } from "@/sections/gaps-list";
import { DraftedDocsList } from "@/sections/drafted-docs-list";
import { RetrievedPassagesList } from "@/sections/retrieved-passages";
import { ClarificationsList } from "@/sections/clarifications";
import { FailuresList } from "@/sections/failures";

interface Props {
  report: AssessmentReport;
  onReset: () => void;
  onContinueWithAnswers: (answers: Record<string, string>) => Promise<void>;
}

const fade = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.4, ease: [0.16, 1, 0.3, 1] as const },
};

export function Report({ report, onReset, onContinueWithAnswers }: Props) {
  const { t } = useTranslation();
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <a
            href={assessExportUrl(report.run_id, "pdf")}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 rounded-full bg-white/[0.04] px-3 py-1.5 text-[12px] text-foreground-muted ring-1 ring-inset ring-white/[0.06] hover:bg-white/[0.08] hover:text-foreground transition-colors"
          >
            <Download className="h-3.5 w-3.5" />
            {t("report.export.pdf")}
          </a>
          <a
            href={assessExportUrl(report.run_id, "md")}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 rounded-full bg-white/[0.04] px-3 py-1.5 text-[12px] text-foreground-muted ring-1 ring-inset ring-white/[0.06] hover:bg-white/[0.08] hover:text-foreground transition-colors"
          >
            <FileText className="h-3.5 w-3.5" />
            {t("report.export.md")}
          </a>
          <Button type="button" variant="subtle" size="sm" onClick={onReset}>
            {t("intake.reset")}
          </Button>
        </div>
      </div>

      <motion.div {...fade}>
        <ReportHeader report={report} />
      </motion.div>

      <motion.div {...fade} transition={{ ...fade.transition, delay: 0.05 }}>
        <FailuresList failures={report.failures} />
      </motion.div>

      <motion.div {...fade} transition={{ ...fade.transition, delay: 0.1 }}>
        <ClarificationsList
          questions={report.clarification_questions}
          iterations={report.clarification_iterations}
          onContinueWithAnswers={onContinueWithAnswers}
        />
      </motion.div>

      <div className="grid gap-6 lg:grid-cols-2">
        {report.classification && (
          <motion.div
            {...fade}
            transition={{ ...fade.transition, delay: 0.15 }}
          >
            <ClassificationCard classification={report.classification} />
          </motion.div>
        )}
        <motion.div {...fade} transition={{ ...fade.transition, delay: 0.2 }}>
          <ObligationsList obligations={report.obligations} />
        </motion.div>
        <motion.div {...fade} transition={{ ...fade.transition, delay: 0.25 }}>
          <GapsList gaps={report.gaps} />
        </motion.div>
        <motion.div {...fade} transition={{ ...fade.transition, delay: 0.3 }}>
          <DraftedDocsList documents={report.drafted_documents} />
        </motion.div>
      </div>

      <motion.div {...fade} transition={{ ...fade.transition, delay: 0.35 }}>
        <RetrievedPassagesList report={report} />
      </motion.div>
    </div>
  );
}
