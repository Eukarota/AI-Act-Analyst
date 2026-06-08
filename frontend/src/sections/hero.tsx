"use client";

import { useTranslation } from "@/lib/language";
import { AnimateInView } from "@/components/animate-in-view";

export function Hero() {
  const { t, raw } = useTranslation();
  const bullets = raw<string[]>("hero.bullets") ?? [];

  return (
    <section className="relative overflow-hidden border-b border-white/[0.06]">
      <div className="absolute inset-0 grid-bg opacity-90" aria-hidden />
      <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-white/15 to-transparent" aria-hidden />
      <div className="relative mx-auto max-w-6xl px-6 pt-28 pb-24">
        <AnimateInView>
          <span className="inline-flex items-center gap-2 rounded-full bg-white/[0.04] px-3 py-1 text-[12px] text-foreground-muted ring-1 ring-inset ring-white/[0.06]">
            <span className="h-1.5 w-1.5 rounded-full bg-[color:var(--accent)]" />
            {t("hero.eyebrow")}
          </span>
        </AnimateInView>
        <AnimateInView delay={0.05}>
          <h1 className="mt-6 max-w-3xl text-4xl sm:text-5xl md:text-6xl font-semibold tracking-[-0.02em] leading-[1.05]">
            {t("hero.headline")}
          </h1>
        </AnimateInView>
        <AnimateInView delay={0.1}>
          <p className="mt-6 max-w-2xl text-lg text-foreground-muted leading-relaxed">
            {t("hero.subhead")}
          </p>
        </AnimateInView>
        <AnimateInView delay={0.15}>
          <ul className="mt-10 grid gap-3 sm:grid-cols-3 max-w-4xl">
            {bullets.map((bullet, i) => (
              <li
                key={i}
                className="rounded-2xl bg-white/[0.025] ring-1 ring-inset ring-white/[0.06] p-4 text-sm text-foreground-muted"
              >
                <span className="block text-[11px] text-foreground-dim mb-2">
                  · 0{i + 1}
                </span>
                {bullet}
              </li>
            ))}
          </ul>
        </AnimateInView>
        <AnimateInView delay={0.25}>
          <p className="mt-10 max-w-2xl text-[12px] text-foreground-dim">
            {t("hero.notice")}
          </p>
        </AnimateInView>
      </div>
    </section>
  );
}
