"use client";

import { motion } from "framer-motion";

import { useTranslation } from "@/lib/language";
import type { AssessmentReport } from "@/lib/types";
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
      <div className="flex items-center justify-between gap-3">
        <p className="text-[12px] text-foreground-dim italic max-w-2xl leading-relaxed">
          &ldquo;{report.system_profile.description}&rdquo;
        </p>
        <Button type="button" variant="subtle" size="sm" onClick={onReset}>
          {t("intake.reset")}
        </Button>
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
          <motion.div {...fade} transition={{ ...fade.transition, delay: 0.15 }}>
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
