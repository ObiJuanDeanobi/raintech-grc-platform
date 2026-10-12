import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import { Workspace } from "./App";
import { clientProjectsFixture, cmmcScoreFixture } from "./activeAssessmentFixtures";
import { OverviewView } from "./views/overview/OverviewView";

/**
 * Issue #144: the Overview shows where the engagement stands as counts. Grouped
 * "left before issue" counts open the matching filtered list; no blocker is
 * listed one by one; package generation lives under Reports.
 */

const requirements = [
  { id: "AC.L2-3.1.1", title: "Authorized Access Control", family: "AC" },
  { id: "AC.L2-3.1.3", title: "Control CUI Flow", family: "AC" },
  { id: "AU.L2-3.3.1", title: "System Auditing", family: "AU" },
];

const workList = requirements.flatMap((requirement, index) => [
  {
    record_id: requirement.id, citation: requirement.id, title: requirement.title, work_area: requirement.family,
    record_type: "requirement", parent_id: null, designation: null, sort_order: index * 10, editable_determination: false,
  },
  ...["a", "b"].map((letter, offset) => ({
    record_id: `${requirement.id}${letter}`, citation: `${requirement.id}[${letter}]`, title: `Objective [${letter}]`,
    work_area: requirement.family, record_type: "objective", parent_id: requirement.id, designation: null,
    sort_order: index * 10 + offset + 1, editable_determination: true,
  })),
]);

const readiness = {
  project_id: "project-1", state: "Intake complete", assessment_exists: true,
  supported_states: ["Intake started", "Intake complete"], allowed_next_states: [],
  follow_up_work_required_states: [], follow_up_work_required_when_unresolved_required_fields: true,
  assessment_entry_allowed: true, assessment_entry_blocking_reasons: [], profile_completion_blocking_reasons: [],
  current_details: { unresolved_required_fields: [], follow_up_work: "", reviewed_by: "", approval_evidence: "" },
};

const cmmcOverview = {
  variant: "cmmc",
  steps: [
    { label: "Scope", figure: "Profile approved", target: "profile" },
    { label: "Assess", figure: "4 of 6 objectives decided", target: "assessments" },
    { label: "Remediate", figure: "1 open POA&M items · 1 gaps without a plan", target: "assessments" },
    { label: "Deliver", figure: "323 items left before issue", target: "reports" },
  ],
  families: [
    { name: "AC", decided: 3, total: 4, not_met: 1 },
    { name: "AU", decided: 1, total: 2, not_met: 0 },
  ],
  not_met: [{ record_id: "AC.L2-3.1.3", citation: "AC.L2-3.1.3", title: "Control CUI Flow", poam_state: "none" }],
  not_met_without_poam: { count: 1, requirement_ids: ["AC.L2-3.1.3"] },
  resume: { record_id: "AU.L2-3.3.1", citation: "AU.L2-3.3.1", title: "System Auditing", updated_at: "2026-10-12T10:00:00Z" },
  status_counts: null,
  left_before_issue: {
    ready: false,
    count: 323,
    groups: [
      { key: "undecided", label: "Objectives not decided", count: 320, record_ids: ["AU.L2-3.3.1b"], target: "assessments" },
      { key: "met_no_evidence", label: "Met, evidence still needed", count: 2, record_ids: ["AC.L2-3.1.1a", "AC.L2-3.1.1b"], target: "assessments" },
      { key: "ssp", label: "SSP not approved", count: 1, record_ids: [], target: "ssp" },
      { key: "recheck", label: "Records to recheck", count: 1, record_ids: ["AU.L2-3.3.1a"], target: "assessments" },
      { key: "profile", label: "Profile not approved", count: 2, record_ids: [], target: "profile" },
      { key: "other", label: "Other items", count: 1, record_ids: [], target: "overview" },
    ],
  },
};

const hipaaOverview = {
  variant: "hipaa",
  steps: cmmcOverview.steps.map((step) => ({ ...step })),
  families: [],
  not_met: [],
  not_met_without_poam: null,
  resume: null,
  status_counts: [
    { rule: "security", total: 10, counts: { Met: 4, "Not Met": 2, Pending: 1, "N/A": 0, Blank: 3 } },
    { rule: "privacy", total: 5, counts: { Met: 1, "Not Met": 0, Pending: 0, "N/A": 1, Blank: 3 } },
  ],
  left_before_issue: { ready: false, count: 12, groups: [{ key: "undecided", label: "Objectives not decided", count: 12, record_ids: [], target: "assessments" }] },
};

