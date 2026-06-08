"use client";

import { useState, useEffect, useRef } from "react";

import type { AssessmentReport } from "@/lib/types";
import { Nav } from "@/sections/nav";
import { Hero } from "@/sections/hero";
import { Intake } from "@/sections/intake";
import { Report } from "@/sections/report";

export default function Home() {
  const [report, setReport] = useState<AssessmentReport | null>(null);
  const reportRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (report && reportRef.current) {
      reportRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [report]);

  return (
    <main className="min-h-screen bg-background">
      <Nav />
      <Hero />
      <Intake
        onResult={setReport}
        hasResult={report !== null}
        onReset={() => setReport(null)}
      />
      <div ref={reportRef}>{report && <Report report={report} />}</div>
      <Footer />
    </main>
  );
}

function Footer() {
  return (
    <footer className="border-t border-white/[0.06]">
      <div className="mx-auto max-w-6xl px-6 py-10 text-[12px] text-foreground-dim">
        Boussole · Sovereign EU AI Act pre-assessment ·{" "}
        <a
          className="underline-offset-4 hover:underline"
          href="https://eur-lex.europa.eu/eli/reg/2024/1689/oj"
          target="_blank"
          rel="noreferrer noopener"
        >
          Regulation (EU) 2024/1689
        </a>
      </div>
    </footer>
  );
}
