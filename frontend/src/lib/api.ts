/**
 * Thin client over the Phase 7 FastAPI surface. Dev uses next.config.ts
 * rewrites so the browser hits same-origin /api/* and Next proxies to
 * BOUSSOLE_API_ORIGIN (default http://localhost:8000).
 */

import type { ActorRole, AssessResponse } from "@/lib/types";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public body: unknown,
  ) {
    super(message);
  }
}

export interface AssessPayload {
  system_description: string;
  declared_controls: string[];
  declared_actor_role: ActorRole | null;
  language: "EN" | "FR";
}

export async function postAssess(payload: AssessPayload): Promise<AssessResponse> {
  const res = await fetch("/api/assess", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  const contentType = res.headers.get("content-type") ?? "";
  const body = contentType.includes("application/json") ? await res.json() : await res.text();

  if (!res.ok) {
    if (typeof body === "object" && body !== null && "report" in body) {
      return body as AssessResponse;
    }
    throw new ApiError(`POST /assess failed (${res.status})`, res.status, body);
  }
  return body as AssessResponse;
}

export interface ExtractedFile {
  text: string;
  truncated: boolean;
  char_count: number;
  page_count: number | null;
  source_filename: string;
  source_media_type: string;
}

export async function postExtract(file: File): Promise<ExtractedFile> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/extract", { method: "POST", body: form });
  const body = res.headers.get("content-type")?.includes("application/json")
    ? await res.json()
    : await res.text();
  if (!res.ok) {
    const message =
      typeof body === "object" && body && "detail" in body
        ? (body as { detail: { message?: string } }).detail.message ?? "Upload failed"
        : `POST /extract failed (${res.status})`;
    throw new ApiError(message, res.status, body);
  }
  return body as ExtractedFile;
}

export function assessExportUrl(runId: string, format: "md" | "pdf"): string {
  return `/api/assess/${encodeURIComponent(runId)}/export.${format}`;
}

export function citationToShort(c: {
  article: string | null;
  paragraph: string | null;
  annex_ref: string | null;
  recital_ref: string | null;
  celex_id: string;
}): string {
  const parts: string[] = [];
  if (c.article) {
    let s = `Art. ${c.article}`;
    if (c.paragraph) s += `(${c.paragraph})`;
    parts.push(s);
  }
  if (c.annex_ref) parts.push(`Annexe ${c.annex_ref}`);
  if (c.recital_ref) parts.push(`Cons. ${c.recital_ref}`);
  return parts.length ? parts.join(" · ") : c.celex_id;
}

export function eurLexUrl(): string {
  return "https://eur-lex.europa.eu/eli/reg/2024/1689/oj";
}