function cmmcAssessment() {
  return {
    id: "assessment-1",
    project: { id: "project-1", name: "CMMC 2026", client_id: "client-1", client_name: "Synthetic Defense" },
    framework: {
      id: "cmmc-l2", name: "CMMC Level 2", record_count: workList.length, walkthrough_record_count: workList.length,
      prompt_count: 0, determination_record_count: 6,
      declarations: {
        record_shape: { hierarchy: ["requirement", "objective"], determination_rule: "records_without_children" },
        rollup_rule: { precedence: ["Not Met", "Pending"], blank_children_prevent_met: true, satisfied_child_statuses: ["Met"], satisfied_rollup_status: "Met", blank_status: "" },
        status_set: ["", "Met", "Not Met", "Pending"],
        presentation_mode: "requirement_with_objectives",
        findings_rule: "requirement_level",
        close_readiness: { fieldwork_ready_for_generation: {} },
        scoring: { authority: "32 CFR 170.24", requirements: Object.fromEntries(requirements.map((r) => [r.id, { rule: "fixed", points: 5, source: "32 CFR 170.24" }])) },
      },
    },
    progress: { resolved_determination_count: 4, determination_record_count: 6 },
    work_list: workList, record_index: workList,
    record_states: Object.fromEntries(workList.map((record) => [record.record_id, { status: "", evidence_count: 0, open_poam_count: 0, verification: null }])),
    not_met_without_poam: { count: 0, requirement_ids: [] },
  };
}

