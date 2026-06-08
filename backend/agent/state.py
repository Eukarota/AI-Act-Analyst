"""
Core Pydantic models that anchor the agent.

Single source of truth: every later phase imports these.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Tier(StrEnum):
    """Risk tiers per Regulation (EU) 2024/1689."""

    PROHIBITED = "prohibited"
    HIGH_RISK_ANNEX_I = "high_risk_annex_i"
    HIGH_RISK_ANNEX_III = "high_risk_annex_iii"
    TRANSPARENCY = "transparency"
    MINIMAL = "minimal"
    GPAI = "gpai"
    GPAI_SYSTEMIC = "gpai_systemic"
    UNDETERMINED = "undetermined"


class ActorRole(StrEnum):
    """Roles bearing obligations under the AI Act."""

    PROVIDER = "provider"
    DEPLOYER = "deployer"
    DISTRIBUTOR = "distributor"
    IMPORTER = "importer"
    PRODUCT_MANUFACTURER = "product_manufacturer"
    AUTHORISED_REPRESENTATIVE = "authorised_representative"


class Frozen(BaseModel):
    """Base class for value objects: immutable, extra forbidden."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class Citation(Frozen):
    """
    Citation metadata attached to every retrieved passage.

    A claim that does not carry a Citation cannot be grounded; see
    backend.rag.grounding for the enforced contract.
    """

    celex_id: str
    article: str | None = None
    paragraph: str | None = None
    annex_ref: str | None = None
    recital_ref: str | None = None
    lang: str = "en"
    url: str | None = None
    corpus_version: str

    def short(self) -> str:
        parts: list[str] = []
        if self.article:
            parts.append(f"Art. {self.article}")
            if self.paragraph:
                parts[-1] += f"({self.paragraph})"
        if self.annex_ref:
            parts.append(f"Annex {self.annex_ref}")
        if self.recital_ref:
            parts.append(f"Recital {self.recital_ref}")
        return ", ".join(parts) if parts else self.celex_id


class RetrievedPassage(Frozen):
    """A passage returned by the retrieval layer, always cited."""

    text: str
    citation: Citation
    score: float = 0.0
    retrieval_scope: str | None = None


class AttributeSet(BaseModel):
    """
    Attributes extracted from a system description.

    The LLM populates these; the rules layer consumes them. Keeping the
    structure flat and explicit makes rule evaluation auditable.
    """

    model_config = ConfigDict(extra="forbid")

    purpose: str
    domain: str | None = None
    deployment_context: str | None = None
    user_population: str | None = None
    autonomy_level: str | None = None
    human_oversight: str | None = None
    data_types: list[str] = Field(default_factory=list)
    geography: str | None = None
    is_gpai_model: bool = False
    built_on_gpai: bool = False
    is_safety_component: bool = False
    regulated_product_legislation: str | None = None
    biometric: bool = False
    affects_fundamental_rights: bool = False
    uses_subliminal_techniques: bool = False
    social_scoring: bool = False
    real_time_remote_biometric_id: bool = False
    emotion_recognition: bool = False
    interacts_with_humans: bool = False
    generates_synthetic_content: bool = False
    extras: dict[str, Any] = Field(default_factory=dict)


class ClassificationResult(Frozen):
    """
    Output of the rules layer.

    Deterministic: same AttributeSet + same rules_version => identical result.
    """

    tier: Tier
    fired_rule: str
    supporting_refs: tuple[Citation, ...]
    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = 1.0
    rationale: str = ""
    rules_version: str


class Obligation(Frozen):
    """An obligation owed under the AI Act, with its article reference."""

    obligation_id: str
    summary: str
    article_ref: str
    applies_to: tuple[ActorRole, ...]
    citation: Citation


class GapFinding(Frozen):
    """Result of comparing a declared control against a required obligation."""

    obligation_id: str
    status: str
    notes: str = ""
    declared_evidence: str | None = None


class DraftedDocument(Frozen):
    """A document drafted by draft_documentation (Annex IV skeleton, Art. 50 notice, etc.)."""

    kind: str
    title: str
    body: str
    citations: tuple[Citation, ...]


class ClarificationQuestion(Frozen):
    """A targeted question the agent asks when an attribute is underspecified."""

    attribute: str
    question: str
    why_it_matters: str


class SystemProfile(BaseModel):
    """
    What the client describes plus the attributes extracted from it.

    Kept mutable across the graph because the clarify loop refines it.
    """

    model_config = ConfigDict(extra="forbid")

    description: str
    declared_controls: list[str] = Field(default_factory=list)
    declared_actor_role: ActorRole | None = None
    attributes: AttributeSet | None = None


class RunManifest(Frozen):
    """
    Versioning manifest persisted per assessment.

    Every later phase reads this. Nothing runs unversioned (CLAUDE.md section 12.4).
    """

    run_id: str
    corpus_version: str
    model_id: str
    embedding_model: str
    prompt_set_version: str
    rules_version: str
    timestamp: datetime

    @field_validator("timestamp")
    @classmethod
    def _ensure_tz(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            return v.replace(tzinfo=UTC)
        return v


class AgentState(BaseModel):
    """
    The LangGraph state object.

    Field names match CLAUDE.md section 12.3 exactly; do not rename without
    sweeping the graph nodes.
    """

    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(default_factory=lambda: uuid4().hex)
    manifest: RunManifest | None = None

    system_profile: SystemProfile
    classification: ClassificationResult | None = None
    retrieved_passages: list[RetrievedPassage] = Field(default_factory=list)
    obligations: list[Obligation] = Field(default_factory=list)
    gaps: list[GapFinding] = Field(default_factory=list)
    drafted_documents: list[DraftedDocument] = Field(default_factory=list)

    confidence: Annotated[float, Field(ge=0.0, le=1.0)] = 0.0
    clarification_needed: bool = False
    clarification_questions: list[ClarificationQuestion] = Field(default_factory=list)
    clarification_iterations: int = 0

    trace_events: list[dict[str, Any]] = Field(default_factory=list)
