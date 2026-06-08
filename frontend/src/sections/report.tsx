"use client";

import { motion } from "framer-motion";

import type { AssessmentReport } from "@/lib/types";
import { ReportHeader } from "@/sections/report-header";
import { ClassificationCard } from "@/sections/classification-card";
import { ObligationsList } from "@/sections/obligations-list";
import { GapsList } from "@/sections/gaps-list";
import { DraftedDocsList } from "@/sections/drafted-docs-list";
import { RetrievedPassagesList } from "@/sections/retrieved-passages";
import { TracePanel } from "@/sections/trace-panel";
import { ClarificationsList } from "@/sections/clarifications";
import { FailuresList } from "@/sections/failures";

interface Props {
  report: AssessmentReport;
}

const fade = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] as const },
};

export function Report({ report }: Props) {
  return (
    <section id="report" className="border-b border-white/[0.06]">
      <div className="mx-auto max-w-6xl px-6 py-16 space-y-8">
        <motion.div {...fade}>
          <ReportHeader report={report} />
        </motion.div>

        <motion.div {...fade} transition={{ ...fade.transition, delay: 0.05 }}>
          <FailuresList failures={report.failures} />
        </motion.div>

        <motion.div {...fade} transition={{ ...fade.transition, delay: 0.05 }}>
          <ClarificationsList questions={report.clarification_questions} />
        </motion.div>

        <div className="grid gap-6 lg:grid-cols-2">
          {report.classification && (
            <motion.div {...fade} transition={{ ...fade.transition, delay: 0.1 }}>
              <ClassificationCard classification={report.classification} />
            </motion.div>
          )}
          <motion.div {...fade} transition={{ ...fade.transition, delay: 0.15 }}>
            <ObligationsList obligations={report.obligations} />
          </motion.div>
          <motion.div {...fade} transition={{ ...fade.transition, delay: 0.2 }}>
            <GapsList gaps={report.gaps} />
          </motion.div>
          <motion.div {...fade} transition={{ ...fade.transition, delay: 0.25 }}>
            <DraftedDocsList documents={report.drafted_documents} />
          </motion.div>
        </div>

        <motion.div {...fade} transition={{ ...fade.transition, delay: 0.3 }}>
          <TracePanel runId={report.run_id} />
        </motion.div>

        <motion.div {...fade} transition={{ ...fade.transition, delay: 0.35 }}>
          <RetrievedPassagesList passages={report.retrieved_passages} />
        </motion.div>
      </div>
    </section>
  );
}
