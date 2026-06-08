"use client";

import { useTranslation } from "@/lib/language";
import type { ClarificationQuestion } from "@/lib/types";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

interface Props {
  questions: ClarificationQuestion[];
}

export function ClarificationsList({ questions }: Props) {
  const { t } = useTranslation();
  if (questions.length === 0) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("report.clarifications.heading")}</CardTitle>
        <p className="mt-1 text-[12px] text-foreground-dim">
          {t("report.clarifications.intro")}
        </p>
      </CardHeader>
      <CardContent>
        <ul className="space-y-3">
          {questions.map((q, i) => (
            <li
              key={i}
              className="rounded-xl bg-white/[0.02] ring-1 ring-inset ring-white/[0.05] px-4 py-3"
            >
              <span className="block text-[11px] text-foreground-dim mb-0.5">
                {q.attribute}
              </span>
              <p className="text-sm text-foreground">{q.question}</p>
              <p className="mt-2 text-[12px] text-foreground-muted leading-relaxed">
                ↳ {q.why_it_matters}
              </p>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
