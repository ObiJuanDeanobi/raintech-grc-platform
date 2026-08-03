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
  determination?: Determination;
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
    prompt_count: number;
    determination_record_count: number;
    declarations: FrameworkDeclarations;
  };
  work_list: RecordIndex[];
  record_index: RecordIndex[];
}

export interface Determination {
  status: Status;
  derived: boolean;
  na_rationale: string;
  addressable_disposition: string | null;
  disposition_reason: string;
  interview_observation: string;
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
  record_id: string;
  working_record: PromptWorkingRecord | null;
  moved_from: { record_id: string; citation: string; title: string } | null;
  placement: { rule_citation: string; reason: string } | null;
}

export interface EvidenceMapping {
  mapping_id: string;
  artifact_id: string;
  name: string;
  relative_path: string;
  rationale: string;
  shared_record_count: number;
}

export interface PromptWorkingRecord {
  status: Status;
  note: string;
  na_rationale: string;
  interview_observation: string;
  updated_at: string | null;
  evidence: EvidenceMapping[];
}

export interface Artifact {
  id: string;
  name: string;
  relative_path: string;
  shared_record_count: number;
}

export interface RecordDetail {
  record: RecordSummary;
  determination: Determination;
  parent: RecordSummary | null;
  parent_prompts: Prompt[];
  context_prompts: Prompt[];
  children: RecordSummary[];
  prompts: Prompt[];
  note: string;
  evidence: EvidenceMapping[];
  position: {
    current: number;
    total: number;
    previous_record_id: string | null;
    next_record_id: string | null;
  } | null;
}
