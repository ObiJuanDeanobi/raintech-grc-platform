export type Status = string;

export interface FrameworkDeclarations {
  record_shape: {
    hierarchy: string[];
    determination_rule: string;
  };
  rollup_rule: {
    precedence: string[];
    blank_children_prevent_met: boolean;
    satisfied_child_statuses: string[];
    satisfied_rollup_status: string;
    blank_status: string;
  };
  status_set: Status[];
  designation_rules?: Record<
    string,
    { dispositions: string[]; reason_required_for: string[] }
  >;
  presentation_mode: string;
  // Declared only by frameworks with a fieldwork close and package workflow.
  close_readiness?: Record<string, unknown>;
  // CMMC: official point values from 32 CFR 170.24, keyed by requirement.
  scoring?: {
    authority: string;
    requirements: Record<string, { rule: string; points?: number; source: string; note?: string }>;
  };
  sra?: {
    anchor_record_id: string;
    work_area: string;
  };
}

export interface FrameworkOption {
  id: string;
  name: string;
}

export interface Project {
  id: string;
  name: string;
  framework_version_id: string;
}

export interface Client {
  id: string;
  name: string;
  projects: Project[];
}

export interface RecordIndex {
  record_id: string;
  citation: string;
  title: string;
  work_area: string;
  record_type: string;
  parent_id: string | null;
  designation: string | null;
  sort_order: number;
  editable_determination?: boolean;
}

export interface Assessment {
  /** The active revision identity. The legacy project route resolves this ID. */
  id: ActiveAssessmentId;
  project: {
    id: string;
    name: string;
    client_id: string;
    client_name: string;
  };
  framework: {
    id: string;
    name: string;
    record_count: number;
    walkthrough_record_count: number;
    prompt_count: number;
    determination_record_count: number;
    declarations: FrameworkDeclarations;
  };
  progress: {
    resolved_determination_count: number;
    determination_record_count: number;
  };
  work_list: RecordIndex[];
  record_index: RecordIndex[];
  reopening?: AssessmentReopening | null;
  revalidation_items?: RevalidationItem[];
}

export interface AssessmentReopening {
  id: string;
  classification: "substantive";
  rationale: string;
  affected_record_ids_json: string;
  predecessor_assessment_id: string;
  successor_assessment_id: string;
  prior_package_id: string;
  prior_issuance_id: string;
  actor_id: string;
  created_at: string;
}

export interface RevalidationItem {
  id: string;
  record_id: string;
  revalidated_by: string | null;
  revalidated_at: string | null;
  note: string;
}

export type ActiveAssessmentId = string;

export interface CloseReadiness {
  target: string;
  status: "Ready" | "Blocked" | string;
  checks: Array<Record<string, unknown>>;
  blockers: Array<Record<string, unknown> | string>;
  links?: Array<Record<string, unknown>>;
  informational?: Record<string, unknown>;
  metadata?: Record<string, unknown>;
}

export interface GeneratedPackageComponent {
  id: string;
  kind: string;
  filename: string;
  relative_path?: string;
  sha256?: string;
  byte_count?: number;
  download_url?: string;
}

export interface GeneratedPackage {
  id: string;
  assessment_id: string;
  state: string;
  created_at: string;
  source_snapshot_id?: string;
  source_sha256?: string;
  template_version?: string;
  components: GeneratedPackageComponent[];
  manifest?: { components?: GeneratedPackageComponent[]; source_snapshot_sha256?: string; template_version?: string };
  issuance_status?: "Current" | "Superseded" | null;
  issued_snapshot_id?: string | null;
  superseded_by_package_id?: string | null;
  correction?: PackageCorrection | null;
  reopening?: AssessmentReopening | null;
}

export interface PackageCorrection {
  id: string;
  classification: "presentation_only";
  reason: string;
  actor_id: string;
  prior_package_id: string;
  prior_issuance_id: string;
  result_package_id: string;
  created_at: string;
}

export interface IssueReadiness {
  target: string;
  status: string;
  checks: Array<Record<string, unknown>>;
  blockers: Array<Record<string, unknown> | string>;
  package_id?: string;
  source_snapshot_id?: string;
  source_sha256?: string;
  manifest_sha256?: string;
  backup_id?: string;
  backup_manifest_sha256?: string;
  backup_completed_at?: string;
  issued_snapshot_id?: string;
  issued_at?: string;
  issuance_status?: "Current" | "Superseded" | null;
  superseded_by_package_id?: string | null;
  correction?: PackageCorrection | null;
  failure?: { stage?: string; component?: string; reason?: string; attempt_id?: string };
}

