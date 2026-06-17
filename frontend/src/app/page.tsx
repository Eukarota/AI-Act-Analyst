"use client";

import { useState, useEffect, useRef } from "react";

import type { AssessmentReport } from "@/lib/types";
import { postAssess, type AssessPayload } from "@/lib/api";
import { Nav } from "@/sections/nav";
import { Intake } from "@/sections/intake";
import { Report } from "@/sections/report";
import { TracePanel } from "@/sections/trace-panel";
import { RagCube } from "@/sections/rag-cube";
import { Footer } from "@/sections/footer";

export default function Home() {
  const [report, setReport] = useState<AssessmentReport | null>(null);
  const [lastPayload, setLastPayload] = useState<AssessPayload | null>(null);
  const reportRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (report && reportRef.current) {
      reportRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [report]);

  const handleResult = (next: AssessmentReport, payload: AssessPayload) => {
    setReport(next);
    setLastPayload(payload);
  };

  const handleReset = () => {
    setReport(null);
    setLastPayload(null);
  };

  // Take the clarification answers, append them to the system description
  // as a structured Q&A block, and re-submit. The agent re-runs extraction;
  // attributes it can now infer from the appended text no longer trigger
  // the clarify loop.
  const handleContinueWithAnswers = async (answers: Record<string, string>) => {
    if (!lastPayload) return;
    const qaBlock = Object.entries(answers)
      .map(([k, v]) => `- ${k}: ${v.trim()}`)
      .join("\n");
    const newDescription = `${lastPayload.system_description}\n\nClarifications:\n${qaBlock}`;
    const newPayload: AssessPayload = { ...lastPayload, system_description: newDescription };
    const response = await postAssess(newPayload);
    setReport(response.report);
    setLastPayload(newPayload);
  };

  return (
    <main className="min-h-screen bg-background flex flex-col">
      <Nav />
      {report === null ? (
        <div className="mx-auto w-full max-w-3xl px-6 pt-24 pb-32 flex-1 flex flex-col justify-center">
          <Intake onResult={handleResult} />
        </div>
      ) : (
        <div
          ref={reportRef}
          className="mx-auto w-full max-w-[1400px] px-6 py-10 grid gap-10 lg:grid-cols-[minmax(0,1fr)_380px]"
        >
          <div className="min-w-0 space-y-6">
            <Report
              report={report}
              onReset={handleReset}
              onContinueWithAnswers={handleContinueWithAnswers}
            />
          </div>
          <aside className="lg:sticky lg:top-24 lg:self-start lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto pr-1 space-y-4">
            <RagCube
              retrievedPassages={report.retrieved_passages}
              corpusVersion={report.manifest.corpus_version}
            />
            <TracePanel runId={report.run_id} />
          </aside>
        </div>
      )}
      <Footer />
    </main>
  );
}
