"use client";

import Link from "next/link";
import { Compass } from "lucide-react";
import { motion } from "framer-motion";

import { useTranslation } from "@/lib/language";
import { LanguageSwitcher } from "@/components/language-switcher";

export function Nav() {
  const { t } = useTranslation();
  return (
    <header className="fixed top-0 left-0 right-0 z-40 px-4 sm:px-6 py-3 pointer-events-none">
      <div className="mx-auto max-w-[1400px] flex items-center justify-between pointer-events-auto">
        <motion.div
          initial={{ y: -8, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6, ease: [0.23, 1, 0.32, 1] }}
        >
          <Link
            href="/"
            className="group inline-flex items-center gap-3 rounded-2xl bg-black/40 backdrop-blur-xl ring-1 ring-inset ring-white/[0.08] px-4 py-2 shadow-2xl shadow-black/50 transition-colors hover:ring-white/[0.16]"
          >
            <Compass className="h-5 w-5 text-foreground transition-transform duration-500 group-hover:rotate-45" />
            <div className="flex flex-col leading-none">
              <span className="text-[15px] font-semibold tracking-tight text-foreground">
                {t("nav.brand")}
              </span>
              <span className="mt-0.5 text-[11px] tracking-tight text-foreground-dim">
                {t("nav.tagline")}
              </span>
            </div>
          </Link>
        </motion.div>
        <motion.div
          initial={{ y: -8, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.6, delay: 0.05, ease: [0.23, 1, 0.32, 1] }}
          className="rounded-2xl bg-black/40 backdrop-blur-xl ring-1 ring-inset ring-white/[0.08] shadow-2xl shadow-black/50"
        >
          <LanguageSwitcher />
        </motion.div>
      </div>
    </header>
  );
}