function mockCmmcServer(overview: unknown = cmmcOverview) {
  const calls: string[] = [];
  vi.mocked(fetch).mockImplementation(async (input) => {
    const url = String(input);
    calls.push(url);
    if (url.endsWith("/profile-readiness")) return Response.json(readiness);
    if (url === "/api/projects/project-1/assessment") return Response.json(cmmcAssessment());
    if (url.endsWith("/overview")) return Response.json(overview);
    const recordMatch = url.match(/\/records\/([^/]+)$/);
    if (recordMatch) {
      const id = decodeURIComponent(recordMatch[1]);
      const record = workList.find((item) => item.record_id === id)!;
      return Response.json({
        record: { ...record, regulation_text: `Text for ${id}.` },
        determination: { status: "", derived: !record.parent_id, na_rationale: "", addressable_disposition: null, disposition_reason: "", interview_observation: "", verification: null },
        parent: null, parent_prompts: [], context_prompts: [], prompts: [], no_prompt_explanation: null,
        children: [], note: "", evidence: [], practitioner_guidance: null,
        position: { current: 1, total: workList.length, previous_record_id: null, next_record_id: null },
      });
    }
    if (url.endsWith("/finding")) return Response.json(null);
    if (url.endsWith("/cmmc-score")) return Response.json({ ...cmmcScoreFixture([{ record_id: "AC.L2-3.1.3", title: "Control CUI Flow", points: 5, state: "not_met" }]), not_met_without_poam: { count: 1, requirement_ids: [] } });
    if (url.includes("close-readiness")) return Response.json({ status: "Blocked", blockers: [], checks: [] });
    if (url.endsWith("/packages")) return Response.json([]);
    if (url.endsWith("/ssp")) return Response.json(null);
    if (url.includes("/evidence")) return Response.json([]);
    if (url === "/api/backups") return Response.json({ warning: null, backups: [] });
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  return calls;
}

function renderOverview() {
  return render(
    <Workspace clients={clientProjectsFixture()} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} initialView="overview" />,
  );
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

test("the step rail shows Scope, Assess, Remediate and Deliver with one figure each", async () => {
  mockCmmcServer();
  renderOverview();
  const rail = await screen.findByRole("navigation", { name: "Engagement steps" });
  const steps = within(rail).getAllByRole("button");
  expect(steps.map((step) => step.querySelector("strong")?.textContent)).toEqual(["Scope", "Assess", "Remediate", "Deliver"]);
  expect(steps[0]).toHaveTextContent("Profile approved");
  expect(steps[1]).toHaveTextContent("4 of 6 objectives decided");
  expect(steps[2]).toHaveTextContent("1 open POA&M items · 1 gaps without a plan");
  expect(steps[3]).toHaveTextContent("323 items left before issue");
});

test("shows the score, the family table and the NOT MET list, without the old blocks or any one-by-one blockers", async () => {
  mockCmmcServer();
  renderOverview();
  const score = await screen.findByRole("region", { name: "CMMC score and Conditional status" });
  expect(score).toHaveTextContent("VERIFIED SPRS");
  expect(score).toHaveTextContent("Projected (includes Met awaiting evidence)");
  expect(within(score).getByRole("region", { name: "32 CFR 170.21 Conditional status checks" })).toBeVisible();

  const families = screen.getByRole("region", { name: "Progress by family" });
  expect(within(families).getByRole("row", { name: /Access Control AC 3 of 4/ })).toBeVisible();
  const notMet = screen.getByRole("region", { name: "NOT MET requirements" });
  expect(within(notMet).getByText("Control CUI Flow")).toBeVisible();
  expect(within(notMet).getByText("No POA&M")).toBeVisible();

  // Removed from the Overview.
  expect(screen.queryByText("determinations")).not.toBeInTheDocument();
  expect(screen.queryByText("Client projects")).not.toBeInTheDocument();
  expect(screen.queryByText("PROFILE READINESS")).not.toBeInTheDocument();
  expect(screen.queryByText("Fieldwork ready for generation")).not.toBeInTheDocument();
  expect(screen.queryByText("Assessment package")).not.toBeInTheDocument();
  // Grouped counts, never one line per blocker.
  const left = screen.getByRole("region", { name: "Left before issue" });
  expect(within(left).getAllByRole("listitem")).toHaveLength(6);
  expect(screen.getByRole("region", { name: "Continue where you left off" })).toHaveTextContent("System Auditing");
});

test("a grouped count opens Assessments filtered to its records and the chip clears it", async () => {
  mockCmmcServer();
  renderOverview();
  const user = userEvent.setup();
  const left = await screen.findByRole("region", { name: "Left before issue" });
  await user.click(within(left).getByRole("button", { name: "Met, evidence still needed: 2" }));

  const chip = await screen.findByRole("status");
  expect(chip).toHaveTextContent("Showing: Met, evidence still needed (2) · Show all");
  expect(screen.getByRole("button", { name: "Assessments" })).toHaveClass("active");
  const list = screen.getByRole("navigation", { name: "Requirements by family" });
  // Objectives map to their requirement; others are hidden.
  expect(within(list).getByRole("button", { name: /Authorized Access Control/ })).toBeVisible();
  expect(within(list).queryByRole("button", { name: /System Auditing/ })).not.toBeInTheDocument();
  expect(within(list).queryByRole("button", { name: /Control CUI Flow/ })).not.toBeInTheDocument();

  await user.click(within(chip).getByRole("button", { name: "Show all" }));
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
  const all = screen.getByRole("navigation", { name: "Requirements by family" });
  const headers = within(all).getAllByRole("button", { expanded: false });
  for (const header of headers) await user.click(header);
  expect(within(all).getByRole("button", { name: /System Auditing/ })).toBeVisible();
});

test("Show every item lists the flat blockers only on request", async () => {
  const calls = mockCmmcServer();
  renderOverview();
  const user = userEvent.setup();
  await screen.findByRole("region", { name: "Left before issue" });
  expect(calls.some((url) => url.includes("close-readiness"))).toBe(false);
  await user.click(screen.getByRole("button", { name: "Show every item" }));
  expect(await screen.findByRole("button", { name: "Hide every item" })).toBeVisible();
  expect(calls.some((url) => url.includes("close-readiness"))).toBe(true);
});

test("package generation is reachable from Reports", async () => {
  mockCmmcServer();
  renderOverview();
  const user = userEvent.setup();
  await screen.findByRole("region", { name: "Left before issue" });
  await user.click(screen.getByRole("button", { name: "Reports" }));
  expect(await screen.findByRole("heading", { name: "Assessment package" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Reports" })).toHaveClass("active");
  expect(screen.queryByRole("region", { name: "Left before issue" })).not.toBeInTheDocument();
});

test("HIPAA shows counts by status per rule, grouped counts and no score", async () => {
  vi.mocked(fetch).mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith("/overview")) return Response.json(hipaaOverview);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  render(
    <OverviewView
      projectId="project-1" assessmentId="assessment-1" projectName="HIPAA 2026" clientName="Northwind Health"
      frameworkName="HIPAA 45 CFR Part 164" scored={false} refreshKey={0}
      onOpenStep={vi.fn()} onOpenGroup={vi.fn()} onOpenRecord={vi.fn()}
    />,
  );
  const table = await screen.findByRole("region", { name: "Status by rule" });
  expect(within(table).getByRole("row", { name: /Security Rule 4 2 1 0 3/ })).toBeVisible();
  expect(within(table).getByRole("row", { name: /Privacy Rule/ })).toBeVisible();
  expect(screen.getByRole("region", { name: "Left before issue" })).toHaveTextContent("Objectives not decided");
  expect(screen.queryByText(/SPRS/)).not.toBeInTheDocument();
  expect(screen.queryByText(/Projected/)).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "CMMC score and Conditional status" })).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "NOT MET requirements" })).not.toBeInTheDocument();
  expect(screen.queryByText(/%/)).not.toBeInTheDocument();
});

