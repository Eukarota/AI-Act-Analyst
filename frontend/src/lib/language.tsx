"use client";

import {
  createContext,
  useContext,
  useState,
  useEffect,
  ReactNode,
} from "react";
import content from "@/content.json";

type Language = "fr" | "en";
type LanguageContextType = {
  language: Language;
  setLanguage: (lang: Language) => void;
};

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function LanguageProvider({
  children,
  initialLanguage = "fr",
}: {
  children: ReactNode;
  initialLanguage?: Language;
}) {
  const [language, setLanguage] = useState<Language>(initialLanguage);

  useEffect(() => {
    try {
      const saved = localStorage.getItem("language") as Language | null;
      if (saved === "fr" || saved === "en") {
        setLanguage(saved);
        return;
      }
      localStorage.setItem("language", "fr");
    } catch {
      // no-op (SSR or storage disabled)
    }
  }, []);

  const handleSetLanguage = (lang: Language) => {
    setLanguage(lang);
    try {
      localStorage.setItem("language", lang);
    } catch {
      // no-op
    }
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage: handleSetLanguage }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error("useLanguage must be used within a LanguageProvider");
  return ctx;
}

export function useTranslation() {
  const { language } = useLanguage();

  const resolve = (lang: Language, key: string): unknown => {
    const keys = key.split(".");
    let value: unknown = content[lang];
    for (const k of keys) {
      if (!value || typeof value !== "object") return undefined;
      value = (value as Record<string, unknown>)[k];
    }
    return value;
  };

  return {
    language,
    t: (key: string, fallback?: string): string => {
      if (!key) return fallback ?? "";
      const v = resolve(language, key);
      if (typeof v === "string") return v;
      if (language !== "fr") {
        const fr = resolve("fr", key);
        if (typeof fr === "string") return fr;
      }
      return fallback ?? key;
    },
    raw: <T = unknown,>(key: string): T | undefined => {
      const v = resolve(language, key);
      if (v !== undefined) return v as T;
      if (language !== "fr") {
        const fr = resolve("fr", key);
        if (fr !== undefined) return fr as T;
      }
      return undefined;
    },
  };
}
