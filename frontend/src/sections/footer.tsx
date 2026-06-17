"use client";

import Link from "next/link";
import Image from "next/image";
import { Mail } from "lucide-react";

import { useTranslation } from "@/lib/language";

function GithubMark({ className = "" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="currentColor"
      aria-hidden="true"
      className={className}
    >
      <path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" />
    </svg>
  );
}

type SocialLink = {
  label: string;
  href: string;
  external: boolean;
  tileClass: string;
} & (
  | {
      Icon: React.ComponentType<{ className?: string }>;
      image?: never;
    }
  | { image: string; Icon?: never }
);

const SOCIAL_LINKS: SocialLink[] = [
  {
    label: "GitHub",
    href: "https://github.com/Eukarota",
    Icon: GithubMark,
    tileClass:
      "bg-gradient-to-br from-zinc-700 via-zinc-800 to-black text-white",
    external: true,
  },
  {
    label: "Malt",
    href: "https://www.malt.fr/profile/mathiasdupey",
    image: "/icons/malt.png",
    tileClass: "bg-[#FC5656]",
    external: true,
  },
  {
    label: "contact@ceres.broker",
    href: "mailto:contact@ceres.broker",
    Icon: Mail,
    tileClass:
      "bg-gradient-to-br from-sky-400 via-blue-500 to-blue-700 text-white",
    external: false,
  },
];

export function Footer() {
  const { t } = useTranslation();
  return (
    <footer className="relative bg-background pt-24 pb-12 mt-32 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-14 mb-16">
        <div className="space-y-5">
          <p className="text-base font-semibold text-foreground tracking-tight">
            {t("footer.brand")}
          </p>
          <p className="text-sm text-foreground/55 leading-relaxed max-w-xs">
            {t("footer.tagline")}
          </p>
        </div>

        <div>
          <p className="text-xs font-medium uppercase text-foreground/45 mb-6 tracking-[0.12em]">
            {t("footer.contactLabel")}
          </p>
          <ul className="space-y-4">
            {SOCIAL_LINKS.map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  {...(link.external
                    ? { target: "_blank", rel: "noopener noreferrer" }
                    : {})}
                  className="group inline-flex items-center gap-4 text-sm text-foreground/70 hover:text-foreground transition-colors"
                >
                  <span
                    className={`relative inline-flex items-center justify-center w-11 h-11 rounded-[24%] shrink-0 overflow-hidden ${link.tileClass} shadow-[inset_0_1px_0_rgba(255,255,255,0.25),inset_0_-1px_0_rgba(0,0,0,0.15),0_6px_16px_-4px_rgba(0,0,0,0.4)] ring-1 ring-black/10 transition-transform duration-300 group-hover:scale-[1.06] group-hover:-translate-y-0.5`}
                  >
                    {link.image ? (
                      <Image
                        src={link.image}
                        alt={link.label}
                        width={44}
                        height={44}
                        className="w-full h-full object-cover"
                      />
                    ) : link.Icon ? (
                      <link.Icon className="w-5 h-5 drop-shadow-[0_1px_0_rgba(0,0,0,0.15)]" />
                    ) : null}
                  </span>
                  <span className="tracking-tight">{link.label}</span>
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <p className="text-xs font-medium uppercase text-foreground/45 mb-6 tracking-[0.12em]">
            {t("footer.legalLabel")}
          </p>
          <ul className="space-y-3">
            <li>
              <Link
                href="https://ceres.broker"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-foreground/65 hover:text-foreground transition-colors tracking-tight"
              >
                {t("footer.parentSite")}
              </Link>
            </li>
            <li>
              <Link
                href="https://eur-lex.europa.eu/eli/reg/2024/1689/oj"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-foreground/65 hover:text-foreground transition-colors tracking-tight"
              >
                {t("footer.regulation")}
              </Link>
            </li>
          </ul>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pt-8 border-t border-foreground/5">
        <p className="text-sm text-foreground/40 tracking-tight">
          © {new Date().getFullYear()} {t("footer.brand")}
        </p>
        <p className="text-xs text-foreground/35 tracking-tight inline-flex items-center gap-2">
          <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400/60 shadow-[0_0_8px_rgba(52,211,153,0.5)]" />
          {t("footer.hostedInEurope")}
        </p>
      </div>
    </footer>
  );
}
