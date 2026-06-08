"use client";

import { useTranslation } from "@/lib/language";
import { LanguageSwitcher } from "@/components/language-switcher";

export function Nav() {
  const { t } = useTranslation();
  return (
    <header className="sticky top-0 z-30 border-b border-white/[0.06] glass">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="grid h-8 w-8 place-items-center rounded-lg bg-white text-black font-semibold tracking-tight">
            B
          </div>
          <div className="flex flex-col leading-none">
            <span className="text-sm font-semibold tracking-tight">
              {t("nav.brand")}
            </span>
            <span className="text-[11px] text-foreground-dim mt-0.5">
              {t("nav.tagline")}
            </span>
          </div>
        </div>
        <LanguageSwitcher />
      </div>
    </header>
  );
}
