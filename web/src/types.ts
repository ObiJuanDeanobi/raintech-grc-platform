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
  id: string;
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
  boundary_document: string;
  acknowledgement: {
    document_path: string;
    statement: string;
    actor: { id: string; display_name: string };
    timestamp: string;
  } | null;
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
  position: {
    current: number;
    total: number;
    previous_record_id: string | null;
    next_record_id: string | null;
  };
}