export interface PackageReview {
  package_id: string;
  state: string;
  reviewer_name?: string;
  reviewer_role?: string;
  note?: string;
  component_confirmations?: Record<string, boolean>;
  source_snapshot_sha256?: string;
  template_version?: string;
  drift?: string[];
  blockers?: string[];
  updated_at?: string;
}

export interface ProfileReadiness {
  project_id: string;
  state: string;
  assessment_exists: boolean;
  supported_states: string[];
  allowed_next_states: string[];
  assessment_entry_allowed: boolean;
  assessment_entry_blocking_reasons: string[];
  profile_completion_blocking_reasons: string[];
  follow_up_work_required_states: string[];
  follow_up_work_required_when_unresolved_required_fields: boolean;
  current_details: {
    unresolved_required_fields: string[];
    follow_up_work: string;
    reviewed_by: string;
    approval_evidence: string;
  };
}

export interface Determination {
  status: Status;
  derived: boolean;
  na_rationale: string;
  addressable_disposition: string | null;
  disposition_reason: string;
  interview_observation: string;
}

export type ReconciliationDisposition = "create" | "link_existing" | "not_needed";
export interface ReconciliationLink {
  id: string;
  finding_id?: string | null;
  title?: string;
  status?: string;
  linked_at?: string;
  linked_by?: string;
  type?: "finding" | "corrective_action";
  description?: string;
  validation_state?: string;
}
export interface ReconciliationRecord {
  state?: "pending" | "unresolved" | "reconciled";
  outcome?: ReconciliationDisposition;
  prefill?: Record<string, string | null>;
  evidence_references?: Array<{
    mapping_id: string;
    artifact_id: string;
    version_id: string;
    name: string;
    relative_path: string;
    review_state: string;
    sha256: string;
  }>;
  finding_id?: string | null;
  corrective_action_id?: string | null;
  links: ReconciliationLink[];
  history: Array<{ id: string; outcome: ReconciliationDisposition; rationale?: string; changed_at: string; actor_id?: string }>;
}

export interface CorrectiveActionValidation {
  finding: { id: string; title: string; description?: string; status?: string };
  corrective_action: { id: string; title: string; description?: string; status: string; validation_state?: string };
  determination: { status: string; interview_observation?: string } | null;
  events: Array<Record<string, unknown> & {
    id: string;
    outcome: "Validated" | "Failed";
    notes: string;
    created_at: string;
    prior_determination: "Not Met";
    evidence_context: { interview_observation?: string; presented: Array<{ name: string; sha256: string }> };
  }>;
}

export interface RecordSummary {
  record_id: string;
  citation: string;
  title: string;
  regulation_text: string;
  work_area: string;
  record_type: string;
  parent_id: string | null;
  designation: string | null;
  editable_determination: boolean;
  determination?: Determination;
  prompts_collapsed_by_default?: boolean;
}

export interface Prompt {
  id: string;
  text: string;
  source: string;
  source_detail: string;
  cfr_paragraph: string;
  group: string;
  role: string;
  role_reason: string;
  render_checkbox: boolean;
  answer: string;
}

export interface EvidenceMapping {
  mapping_id: string;
  artifact_id: string;
  name: string;
  relative_path: string;
  rationale: string;
  review_state: string;
  shared_record_count: number;
  version_id: string;
  version_project_id: string;
  version_number: number;
  sha256: string;
  latest_version_number?: number;
  review_date?: string | null;
}

export interface Artifact {
  id: string;
  name: string;
  relative_path: string;
  shared_record_count: number;
  version_id: string;
  version_number: number;
  sha256: string;
  version_relative_path: string;
  version_created_at: string;
  review_date?: string | null;
  overdue?: boolean;
  deleted_at?: string | null;
  purged_at?: string | null;
}

export type ProfileItemType =
  | "scope_item"
  | "environment"
  | "business_process"
  | "location"
  | "external_service"
  | "person_role"
  | "exclusion_constraint"
  | "reference"
  | "unknown_follow_up";

export interface ProfileValue {
  id?: string;
  target_key?: string;
  section: string;
  field_key: string;
  label: string;
  value: string;
  source: string;
  reviewer: string;
  last_reviewed_at: string;
  sort_order?: number;
}

export interface ProfileItem {
  id?: string;
  client_key: string;
  item_type: ProfileItemType;
  environment_item_id: string | null;
  environment_item_key?: string | null;
  sort_order?: number;
  values: ProfileValue[];
}

export interface ProfileLifecycleEvent {
  id: string;
  status: "Draft" | "Reviewed" | "Approved";
  actor: { id: string; display_name: string };
  reviewer: string;
  content_revision?: string;
  timestamp: string;
}

