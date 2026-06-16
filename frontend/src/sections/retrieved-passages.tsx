"use client";

import { useTranslation } from "@/lib/language";
import type { AssessmentReport, Citation, RetrievedPassage } from "@/lib/types";
import { eurLexUrl } from "@/lib/api";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

function citationKey(c: Citation): string {
  return [c.celex_id, c.article ?? "", c.paragraph ?? "", c.annex_ref ?? "", c.recital_ref ?? ""].join(
    "|",
  );
}

function citedCitationKeys(report: AssessmentReport): Set<string> {
  const keys = new Set<string>();
  if (report.classification) {
    for (const c of report.classification.supporting_refs) keys.add(citationKey(c));
  }
  for (const o of report.obligations) keys.add(citationKey(o.citation));
  for (const d of report.drafted_documents) for (const c of d.citations) keys.add(citationKey(c));
  return keys;
}

function citationLabel(c: Citation): string {
  if (c.article) {
    const para = c.paragraph ? `(${c.paragraph})` : "";
    return `Art. ${c.article}${para}`;
  }
  if (c.annex_ref) return `Annex ${c.annex_ref}`;
  if (c.recital_ref) return `Recital ${c.recital_ref}`;
  return c.celex_id;
}

interface Props {
  report: AssessmentReport;
}

export function RetrievedPassagesList({ report }: Props) {
  const { t } = useTranslation();
  const passages = report.retrieved_passages;
  const cited = citedCitationKeys(report);

  // Group passages by scope so the user sees what each retrieval call asked
  // for and what came back.
  const byScope = new Map<string, RetrievedPassage[]>();
  for (const p of passages) {
    const scope = p.retrieval_scope ?? "_unscoped";
    if (!byScope.has(scope)) byScope.set(scope, []);
    byScope.get(scope)!.push(p);
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <CardTitle>
            {t("report.retrieved.heading")}
            <span className="ml-2 text-foreground-dim text-sm font-normal">{passages.length}</span>
          </CardTitle>
          <span className="text-[12px] text-foreground-dim">{t("report.retrieved.subhead")}</span>
        </div>
      </CardHeader>
      <CardContent>
        {passages.length === 0 ? (
          <p className="text-sm text-foreground-muted">{t("report.retrieved.empty")}</p>
        ) : (
          <div className="space-y-6">
            {Array.from(byScope.entries()).map(([scope, items]) => (
              <div key={scope}>
                <div className="flex flex-wrap items-baseline gap-2 mb-2">
                  <span className="text-[11px] uppercase tracking-wide text-foreground-dim">
                    {t("report.retrieved.scope")}
                  </span>
                  <span className="text-[13px] text-foreground-muted font-mono">{scope}</span>
                  <span className="text-[11px] text-foreground-dim ml-auto">
                    {items.length} {t("report.retrieved.passage_count")}
                  </span>
                </div>
                <ul className="space-y-3">
                  {items.map((p, i) => {
                    const key = citationKey(p.citation);
                    const isCited = cited.has(key);
                    const href = p.citation.url ?? eurLexUrl();
                    return (
                      <li
                        key={`${scope}-${i}`}
                        className={`rounded-xl px-4 py-3 ring-1 ring-inset transition-colors ${
                          isCited
                            ? "bg-[color:var(--accent)]/[0.06] ring-[color:var(--accent)]/30"
                            : "bg-white/[0.02] ring-white/[0.05]"
                        }`}
                      >
                        <div className="flex flex-wrap items-center gap-2 mb-2">
                          <Badge tone="muted">#{i + 1}</Badge>
                          <span className="text-[13px] font-medium text-foreground">
                            {citationLabel(p.citation)}
                          </span>
                          {isCited && (
                            <Badge tone="success">{t("report.retrieved.cited_in_report")}</Badge>
                          )}
                          <a
                            href={href}
                            target="_blank"
                            rel="noreferrer noopener"
                            className="ml-auto text-[11px] text-foreground-dim hover:text-foreground underline-offset-4 hover:underline"
                          >
                            {t("report.retrieved.source_link")}
                          </a>
                        </div>
                        <blockquote className="border-l-2 border-white/[0.08] pl-3 text-[13px] text-foreground-muted leading-relaxed whitespace-pre-wrap">
                          {p.text}
                        </blockquote>
                      </li>
                    );
                  })}
                </ul>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
