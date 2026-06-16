"use client";

import { useState } from "react";

import { useTranslation } from "@/lib/language";
import type { ClarificationQuestion } from "@/lib/types";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface Props {
  questions: ClarificationQuestion[];
  iterations: number;
  onContinueWithAnswers: (answers: Record<string, string>) => Promise<void>;
}

export function ClarificationsList({ questions, iterations, onContinueWithAnswers }: Props) {
  const { t, raw } = useTranslation();
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (questions.length === 0) return null;

  // The agent runs the clarify loop up to 3 times and may emit the same
  // attribute on each iteration. Dedupe by attribute name; show how many
  // iterations ran via the badge.
  const dedup = new Map<string, ClarificationQuestion>();
  for (const q of questions) {
    if (!dedup.has(q.attribute)) dedup.set(q.attribute, q);
  }
  const unique = Array.from(dedup.values());

  const localizedQuestion = (attribute: string, fallback: string) =>
    raw<string>(`report.clarifications.questions.${attribute}`) ?? fallback;
  const localizedWhy = (attribute: string, fallback: string) =>
    raw<string>(`report.clarifications.why.${attribute}`) ?? fallback;

  const handleSubmit = async () => {
    const filled = Object.fromEntries(
      Object.entries(answers).filter(([, v]) => v.trim().length > 0),
    );
    if (Object.keys(filled).length === 0) {
      setError(t("report.clarifications.missing_answer"));
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await onContinueWithAnswers(filled);
      setAnswers({});
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <CardTitle>{t("report.clarifications.heading")}</CardTitle>
          {iterations > 0 && (
            <Badge tone="warning">
              {iterations} {t("report.clarifications.iterations_label")}
            </Badge>
          )}
        </div>
        <p className="mt-1 text-[12px] text-foreground-dim">{t("report.clarifications.intro")}</p>
      </CardHeader>
      <CardContent className="space-y-4">
        <ul className="space-y-3">
          {unique.map((q) => (
            <li
              key={q.attribute}
              className="rounded-xl bg-white/[0.02] ring-1 ring-inset ring-white/[0.05] px-4 py-3 space-y-2"
            >
              <span className="block text-[11px] text-foreground-dim font-mono">{q.attribute}</span>
              <p className="text-sm text-foreground">
                {localizedQuestion(q.attribute, q.question)}
              </p>
              <p className="text-[12px] text-foreground-muted leading-relaxed">
                {localizedWhy(q.attribute, q.why_it_matters)}
              </p>
              <Textarea
                rows={2}
                placeholder={t("report.clarifications.answer_placeholder")}
                value={answers[q.attribute] ?? ""}
                onChange={(e) =>
                  setAnswers((prev) => ({ ...prev, [q.attribute]: e.target.value }))
                }
                disabled={submitting}
                className="mt-1"
              />
            </li>
          ))}
        </ul>
        {error && (
          <p className="text-[12px] text-[color:var(--danger)]">{error}</p>
        )}
        <div className="flex justify-end">
          <Button type="button" onClick={handleSubmit} disabled={submitting}>
            {submitting ? t("report.clarifications.submitting") : t("report.clarifications.submit")}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
