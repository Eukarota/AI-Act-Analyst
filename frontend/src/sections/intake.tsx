"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

import { useTranslation } from "@/lib/language";
import { postAssess, ApiError } from "@/lib/api";
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
  onResult: (report: AssessmentReport) => void;
  hasResult: boolean;
  onReset: () => void;
}

export function Intake({ onResult, hasResult, onReset }: Props) {
  const { t, raw } = useTranslation();
  const [systemDescription, setSystemDescription] = useState("");
  const [actorRole, setActorRole] = useState<string>("");
  const [declaredControls, setDeclaredControls] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSample = (key: (typeof SAMPLE_KEYS)[number]) => {
    const sample = raw<Sample>(`samples.${key}`);
    if (!sample) return;
    setSystemDescription(sample.system_description);
    setActorRole(sample.actor_role);
    setDeclaredControls(sample.declared_controls);
    setError(null);
  };

  const reset = () => {
    setSystemDescription("");
    setActorRole("");
    setDeclaredControls("");
    setError(null);
    onReset();
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
      const response = await postAssess({
        system_description: systemDescription,
        declared_controls: controls,
        declared_actor_role: (actorRole || null) as ActorRole | null,
      });
      onResult(response.report);
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
    <section id="intake" className="relative border-b border-white/[0.06]">
      <div className="mx-auto max-w-6xl px-6 py-16">
        <div className="grid gap-12 lg:grid-cols-[1.05fr_1fr]">
          <div>
            <h2 className="text-3xl font-semibold tracking-tight">{t("intake.heading")}</h2>
            <p className="mt-3 text-foreground-muted max-w-xl leading-relaxed">
              {t("intake.description")}
            </p>
            <div className="mt-8 flex flex-wrap items-center gap-2">
              <span className="text-[12px] text-foreground-dim">
                {t("intake.samples.label")}
              </span>
              {SAMPLE_KEYS.map((k) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => loadSample(k)}
                  className="rounded-full bg-white/[0.04] px-3 py-1 text-[12px] text-foreground-muted ring-1 ring-inset ring-white/[0.06] hover:bg-white/[0.08] hover:text-foreground transition-colors"
                >
                  {t(`intake.samples.${k}`)}
                </button>
              ))}
            </div>
          </div>

          <form
            onSubmit={submit}
            className="rounded-2xl bg-card/60 ring-1 ring-inset ring-white/[0.06] p-6 backdrop-blur-xl"
          >
            <div className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="system_description">
                  {t("intake.labels.system_description")}
                </Label>
                <Textarea
                  id="system_description"
                  rows={6}
                  placeholder={t("intake.labels.system_description_placeholder")}
                  value={systemDescription}
                  onChange={(e) => setSystemDescription(e.target.value)}
                  disabled={submitting || hasResult}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="actor_role">{t("intake.labels.actor_role")}</Label>
                <Select
                  id="actor_role"
                  value={actorRole}
                  onChange={(e) => setActorRole(e.target.value)}
                  disabled={submitting || hasResult}
                >
                  {ACTOR_ROLES.map((role) => (
                    <option key={role || "unspecified"} value={role}>
                      {actorOptions[role || "unspecified"]}
                    </option>
                  ))}
                </Select>
                <p className="text-[12px] text-foreground-dim">
                  {t("intake.labels.actor_role_help")}
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="declared_controls">
                  {t("intake.labels.declared_controls")}
                </Label>
                <Textarea
                  id="declared_controls"
                  rows={4}
                  placeholder={t("intake.labels.declared_controls_placeholder")}
                  value={declaredControls}
                  onChange={(e) => setDeclaredControls(e.target.value)}
                  disabled={submitting || hasResult}
                />
                <p className="text-[12px] text-foreground-dim">
                  {t("intake.labels.declared_controls_help")}
                </p>
              </div>

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

              <div className="flex items-center justify-end gap-3 pt-2">
                {hasResult ? (
                  <Button type="button" variant="ghost" onClick={reset}>
                    {t("intake.reset")}
                  </Button>
                ) : null}
                <Button type="submit" disabled={submitting || hasResult}>
                  {submitting ? t("intake.submit_running") : t("intake.submit")}
                </Button>
              </div>
            </div>
          </form>
        </div>
      </div>
    </section>
  );
}
