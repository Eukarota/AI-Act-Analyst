"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { useTranslation } from "@/lib/language";
import type { DraftedDocument } from "@/lib/types";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { CitationChip } from "@/components/citation-chip";
import { Button } from "@/components/ui/button";

interface Props {
  documents: DraftedDocument[];
}

export function DraftedDocsList({ documents }: Props) {
  const { t } = useTranslation();
  const [open, setOpen] = useState<Set<string>>(new Set());

  const toggle = (kind: string) =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(kind)) next.delete(kind);
      else next.add(kind);
      return next;
    });

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {t("report.drafted_documents.heading")}
          <span className="ml-2 text-foreground-dim">{documents.length}</span>
        </CardTitle>
        <p className="mt-1 text-[12px] text-foreground-dim leading-relaxed">
          {t("report.drafted_documents.subhead")}
        </p>
      </CardHeader>
      <CardContent>
        {documents.length === 0 ? (
          <p className="text-sm text-foreground-muted">
            {t("report.drafted_documents.empty")}
          </p>
        ) : (
          <ul className="space-y-3">
            {documents.map((doc) => {
              const isOpen = open.has(doc.kind);
              return (
                <li
                  key={doc.kind}
                  className="rounded-xl bg-white/[0.02] ring-1 ring-inset ring-white/[0.05] px-4 py-3"
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="min-w-0 flex-1">
                      <span className="block text-[11px] text-foreground-dim mb-0.5">
                        {doc.kind}
                      </span>
                      <p className="text-sm text-foreground">{doc.title}</p>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {doc.citations.map((c, i) => (
                          <CitationChip key={i} citation={c} />
                        ))}
                      </div>
                    </div>
                    <Button
                      type="button"
                      variant="subtle"
                      size="sm"
                      onClick={() => toggle(doc.kind)}
                    >
                      {isOpen
                        ? t("report.drafted_documents.preview_close")
                        : t("report.drafted_documents.preview_open")}
                    </Button>
                  </div>
                  <AnimatePresence initial={false}>
                    {isOpen && (
                      <motion.pre
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                        className="mt-3 overflow-hidden whitespace-pre-wrap rounded-lg bg-black/40 p-4 text-[12px] leading-relaxed text-foreground-muted ring-1 ring-inset ring-white/[0.05]"
                      >
                        {doc.body}
                      </motion.pre>
                    )}
                  </AnimatePresence>
                </li>
              );
            })}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}