export interface ProfileEvidenceMapping {
  mapping_id: string;
  artifact_id: string;
  name: string;
  uploaded_file_id: string;
  evidence_version_id: string;
  version_number: number;
  sha256: string;
  relative_path: string;
  target_type: "profile";
  target_key: string;
  rationale: string;
  review_state: string;
  created_at: string;
  content_revision?: string;
}

export interface ProfileVersion {
  id: string;
  project_id: string;
  version_number: number;
  status: "Draft" | "Reviewed" | "Approved";
  created_by: string;
  created_at: string;
  content_revision: string;
  values: ProfileValue[];
  items: ProfileItem[];
  lifecycle: ProfileLifecycleEvent[];
  evidence: ProfileEvidenceMapping[];
}

export interface ProjectProfile {
  project_id: string;
  active_version_id: string | null;
  versions: ProfileVersion[];
  template: {
    available: boolean;
    name: string | null;
    message: string;
  };
}

export interface SraScopeItem {
  id: string | null;
  scope_type: string;
  target_key: string;
  name: string;
  included: boolean | null;
  exclusion_rationale: string;
  reviewed_by: string;
  reviewed_at: string | null;
}

export interface RiskScore {
  likelihood: number;
  impact: number;
  score: number;
  band: "Low" | "Moderate" | "High" | "Critical";
}

export interface SraRisk {
  id: string;
  profile_version_id: string;
  assessment_id: string;
  title: string;
  threat: string;
  vulnerability: string;
  cia_impact: string;
  safeguards: string;
  corrective_action: string;
  inherent_likelihood: number;
  inherent_impact: number;
  residual_likelihood: number;
  residual_impact: number;
  treatment: "corrective_action" | "acceptance";
  owner: string;
  status: string;
  acceptance_rationale: string;
  approver: string;
  approved_at: string | null;
  review_date: string | null;
  reviewed_by: string;
  reviewed_at: string;
  inherent: RiskScore;
  residual: RiskScore;
  evidence_links: EvidenceMapping[];
}

export interface SraWorkspace {
  project_id: string;
  assessment_id: string | null;
  profile_version_id: string;
  work_area: string;
  status: "Complete" | "Incomplete";
  anchor: Pick<RecordSummary, "record_id" | "citation" | "title" | "work_area"> & {
    regulation_text: string;
  };
  scope_items: SraScopeItem[];
  risks: SraRisk[];
  blockers: string[];
  completion: { complete: boolean; percentage: number; missing: string[] };
}

export interface RecordDetail {
  record: RecordSummary;
  determination: Determination;
  parent: RecordSummary | null;
  parent_prompts: Prompt[];
  context_prompts: Prompt[];
  children: RecordSummary[];
  prompts: Prompt[];
  no_prompt_explanation: string | null;
  note: string;
  evidence: EvidenceMapping[];
  // RainTech worksheet guidance. Display only; never framework authority.
  practitioner_guidance?: { provenance: string; fields: Record<string, string> } | null;
  position: {
    current: number;
    total: number;
    previous_record_id: string | null;
    next_record_id: string | null;
  };
}

export interface CmmcScore {
  authority: string;
  maximum_score: number;
  minimum_score: number;
  score: number;
  complete: boolean;
  blockers: string[];
  deductions: { record_id: string; citation: string; title: string; points: number | null; source: string; conditional_poam_allowed: boolean }[];
  unscored: { record_id: string; status: string }[];
  partial_inputs_needed: string[];
  partial_implementations: Record<string, { implementation: "partial" | "none"; rationale: string }>;
  follow_up: { record_id: string; requirement_id: string; kind: string }[];
  conditional: { source: string; score_ratio: number; eligible: boolean };
}

export interface RequirementFinding {
  finding: { id: string; title: string; status: string };
  requirement_id: string;
  requirement_status: string;
  failed_objectives: { record_id: string; citation: string; regulation_text: string; note: string; interview_observation: string; evidence: { name: string; rationale: string }[] }[];
  poam_items: { id: string; title: string; description: string; status: string; validation_state: string }[];
  history: { event: string; failed_objectives: string[]; created_at: string }[];
}

export interface SspView {
  id: string;
  template_version: string;
  source_sha256: string;
  source: { requirements: { record_id: string; citation: string; status: string; poam_items: string[] }[] };
  versions: { id: string; version_number: number; note: string; created_at: string }[];
  latest: {
    id: string;
    version_number: number;
    content: {
      system_description: string;
      environment_narrative: string;
      requirements: Record<string, { implementation: string }>;
    };
  };
  missing_for_approval: string[];
  approval: { approver_id: string; approved_at: string } | null;
}
