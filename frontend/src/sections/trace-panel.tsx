"use client";

import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

import { useTranslation } from "@/lib/language";
import type { TraceEvent } from "@/lib/types";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface Props {
  runId: string;
}

const KIND_TONE: Record<string, "muted" | "info" | "warning" | "danger" | "success"> = {
  node_start: "muted",
  node_end: "muted",
  tool_call: "info",
  tool_return: "info",
  llm_call: "info",
  retrieval: "info",
  classification: "warning",
  grounding_check: "success",
  clarification: "warning",
  error: "danger",
};

export function TracePanel({ runId }: Props) {
  const { t, raw } = useTranslation();
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [expanded, setExpanded] = useState(true);
  const [openIds, setOpenIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`/api/trace/${runId}`);
        if (!res.ok) return;
        const body = (await res.json()) as { events: TraceEvent[] };
        if (!cancelled) {
          setEvents(body.events ?? []);
          setLoaded(true);
        }
      } catch {
        if (!cancelled) setLoaded(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [runId]);

  const summary = useMemo(() => {
    const nodes = events.filter((e) => e.kind === "node_start");
    return { node_count: nodes.length, total: events.length };
  }, [events]);

  const kindLabels = (raw<Record<string, string>>("report.trace.kinds") ?? {}) as Record<
    string,
    string
  >;

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <CardTitle>{t("report.trace.heading")}</CardTitle>
            <p className="mt-1 text-[12px] text-foreground-dim">{t("report.trace.subhead")}</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge tone="muted">
              {summary.node_count} · {summary.total}
            </Badge>
            <Button
              type="button"
              variant="subtle"
              size="sm"
              onClick={() => setExpanded((e) => !e)}
            >
              {expanded ? t("report.trace.collapse") : t("report.trace.expand")}
            </Button>
          </div>
        </div>
      </CardHeader>
      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
            className="overflow-hidden"
          >
            <CardContent>
              {!loaded ? (
                <p className="text-sm text-foreground-dim">…</p>
              ) : events.length === 0 ? (
                <p className="text-sm text-foreground-muted">{t("report.trace.empty")}</p>
              ) : (
                <ol className="relative space-y-2 pl-6">
                  <span
                    className="absolute left-2 top-2 bottom-2 w-px bg-white/[0.06]"
                    aria-hidden
                  />
                  {events.map((event) => {
                    const isOpen = openIds.has(event.event_id);
                    return (
                      <li key={event.event_id} className="relative">
                        <span
                          aria-hidden
                          className="absolute -left-[18px] top-3 h-1.5 w-1.5 rounded-full bg-foreground-muted"
                        />
                        <button
                          type="button"
                          onClick={() =>
                            setOpenIds((prev) => {
                              const next = new Set(prev);
                              if (next.has(event.event_id)) next.delete(event.event_id);
                              else next.add(event.event_id);
                              return next;
                            })
                          }
                          className="flex w-full items-start justify-between gap-3 rounded-lg px-3 py-2 text-left transition-colors hover:bg-white/[0.03]"
                        >
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <Badge tone={KIND_TONE[event.kind] ?? "muted"}>
                                {kindLabels[event.kind] ?? event.kind}
                              </Badge>
                              <span className="text-sm text-foreground">{event.name}</span>
                            </div>
                            {(event.latency_ms != null ||
                              event.tokens_in != null ||
                              event.tokens_out != null ||
                              event.model_id) && (
                              <div className="mt-1 flex flex-wrap gap-3 text-[11px] text-foreground-dim">
                                {event.latency_ms != null && (
                                  <span>
                                    {t("report.trace.latency")} ·{" "}
                                    {event.latency_ms.toFixed(1)} ms
                                  </span>
                                )}
                                {event.model_id && <span>{event.model_id}</span>}
                                {event.tokens_in != null && <span>in {event.tokens_in}</span>}
                                {event.tokens_out != null && <span>out {event.tokens_out}</span>}
                              </div>
                            )}
                          </div>
                        </button>
                        <AnimatePresence initial={false}>
                          {isOpen && Object.keys(event.attributes).length > 0 && (
                            <motion.pre
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: "auto", opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              transition={{
                                duration: 0.2,
                                ease: [0.16, 1, 0.3, 1],
                              }}
                              className="overflow-hidden whitespace-pre-wrap rounded-lg bg-black/40 ml-3 mt-1 mb-2 p-3 text-[11px] leading-relaxed text-foreground-muted ring-1 ring-inset ring-white/[0.05]"
                            >
                              {JSON.stringify(event.attributes, null, 2)}
                            </motion.pre>
                          )}
                        </AnimatePresence>
                      </li>
                    );
                  })}
                </ol>
              )}
            </CardContent>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}