test("Records to recheck opens the filtered list", async () => {
  mockCmmcServer();
  renderOverview();
  const user = userEvent.setup();
  const left = await screen.findByRole("region", { name: "Left before issue" });
  await user.click(within(left).getByRole("button", { name: "Records to recheck: 1" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Showing: Records to recheck (1) · Show all");
  const list = screen.getByRole("navigation", { name: "Requirements by family" });
  expect(within(list).getByRole("button", { name: /System Auditing/ })).toBeVisible();
  expect(within(list).queryByRole("button", { name: /Authorized Access Control/ })).not.toBeInTheDocument();
});

test("SSP not approved opens the requirement view where the SSP is edited, never a dead end", async () => {
  mockCmmcServer();
  renderOverview();
  const user = userEvent.setup();
  const left = await screen.findByRole("region", { name: "Left before issue" });
  await user.click(within(left).getByRole("button", { name: "SSP not approved: 1" }));
  expect(screen.getByRole("button", { name: "Assessments" })).toHaveClass("active");
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
  expect(await screen.findByRole("heading", { level: 1, name: "Authorized Access Control" })).toBeVisible();
  expect(await screen.findByText("System Security Plan")).toBeVisible();
});

test("Profile not approved opens Profile and Other items opens Reports", async () => {
  mockCmmcServer();
  renderOverview();
  const user = userEvent.setup();
  const left = await screen.findByRole("region", { name: "Left before issue" });
  await user.click(within(left).getByRole("button", { name: "Other items: 1" }));
  expect(screen.getByRole("button", { name: "Reports" })).toHaveClass("active");
  await user.click(screen.getByRole("button", { name: "Overview" }));
  await user.click(await within(await screen.findByRole("region", { name: "Left before issue" })).findByRole("button", { name: "Profile not approved: 2" }));
  expect(screen.getByRole("button", { name: "Profile" })).toHaveClass("active");
});

test("other client projects stay one click away and switch the project", async () => {
  mockCmmcServer();
  const onProjectChange = vi.fn();
  render(
    <Workspace clients={clientProjectsFixture()} projectId="project-1" onProjectChange={onProjectChange} onWorkspaceCreated={vi.fn()} initialView="overview" />,
  );
  const other = await screen.findByRole("region", { name: "Other client projects" });
  expect(other).toHaveTextContent("Northwind Health");
  expect(other).toHaveTextContent("HIPAA B");
  await userEvent.setup().click(within(other).getByRole("button", { name: /HIPAA B/ }));
  expect(onProjectChange).toHaveBeenCalledWith("project-2");
});

test("a grouped-count filter stays live as the work changes", async () => {
  let loads = 0;
  mockCmmcServer();
  const base = vi.mocked(fetch).getMockImplementation()!;
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    if (String(input).endsWith("/overview")) {
      loads += 1;
      // The Overview loads once; later loads see one record already fixed.
      const record_ids = loads === 1 ? ["AC.L2-3.1.1a", "AC.L2-3.1.1b"] : ["AC.L2-3.1.1b"];
      const groups = cmmcOverview.left_before_issue.groups.map((group) => (group.key === "met_no_evidence" ? { ...group, count: record_ids.length, record_ids } : group));
      return Response.json({ ...cmmcOverview, left_before_issue: { ...cmmcOverview.left_before_issue, groups } });
    }
    return base(input, init);
  });
  renderOverview();
  const user = userEvent.setup();
  const left = await screen.findByRole("region", { name: "Left before issue" });
  await user.click(within(left).getByRole("button", { name: "Met, evidence still needed: 2" }));
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Showing: Met, evidence still needed (1) · Show all"));
});
