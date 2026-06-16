"use client";

import { useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

import { useTranslation } from "@/lib/language";
import { postAssess, ApiError, type AssessPayload } from "@/lib/api";
import type { ActorRole, AssessmentReport } from "@/lib/types";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Select } from "@/components/ui/select";
import { Label } from "@/components/ui/label";

type Sample = {
  system_description: string;
  actor_role: string;
  declared_controls: string;
};

const ACTOR_ROLES: (ActorRole | "")[] = [
  "",
  "provider",
  "deployer",
  "distributor",
  "importer",
  "product_manufacturer",
  "authorised_representative",
];

const SAMPLE_KEYS = ["recruitment", "translator", "chatbot", "social_scoring"] as const;

interface Props {
  onResult: (report: AssessmentReport, payload: AssessPayload) => void;
}

export function Intake({ onResult }: Props) {
  const { t, raw, language } = useTranslation();
  const [systemDescription, setSystemDescription] = useState("");
  const [actorRole, setActorRole] = useState<string>("");
  const [declaredControls, setDeclaredControls] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const loadSample = (key: (typeof SAMPLE_KEYS)[number]) => {
    const sample = raw<Sample>(`samples.${key}`);
    if (!sample) return;
    setSystemDescription(sample.system_description);
    setActorRole(sample.actor_role);
    setDeclaredControls(sample.declared_controls);
    if (sample.actor_role || sample.declared_controls) setShowAdvanced(true);
    setError(null);
    textareaRef.current?.focus();
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (systemDescription.trim().length < 10) {
      setError(t("errors.validation"));
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const controls = declaredControls
        .split("\n")
        .map((c) => c.trim())
        .filter(Boolean);
      const payload: AssessPayload = {
        system_description: systemDescription,
        declared_controls: controls,
        declared_actor_role: (actorRole || null) as ActorRole | null,
        language: language.toUpperCase() as "EN" | "FR",
      };
      const response = await postAssess(payload);
      onResult(response.report, payload);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(`${err.status} · ${err.message}`);
      } else if (err instanceof TypeError) {
        setError(t("errors.network"));
      } else {
        setError(t("errors.unknown"));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const actorOptions = raw<Record<string, string>>("intake.labels.actor_role_options") ?? {};

  return (
    <form onSubmit={submit} className="space-y-6">
      <div className="text-center space-y-3">
        <h1 className="text-3xl sm:text-4xl font-semibold tracking-tight">{t("intake.heading")}</h1>
        <p className="text-foreground-muted max-w-xl mx-auto leading-relaxed text-[15px]">
          {t("intake.description")}
        </p>
      </div>

      <div className="flex flex-wrap items-center justify-center gap-2">
        <span className="text-[12px] text-foreground-dim">{t("intake.samples.label")}</span>
        {SAMPLE_KEYS.map((k) => (
          <button
            key={k}
            type="button"
            onClick={() => loadSample(k)}
            disabled={submitting}
            className="rounded-full bg-white/[0.04] px-3 py-1 text-[12px] text-foreground-muted ring-1 ring-inset ring-white/[0.06] hover:bg-white/[0.08] hover:text-foreground disabled:opacity-50 transition-colors"
          >
            {t(`intake.samples.${k}`)}
          </button>
        ))}
      </div>

      <div className="relative rounded-3xl bg-card/60 ring-1 ring-inset ring-white/[0.08] backdrop-blur-xl shadow-2xl shadow-black/20">
        <Textarea
          ref={textareaRef}
          rows={5}
          placeholder={t("intake.placeholder")}
          value={systemDescription}
          onChange={(e) => setSystemDescription(e.target.value)}
          disabled={submitting}
          className="w-full resize-none bg-transparent border-0 ring-0 focus:ring-0 focus:outline-none px-5 pt-5 pb-16 text-[15px] leading-relaxed placeholder:text-foreground-dim"
        />
        <div className="absolute bottom-3 left-3 right-3 flex items-center justify-between gap-3">
          <button
            type="button"
            onClick={() => setShowAdvanced((v) => !v)}
            disabled={submitting}
            className="rounded-full px-3 py-1.5 text-[12px] text-foreground-dim hover:text-foreground hover:bg-white/[0.04] transition-colors"
          >
            {showAdvanced ? t("intake.advanced_close") : t("intake.advanced_open")}
          </button>
          <Button type="submit" disabled={submitting || systemDescription.trim().length < 10}>
            {submitting ? t("intake.send_running") : t("intake.send")}
          </Button>
        </div>
      </div>

      <AnimatePresence>
        {showAdvanced && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="space-y-5 rounded-2xl bg-card/40 ring-1 ring-inset ring-white/[0.06] p-5">
              <div className="space-y-2">
                <Label htmlFor="actor_role">{t("intake.labels.actor_role")}</Label>
                <Select
                  id="actor_role"
                  value={actorRole}
                  onChange={(e) => setActorRole(e.target.value)}
                  disabled={submitting}
                >
                  {ACTOR_ROLES.map((role) => (
                    <option key={role || "unspecified"} value={role}>
                      {actorOptions[role || "unspecified"]}
                    </option>
                  ))}
                </Select>
                <p className="text-[12px] text-foreground-dim">{t("intake.labels.actor_role_help")}</p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="declared_controls">{t("intake.labels.declared_controls")}</Label>
                <Textarea
                  id="declared_controls"
                  rows={4}
                  placeholder={t("intake.labels.declared_controls_placeholder")}
                  value={declaredControls}
                  onChange={(e) => setDeclaredControls(e.target.value)}
                  disabled={submitting}
                />
                <p className="text-[12px] text-foreground-dim">{t("intake.labels.declared_controls_help")}</p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            className="rounded-xl bg-[color:var(--danger)]/10 ring-1 ring-inset ring-[color:var(--danger)]/30 text-[color:var(--danger)] text-[13px] px-4 py-3"
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>

      <p className="text-[11px] text-foreground-dim text-center max-w-xl mx-auto leading-relaxed">
        {t("intake.notice")}
      </p>
    </form>
  );
}
