"""
Assessment report exporters: Markdown + PDF.

Renders an AssessmentReport into a hand-out document a compliance officer can
file. Both formats render from the same canonical Markdown so what the
analyst sees on screen, what they download as Markdown, and what they download
as PDF stay aligned. The PDF path uses WeasyPrint and depends on system
libraries (Pango/Cairo); if those are missing the caller gets a typed 503
with the install hint, while the Markdown path stays available.

Notes:
- Output language follows `report.system_profile.language` (FR/EN).
- The manifest is always shown verbatim so the document is reproducible.
- Every legal claim already carries its citation by construction (grounding
  contract). The exporter only formats; it never invents.
- Em dashes are forbidden per the project's CLAUDE.md and are not used here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from backend.agent.report import AssessmentReport
from backend.agent.state import (
    Citation,
    DraftedDocument,
    GapFinding,
    Obligation,
)

_FR = "FR"
_EN = "EN"

_HEADLINES: dict[str, dict[str, str]] = {
    _FR: {
        "prohibited": "Système non conforme : pratique interdite par l'Art. 5",
        "non_compliant": "Système non conforme : {n} obligation(s) manquante(s)",
        "partial": "Système partiellement conforme : {n} point(s) à clarifier",
        "compliant": "Système conforme aux obligations identifiées",
        "no_declared_controls": "Conformité non démontrée : aucun contrôle déclaré",
        "minimal": "Aucune obligation impérative : risque minimal",
        "undetermined": "Classification indéterminée",
    },
    _EN: {
        "prohibited": "Non-compliant: prohibited practice under Art. 5",
        "non_compliant": "Non-compliant: {n} obligation(s) missing",
        "partial": "Partially compliant: {n} point(s) to clarify",
        "compliant": "Compliant with the identified obligations",
        "no_declared_controls": "Compliance not demonstrated: no controls declared",
        "minimal": "No binding obligations: minimal risk",
        "undetermined": "Classification undetermined",
    },
}

_LABELS: dict[str, dict[str, str]] = {
    _FR: {
        "eyebrow": "Pré-évaluation AI Act",
        "system": "Système évalué",
        "manifest": "Manifeste d'exécution",
        "manifest_run": "Identifiant",
        "manifest_model": "Modèle",
        "manifest_embedding": "Embeddings",
        "manifest_corpus": "Corpus",
        "manifest_prompts": "Prompts",
        "manifest_rules": "Règles",
        "manifest_timestamp": "Horodatage",
        "classification": "Classification",
        "classification_tier": "Niveau de risque",
        "classification_rule": "Règle déclenchée",
        "classification_rationale": "Raisonnement",
        "classification_refs": "Citations à l'appui",
        "obligations": "Obligations applicables",
        "obligations_empty": "Aucune obligation impérative.",
        "gaps": "Analyse d'écart",
        "gaps_empty": "Aucun écart matériel détecté à partir des contrôles déclarés.",
        "gap_status_met": "Couvert",
        "gap_status_partial": "Partiel",
        "gap_status_missing": "Manquant",
        "gap_status_unclear": "À préciser",
        "documents": "Documentation à produire",
        "documents_empty": "Aucun document à produire pour ce niveau de risque.",
        "passages": "Extraits du Règlement consultés",
        "passages_empty": "Aucun passage retenu (tier sans obligations matérielles).",
        "notice": "Avertissement",
        "controls_label": "Contrôles déclarés",
        "actor_label": "Rôle déclaré",
        "language_label": "Langue",
    },
    _EN: {
        "eyebrow": "AI Act pre-assessment",
        "system": "System under assessment",
        "manifest": "Run manifest",
        "manifest_run": "Run ID",
        "manifest_model": "Model",
        "manifest_embedding": "Embeddings",
        "manifest_corpus": "Corpus",
        "manifest_prompts": "Prompts",
        "manifest_rules": "Rules",
        "manifest_timestamp": "Timestamp",
        "classification": "Classification",
        "classification_tier": "Risk tier",
        "classification_rule": "Fired rule",
        "classification_rationale": "Rationale",
        "classification_refs": "Supporting citations",
        "obligations": "Applicable obligations",
        "obligations_empty": "No binding obligations.",
        "gaps": "Gap analysis",
        "gaps_empty": "No material gap detected against declared controls.",
        "gap_status_met": "Covered",
        "gap_status_partial": "Partial",
        "gap_status_missing": "Missing",
        "gap_status_unclear": "Unclear",
        "documents": "Documentation to produce",
        "documents_empty": "No documentation to produce at this tier.",
        "passages": "Excerpts of the Regulation consulted",
        "passages_empty": "No passage retained (tier without material obligations).",
        "notice": "Disclaimer",
        "controls_label": "Declared controls",
        "actor_label": "Declared role",
        "language_label": "Language",
    },
}


class PdfRenderingUnavailable(RuntimeError):
    """Raised when the optional PDF rendering stack is not importable."""


@dataclass(frozen=True)
class RenderedDocument:
    body: bytes
    media_type: str
    filename: str


def _lang(report: AssessmentReport) -> str:
    raw = (report.system_profile.language or _EN).upper()
    return _FR if raw == _FR else _EN


def _derive_headline_key(report: AssessmentReport) -> tuple[str, int]:
    """Mirror the frontend `deriveHeadline` so screen and document agree.

    Returns (key, count).
    """
    tier = report.classification.tier.value if report.classification else None
    if tier == "prohibited":
        return "prohibited", 0
    if tier == "minimal":
        return "minimal", 0
    if tier in (None, "undetermined"):
        return "undetermined", 0

    obligations = report.obligations or []
    declared_count = len(report.system_profile.declared_controls or [])
    if obligations and declared_count == 0:
        return "no_declared_controls", 0

    gaps = report.gaps or []
    missing = sum(1 for g in gaps if g.status == "missing")
    partial = sum(1 for g in gaps if g.status == "partial")
    unclear = sum(1 for g in gaps if g.status == "unclear")
    if missing:
        return "non_compliant", missing
    if partial or unclear:
        return "partial", partial + unclear
    return "compliant", len(gaps)


def _short_citation(c: Citation) -> str:
    if c.article:
        s = f"Art. {c.article}"
        if c.paragraph:
            s += f"({c.paragraph})"
        return s
    if c.annex_ref:
        s = f"Annex {c.annex_ref}"
        if c.paragraph:
            s += f"({c.paragraph})"
        return s
    if c.recital_ref:
        return f"Recital {c.recital_ref}"
    return c.celex_id


def _format_timestamp(value: datetime, lang: str) -> str:
    if lang == _FR:
        return value.strftime("%d/%m/%Y %H:%M UTC")
    return value.strftime("%Y-%m-%d %H:%M UTC")


def _format_obligation(o: Obligation) -> str:
    return f"- **{o.article_ref}** · {o.summary} ({_short_citation(o.citation)})"


def _format_gap(g: GapFinding, labels: dict[str, str]) -> str:
    status_label = labels.get(f"gap_status_{g.status}", g.status)
    body = f"- **{g.obligation_id}** · {status_label}"
    if g.notes:
        body += f"\n  - {g.notes}"
    if g.declared_evidence:
        body += f"\n  - ↳ {g.declared_evidence}"
    return body


def _format_drafted(doc: DraftedDocument) -> str:
    refs = ", ".join(_short_citation(c) for c in doc.citations[:4])
    head = f"### {doc.title}"
    if refs:
        head += f"\n\n_({refs})_"
    return f"{head}\n\n```\n{doc.body.strip()}\n```"


def render_markdown(report: AssessmentReport) -> str:
    lang = _lang(report)
    labels = _LABELS[lang]
    headline_key, count = _derive_headline_key(report)
    headline = _HEADLINES[lang][headline_key].replace("{n}", str(count))

    lines: list[str] = []
    lines.append(f"# {headline}")
    lines.append("")
    lines.append(f"_{labels['eyebrow']}_")
    lines.append("")
    if report.classification:
        lines.append(
            f"**{labels['classification_tier']}** : "
            f"`{report.classification.tier.value}`  "
            f"\n**{labels['classification_rule']}** : "
            f"`{report.classification.fired_rule}`"
        )
        lines.append("")
        if report.classification.rationale:
            lines.append(
                f"**{labels['classification_rationale']}** : "
                f"{report.classification.rationale}"
            )
            lines.append("")
        refs = report.classification.supporting_refs
        if refs:
            ref_str = ", ".join(_short_citation(r) for r in refs)
            lines.append(f"**{labels['classification_refs']}** : {ref_str}")
            lines.append("")

    # System block
    lines.append(f"## {labels['system']}")
    lines.append("")
    lines.append(f"> {report.system_profile.description}")
    lines.append("")
    if report.system_profile.declared_actor_role:
        lines.append(
            f"- **{labels['actor_label']}** : "
            f"`{report.system_profile.declared_actor_role}`"
        )
    controls = report.system_profile.declared_controls or []
    if controls:
        lines.append(f"- **{labels['controls_label']}** :")
        for c in controls:
            lines.append(f"  - {c}")
    lines.append(f"- **{labels['language_label']}** : `{lang}`")
    lines.append("")

    # Obligations
    lines.append(f"## {labels['obligations']}")
    lines.append("")
    if report.obligations:
        for o in report.obligations:
            lines.append(_format_obligation(o))
    else:
        lines.append(labels["obligations_empty"])
    lines.append("")

    # Gaps
    lines.append(f"## {labels['gaps']}")
    lines.append("")
    if report.gaps:
        for g in report.gaps:
            lines.append(_format_gap(g, labels))
    else:
        lines.append(labels["gaps_empty"])
    lines.append("")

    # Documents
    lines.append(f"## {labels['documents']}")
    lines.append("")
    if report.drafted_documents:
        for d in report.drafted_documents:
            lines.append(_format_drafted(d))
            lines.append("")
    else:
        lines.append(labels["documents_empty"])
        lines.append("")

    # Passages
    lines.append(f"## {labels['passages']}")
    lines.append("")
    if report.retrieved_passages:
        for p in report.retrieved_passages:
            ref = _short_citation(p.citation)
            text = p.text.strip().replace("\n", " ")
            lines.append(f"- **{ref}** : {text}")
    else:
        lines.append(labels["passages_empty"])
    lines.append("")

    # Manifest (sourced reproducibility block)
    lines.append(f"## {labels['manifest']}")
    lines.append("")
    m = report.manifest
    rows = [
        (labels["manifest_run"], m.run_id),
        (labels["manifest_model"], m.model_id),
        (labels["manifest_embedding"], m.embedding_model),
        (labels["manifest_corpus"], m.corpus_version),
        (labels["manifest_prompts"], m.prompt_set_version),
        (labels["manifest_rules"], m.rules_version),
        (labels["manifest_timestamp"], _format_timestamp(m.timestamp, lang)),
    ]
    for key, value in rows:
        lines.append(f"- **{key}** : `{value}`")
    lines.append("")

    lines.append(f"## {labels['notice']}")
    lines.append("")
    lines.append(report.pre_assessment_notice)
    lines.append("")
    return "\n".join(lines)


_PDF_CSS = """
@page {
  size: A4;
  margin: 22mm 18mm 22mm 18mm;
  @bottom-right {
    content: counter(page) " / " counter(pages);
    font-family: "Inter Tight", "Helvetica Neue", Arial, sans-serif;
    font-size: 9pt;
    color: #71717a;
  }
}
body {
  font-family: "Inter Tight", "Helvetica Neue", Arial, sans-serif;
  font-size: 10.5pt;
  line-height: 1.55;
  color: #18181b;
}
h1 {
  font-size: 22pt;
  font-weight: 700;
  letter-spacing: -0.01em;
  line-height: 1.15;
  margin: 0 0 6pt 0;
  color: #0f172a;
}
h2 {
  font-size: 13pt;
  font-weight: 600;
  margin-top: 18pt;
  margin-bottom: 6pt;
  padding-bottom: 2pt;
  border-bottom: 1px solid #e4e4e7;
  color: #0f172a;
}
h3 { font-size: 11pt; font-weight: 600; margin-top: 12pt; }
em { color: #52525b; }
strong { color: #0f172a; }
blockquote {
  margin: 6pt 0;
  padding: 6pt 10pt;
  background: #f4f4f5;
  border-left: 3px solid #a78bfa;
  font-style: italic;
  color: #3f3f46;
}
code {
  font-family: "JetBrains Mono", "SF Mono", Menlo, monospace;
  font-size: 9.5pt;
  background: #f4f4f5;
  padding: 1pt 3pt;
  border-radius: 2pt;
}
pre {
  background: #f4f4f5;
  padding: 8pt 10pt;
  border-left: 3px solid #06b6d4;
  font-size: 9pt;
  line-height: 1.45;
  white-space: pre-wrap;
  word-wrap: break-word;
}
ul { margin: 4pt 0; padding-left: 18pt; }
li { margin-bottom: 3pt; }
"""


def _ensure_weasyprint():  # type: ignore[no-untyped-def]
    try:
        import weasyprint  # type: ignore[import-not-found]
    except OSError as exc:
        raise PdfRenderingUnavailable(
            "PDF rendering requires Pango/Cairo system libraries. "
            "Install them with `brew install pango cairo gdk-pixbuf libffi` "
            "on macOS, or `apt-get install libpango-1.0-0 libpangoft2-1.0-0 "
            "libffi-dev` on Debian, then restart the API."
        ) from exc
    except ImportError as exc:
        raise PdfRenderingUnavailable(
            "PDF rendering requires the `report` extras. "
            "Install with `uv sync --all-extras`."
        ) from exc
    return weasyprint


def render_pdf(report: AssessmentReport) -> bytes:
    """Render the assessment as a PDF.

    Raises PdfRenderingUnavailable when the optional stack is not installed
    or system libraries are missing. Callers should map that to HTTP 503.
    """
    weasyprint = _ensure_weasyprint()
    import markdown as md  # local import: keeps module importable when extras absent

    md_text = render_markdown(report)
    html_body = md.markdown(
        md_text,
        extensions=["extra", "sane_lists"],
        output_format="html5",
    )
    html_doc = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        f"<style>{_PDF_CSS}</style></head><body>{html_body}</body></html>"
    )
    return weasyprint.HTML(string=html_doc).write_pdf()


def render_markdown_document(report: AssessmentReport) -> RenderedDocument:
    body = render_markdown(report).encode("utf-8")
    return RenderedDocument(
        body=body,
        media_type="text/markdown; charset=utf-8",
        filename=f"ai-act-analyst-{report.run_id}.md",
    )


def render_pdf_document(report: AssessmentReport) -> RenderedDocument:
    body = render_pdf(report)
    return RenderedDocument(
        body=body,
        media_type="application/pdf",
        filename=f"ai-act-analyst-{report.run_id}.pdf",
    )
