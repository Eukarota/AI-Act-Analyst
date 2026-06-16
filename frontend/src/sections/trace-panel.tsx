"use client";

import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

import { useTranslation } from "@/lib/language";
import type { TraceEvent } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

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

const FILTERS = ["all", "retrieval", "llm", "classification", "errors"] as const;
type Filter = (typeof FILTERS)[number];

function matchesFilter(event: TraceEvent, filter: Filter): boolean {
  switch (filter) {
    case "all":
      return true;
    case "retrieval":
      return event.kind === "retrieval";
    case "llm":
      return event.kind === "llm_call";
    case "classification":
      return event.kind === "classification" || event.kind === "grounding_check";
    case "errors":
      return event.kind === "error";
  }
}

export function TracePanel({ runId }: Props) {
  const { t, raw } = useTranslation();
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [openIds, setOpenIds] = useState<Set<string>>(new Set());
  const [filter, setFilter] = useState<Filter>("all");

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

  const filtered = useMemo(() => events.filter((e) => matchesFilter(e, filter)), [events, filter]);

  const kindLabels = (raw<Record<string, string>>("report.trace.kinds") ?? {}) as Record<
    string,
    string
  >;
  const filterLabels = (raw<Record<string, string>>("report.trace.filters") ?? {}) as Record<
    string,
    string
  >;

  return (
    <div className="space-y-4">
      <div>
        <div className="flex flex-wrap items-baseline justify-between gap-2">
          <h2 className="text-[13px] font-semibold tracking-wide uppercase text-foreground-muted">
            {t("report.trace.heading")}
          </h2>
          <Badge tone="muted">
            {summary.node_count} · {summary.total}
          </Badge>
        </div>
        <p className="mt-1 text-[12px] text-foreground-dim leading-relaxed">
          {t("report.trace.subhead")}
        </p>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {FILTERS.map((f) => {
          const active = filter === f;
          return (
            <button
              key={f}
              type="button"
              onClick={() => setFilter(f)}
              className={`rounded-full px-2.5 py-1 text-[11px] transition-colors ${
                active
                  ? "bg-white/[0.12] text-foreground ring-1 ring-inset ring-white/[0.18]"
                  : "bg-white/[0.03] text-foreground-dim ring-1 ring-inset ring-white/[0.05] hover:bg-white/[0.06] hover:text-foreground-muted"
              }`}
            >
              {filterLabels[f] ?? f}
            </button>
          );
        })}
      </div>

      {!loaded ? (
        <p className="text-sm text-foreground-dim">…</p>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-foreground-muted">{t("report.trace.empty")}</p>
      ) : (
        <ol className="relative space-y-1 pl-5">
          <span className="absolute left-1.5 top-2 bottom-2 w-px bg-white/[0.06]" aria-hidden />
          {filtered.map((event) => {
            const isOpen = openIds.has(event.event_id);
            return (
              <li key={event.event_id} className="relative">
                <span
                  aria-hidden
                  className={`absolute -left-[14px] top-[10px] h-1.5 w-1.5 rounded-full ${
                    event.kind === "error"
                      ? "bg-[color:var(--danger)]"
                      : event.kind === "grounding_check"
                        ? "bg-[color:var(--success)]"
                        : "bg-foreground-muted"
                  }`}
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
                  className="flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left transition-colors hover:bg-white/[0.03]"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-1.5">
                      <Badge tone={KIND_TONE[event.kind] ?? "muted"}>
                        {kindLabels[event.kind] ?? event.kind}
                      </Badge>
                      <span className="text-[12px] text-foreground truncate">{event.name}</span>
                    </div>
                    {(event.latency_ms != null || event.tokens_in != null || event.tokens_out != null) && (
                      <div className="mt-0.5 flex flex-wrap gap-2 text-[10px] text-foreground-dim">
                        {event.latency_ms != null && <span>{event.latency_ms.toFixed(0)} ms</span>}
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
                      transition={{ duration: 0.2, ease: [0.16, 1, 0.3, 1] }}
                      className="overflow-hidden whitespace-pre-wrap rounded-md bg-black/40 ml-1 mt-1 mb-2 p-2 text-[10px] leading-relaxed text-foreground-muted ring-1 ring-inset ring-white/[0.05]"
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
    </div>
  );
}
