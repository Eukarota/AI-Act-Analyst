"use client";

import { useLanguage, useTranslation } from "@/lib/language";
import { cn } from "@/lib/utils";

export function LanguageSwitcher({ className }: { className?: string }) {
  const { language, setLanguage } = useLanguage();
  const { t } = useTranslation();

  return (
    <div
      className={cn(
        "inline-flex rounded-full bg-white/[0.04] p-0.5 ring-1 ring-inset ring-white/[0.06] text-[12px]",
        className,
      )}
    >
      {(["fr", "en"] as const).map((lang) => (
        <button
          key={lang}
          type="button"
          onClick={() => setLanguage(lang)}
          aria-pressed={language === lang}
          className={cn(
            "rounded-full px-3 py-1 transition-colors",
            language === lang
              ? "bg-white text-black"
              : "text-foreground-muted hover:text-foreground",
          )}
        >
          {t(`nav.lang.${lang}`)}
        </button>
      ))}
    </div>
  );
}
