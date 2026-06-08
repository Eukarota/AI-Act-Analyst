/**
 * Wire shapes returned by the FastAPI backend. Kept narrow on purpose:
 * field renames in the Python AssessmentReport break this file by design,
 * so the TS side cannot drift silently.
 */

export type Tier =
  | "prohibited"
  | "high_risk_annex_i"
  | "high_risk_annex_iii"
  | "transparency"
  | "minimal"
  | "gpai"
  | "gpai_systemic"
  | "undetermined";

export type ActorRole =
  | "provider"
  | "deployer"
  | "distributor"
  | "importer"
  | "product_manufacturer"
  | "authorised_representative";

export type ReportStatus =
  | "complete"
  | "incomplete_clarification_exhausted"
  | "failed";

export interface Citation {
  celex_id: string;
  article: string | null;
  paragraph: string | null;
  annex_ref: string | null;
  recital_ref: string | null;
  lang: string;
  url: string | null;
  corpus_version: string;
}

export interface RetrievedPassage {
  text: string;
  citation: Citation;
  score: number;
  retrieval_scope: string | null;
}

export interface ClassificationResult {
  tier: Tier;
  fired_rule: string;
  supporting_refs: Citation[];
  confidence: number;
  rationale: string;
  rules_version: string;
}

export interface Obligation {
  obligation_id: string;
  summary: string;
  article_ref: string;
  applies_to: ActorRole[];
  citation: Citation;
}

export interface GapFinding {
  obligation_id: string;
  status: string;
  notes: string;
  declared_evidence: string | null;
}

export interface DraftedDocument {
  kind: string;
  title: string;
  body: string;
  citations: Citation[];
}

export interface ClarificationQuestion {
  attribute: string;
  question: string;
  why_it_matters: string;
}

export interface SystemProfile {
  description: string;
  declared_controls: string[];
  declared_actor_role: ActorRole | null;
}

export interface RunManifest {
  run_id: string;
  corpus_version: string;
  model_id: string;
  embedding_model: string;
  prompt_set_version: string;
  rules_version: string;
  timestamp: string;
}

export interface TypedFailure {
  code: string;
  message: string;
  node: string | null;
}

export interface AssessmentReport {
  run_id: string;
  manifest: RunManifest;
  status: ReportStatus;
  grounding_passed: boolean;
  system_profile: SystemProfile;
  classification: ClassificationResult | null;
  clarification_questions: ClarificationQuestion[];
  clarification_iterations: number;
  obligations: Obligation[];
  gaps: GapFinding[];
  drafted_documents: DraftedDocument[];
  retrieved_passages: RetrievedPassage[];
  pre_assessment_notice: string;
  failures: TypedFailure[];
  timestamp: string;
}

export interface AssessResponse {
  report: AssessmentReport;
}

export interface TraceEvent {
  schema_version: string;
  event_id: string;
  run_id: string;
  span_id: string;
  parent_span_id: string | null;
  kind: string;
  name: string;
  timestamp: string;
  latency_ms: number | null;
  input_hash: string | null;
  output_hash: string | null;
  tokens_in: number | null;
  tokens_out: number | null;
  model_id: string | null;
  attributes: Record<string, unknown>;
}
