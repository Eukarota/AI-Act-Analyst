"""
Article 50 transparency obligations.

These do not make a system high-risk. They impose disclosure / marking duties
on providers and deployers. We surface them as Tier.TRANSPARENCY so the
obligations layer can emit the right Art. 50 paragraphs.

Triggers (Art. 50):
  (1) AI systems intended to interact directly with natural persons.
  (2) Providers of AI systems generating synthetic audio/image/video/text
      content must mark outputs as artificially generated/manipulated.
  (3) Deployers of emotion-recognition or biometric-categorisation systems
      must inform exposed natural persons.
  (4) Deployers of deepfake-generating systems must disclose that the
      content has been artificially generated/manipulated.

The transparency tier does not stack: any single trigger is enough. If
multiple apply, the agent's downstream `lookup_obligations` step collects
all the relevant Art. 50 paragraphs based on the AttributeSet.
"""

from __future__ import annotations

from backend.agent.state import AttributeSet, Tier
from regulations.ai_act.rules._common import (
    RuleMatch,
    any_phrase,
    article_citation,
    text_search,
)

_DEEPFAKE_PHRASES = (
    "deepfake",
    "manipulated image",
    "manipulated video",
    "manipulated audio",
    "image manipulation",
    "video manipulation",
    "voice clone",
    "voice cloning",
)


def evaluate(attributes: AttributeSet) -> RuleMatch | None:
    triggers: list[tuple[str, str]] = []

    if attributes.interacts_with_humans:
        triggers.append(
            (
                "1",
                "AI system intended to interact directly with natural persons must "
                "inform them they are interacting with an AI.",
            )
        )

    if attributes.generates_synthetic_content:
        triggers.append(
            (
                "2",
                "Providers of AI systems generating synthetic audio, image, video or "
                "text content must mark outputs as artificially generated or "
                "manipulated in a machine-readable format.",
            )
        )

    if attributes.emotion_recognition or attributes.biometric:
        triggers.append(
            (
                "3",
                "Deployers of emotion-recognition or biometric-categorisation systems "
                "must inform natural persons exposed to their operation.",
            )
        )

    text = text_search(attributes)
    if any_phrase(text, _DEEPFAKE_PHRASES):
        triggers.append(
            (
                "4",
                "Deployers of AI systems generating or manipulating deepfake content "
                "must disclose that the content has been artificially generated.",
            )
        )

    if not triggers:
        return None

    paragraphs = ", ".join(p for p, _ in triggers)
    supporting = tuple(article_citation("50", paragraph=p) for p, _ in triggers)
    rationale = (
        "Transparency obligations under Art. 50 paragraph(s) "
        f"{paragraphs}. Reasons: " + " | ".join(reason for _, reason in triggers)
    )

    return RuleMatch(
        tier=Tier.TRANSPARENCY,
        fired_rule=f"art_50.transparency_paragraphs_{paragraphs.replace(', ', '_')}",
        supporting_refs=supporting,
        rationale=rationale,
    )
