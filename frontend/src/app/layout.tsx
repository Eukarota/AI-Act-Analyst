import type { Metadata } from "next";
import { headers } from "next/headers";
import { Inter_Tight } from "next/font/google";

import "./globals.css";
import { LanguageProvider } from "@/lib/language";
import content from "@/content.json";

const interTight = Inter_Tight({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

export async function generateMetadata(): Promise<Metadata> {
  const headersList = await headers();
  const acceptLanguage = headersList.get("accept-language") ?? "";
  const lang = acceptLanguage.startsWith("en") ? "en" : "fr";
  const m = content[lang as keyof typeof content].metadata;
  return {
    title: m.title,
    description: m.description,
  };
}

export default async function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const headersList = await headers();
  const acceptLanguage = headersList.get("accept-language") ?? "";
  const lang = acceptLanguage.startsWith("en") ? "en" : "fr";

  return (
    <html lang={lang} className="scroll-smooth">
      <body className={`${interTight.variable} antialiased`}>
        <LanguageProvider initialLanguage={lang as "fr" | "en"}>
          {children}
        </LanguageProvider>
      </body>
    </html>
  );
}
