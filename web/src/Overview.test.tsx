import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import { Workspace } from "./App";
import { clientProjectsFixture, cmmcScoreFixture } from "./activeAssessmentFixtures";
import { OverviewView } from "./views/overview/OverviewView";

/**
 * Issue #144, ADR 0022: the Overview shows where the engagement stands as progress
 * and the next piece of work. Each progress figure opens the matching filtered list.
 * It never shows blockers ("left before issue", "not approved", FAIL); those appear
 * only in the Finalize dialog under Deliverables.
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

const group = (key: string, label: string, count: number, record_ids: string[], target = "assessments") => ({ key, label, count, record_ids, target });

const cmmcOverview = {
  variant: "cmmc",
  steps: [
    { label: "Scope", figure: "Profile: 14 of 20 facts known · 2 to follow up", parts: [{ text: "Profile: 14 of 20 facts known · 2 to follow up", group: null }], target: "profile" },
    { label: "Assess", figure: "4 of 6 decided", parts: [{ text: "4 of 6 decided", group: group("undecided", "Not decided yet", 2, ["AU.L2-3.3.1b"]) }], target: "assessments" },
    {
      label: "Remediate", figure: "1 gap needs a POA&M · 0 POA&M items open",
      parts: [
        { text: "1 gap needs a POA&M", group: group("gaps_no_plan", "NOT MET without a POA&M", 1, ["AC.L2-3.1.3"]) },
        { text: "0 POA&M items open", group: null },
      ],
      target: "assessments",
    },
    { label: "Deliver", figure: "Draft available", parts: [{ text: "Draft available", group: null }], target: "reports" },
  ],
  families: [
    { name: "AC", decided: 3, total: 4, not_met: 1 },
    { name: "AU", decided: 1, total: 2, not_met: 0 },
  ],
  not_met: [{ record_id: "AC.L2-3.1.3", citation: "AC.L2-3.1.3", title: "Control CUI Flow", poam_state: "none" }],
  not_met_without_poam: { count: 1, requirement_ids: ["AC.L2-3.1.3"] },
  resume: { record_id: "AU.L2-3.3.1", citation: "AU.L2-3.3.1", title: "System Auditing", updated_at: "2026-10-12T10:00:00Z" },
  status_counts: null,
  evidence_progress: { text: "2 Met awaiting evidence", group: group("met_no_evidence", "Met, evidence still needed", 2, ["AC.L2-3.1.1a", "AC.L2-3.1.1b"]) },
};

/** A brand-new project: nothing decided, nothing to follow up. */
const newCmmcOverview = {
  ...cmmcOverview,
  steps: [
    { label: "Scope", figure: "Profile: 1 of 1 facts known", parts: [{ text: "Profile: 1 of 1 facts known", group: null }], target: "profile" },
    { label: "Assess", figure: "0 of 320 decided", parts: [{ text: "0 of 320 decided", group: group("undecided", "Not decided yet", 320, ["AU.L2-3.3.1b"]) }], target: "assessments" },
    { label: "Remediate", figure: "0 gaps need a POA&M · 0 POA&M items open", parts: [{ text: "0 gaps need a POA&M", group: null }, { text: "0 POA&M items open", group: null }], target: "assessments" },
    { label: "Deliver", figure: "Draft available", parts: [{ text: "Draft available", group: null }], target: "reports" },
  ],
  families: cmmcOverview.families.map((family) => ({ ...family, decided: 0, not_met: 0 })),
  not_met: [],
  not_met_without_poam: { count: 0, requirement_ids: [] },
  resume: null,
  evidence_progress: null,
};

const hipaaOverview = {
  variant: "hipaa",
  steps: [
    { label: "Scope", figure: "Profile: 1 of 1 facts known", parts: [{ text: "Profile: 1 of 1 facts known", group: null }], target: "profile" },
    { label: "Assess", figure: "0 of 149 decided", parts: [{ text: "0 of 149 decided", group: group("undecided", "Not decided yet", 149, []) }], target: "assessments" },
    { label: "Remediate", figure: "0 corrective actions open", parts: [{ text: "0 corrective actions open", group: null }], target: "assessments" },
    { label: "Deliver", figure: "Final v2 · 12 Oct 2026", parts: [{ text: "Final v2 · 12 Oct 2026", group: null }], target: "reports" },
  ],
  families: [],
  not_met: [],
  not_met_without_poam: null,
  resume: null,
  status_counts: [
    { rule: "security", total: 10, counts: { Met: 4, "Not Met": 2, Pending: 1, "N/A": 0, Blank: 3 } },
    { rule: "privacy", total: 5, counts: { Met: 1, "Not Met": 0, Pending: 0, "N/A": 1, Blank: 3 } },
  ],
  evidence_progress: null,
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
    not_met_without_poam: { count: 1, requirement_ids: ["AC.L2-3.1.3"] },
  };
}

interface ServerOptions {
  overview?: unknown;
  score?: unknown;
  checklistGroups?: unknown[];
}

function mockCmmcServer(options: ServerOptions = {}) {
  const overview = options.overview ?? cmmcOverview;
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
    if (url.endsWith("/cmmc-score")) return Response.json(options.score ?? { ...cmmcScoreFixture([{ record_id: "AC.L2-3.1.3", title: "Control CUI Flow", points: 5, state: "not_met" }]), not_met_without_poam: { count: 1, requirement_ids: ["AC.L2-3.1.3"] } });
    if (url.endsWith("/packages")) return Response.json([]);
    if (url.endsWith("/profile")) return Response.json({ active_version_id: "pv-1", versions: [{ id: "pv-1", version_number: 1 }] });
    if (url.includes("/issue-checklist")) return Response.json({ ready: false, groups: options.checklistGroups ?? [], warnings: [], current_issue: null });
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

/** Every phrase that would make the Overview read as a list of blockers. */
const BLOCKER_PHRASES = [/left before issue/i, /not approved/i, /\bFAIL\b/, /Final determination required/i, /Show every item/i, /Must be fixed/i, /blocker/i];

function expectNoBlockerText(root: HTMLElement) {
  for (const phrase of BLOCKER_PHRASES) expect(root).not.toHaveTextContent(phrase);
}

test("the step rail shows progress and next work for Scope, Assess, Remediate and Deliver", async () => {
  mockCmmcServer();
  renderOverview();
  const rail = await screen.findByRole("navigation", { name: "Engagement steps" });
  const steps = Array.from(rail.querySelectorAll(".step"));
  expect(steps.map((step) => step.querySelector("strong")?.textContent)).toEqual(["Scope", "Assess", "Remediate", "Deliver"]);
  expect(steps[0]).toHaveTextContent("Profile: 14 of 20 facts known · 2 to follow up");
  expect(steps[1]).toHaveTextContent("4 of 6 decided");
  expect(steps[2]).toHaveTextContent("1 gap needs a POA&M · 0 POA&M items open");
  expect(steps[3]).toHaveTextContent("Draft available");
  // Progress, never a verdict or an item count.
  expectNoBlockerText(rail);
  expect(rail).not.toHaveTextContent(/items? left/i);
});

test("a final version reads 'Final v2 · 12 Oct 2026' on the Deliver step", async () => {
  mockCmmcServer({ overview: { ...cmmcOverview, steps: cmmcOverview.steps.map((step) => (step.label === "Deliver" ? { ...step, figure: "Final v2 · 12 Oct 2026", parts: [{ text: "Final v2 · 12 Oct 2026", group: null }] } : step)) } });
  renderOverview();
  const rail = await screen.findByRole("navigation", { name: "Engagement steps" });
  expect(within(rail).getByRole("button", { name: "Final v2 · 12 Oct 2026" })).toBeVisible();
  expect(rail).not.toHaveTextContent("Draft available");
});

test("a figure with no list behind it opens its step", async () => {
  mockCmmcServer();
  renderOverview();
  const user = userEvent.setup();
  const rail = await screen.findByRole("navigation", { name: "Engagement steps" });
  await user.click(within(rail).getByRole("button", { name: "Profile: 14 of 20 facts known · 2 to follow up" }));
  expect(screen.getByRole("button", { name: "Profile" })).toHaveClass("active");
  await user.click(screen.getByRole("button", { name: "Overview" }));
  await user.click(within(await screen.findByRole("navigation", { name: "Engagement steps" })).getByRole("button", { name: "Draft available" }));
  expect(screen.getByRole("button", { name: "Deliverables" })).toHaveClass("active");
});

test("shows the score, the family table and the NOT MET list, without the old blocks or any blockers", async () => {
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
  expect(screen.queryByRole("region", { name: "Left before issue" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: /Show every item/ })).not.toBeInTheDocument();
  expect(screen.getByRole("region", { name: "Continue where you left off" })).toHaveTextContent("System Auditing");
});

test("a progress figure opens Assessments filtered to its records and the chip clears it", async () => {
  mockCmmcServer();
  renderOverview();
  const user = userEvent.setup();
  const progress = await screen.findByLabelText("Evidence progress");
  expect(progress).toHaveTextContent("Evidence: 2 Met awaiting evidence");
  await user.click(within(progress).getByRole("button", { name: "2 Met awaiting evidence" }));

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

test("the Assess figure opens the not-decided list", async () => {
  mockCmmcServer();
  renderOverview();
  const user = userEvent.setup();
  const rail = await screen.findByRole("navigation", { name: "Engagement steps" });
  await user.click(within(rail).getByRole("button", { name: "4 of 6 decided" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Showing: Not decided yet (2) · Show all");
  const list = screen.getByRole("navigation", { name: "Requirements by family" });
  expect(within(list).getByRole("button", { name: /System Auditing/ })).toBeVisible();
  expect(within(list).queryByRole("button", { name: /Authorized Access Control/ })).not.toBeInTheDocument();
});

test("the Remediate figure opens the gaps that need a POA&M", async () => {
  mockCmmcServer();
  renderOverview();
  const user = userEvent.setup();
  const rail = await screen.findByRole("navigation", { name: "Engagement steps" });
  await user.click(within(rail).getByRole("button", { name: "1 gap needs a POA&M" }));
  expect(await screen.findByRole("status")).toHaveTextContent("Showing: NOT MET without a POA&M");
  const list = screen.getByRole("navigation", { name: "Requirements by family" });
  expect(within(list).getByRole("button", { name: /Control CUI Flow/ })).toBeVisible();
});

test("the Overview never reads the close check or lists blockers; that happens only on Finalize", async () => {
  const calls = mockCmmcServer();
  renderOverview();
  const dashboard = (await screen.findByRole("navigation", { name: "Engagement steps" })).closest("main")!;
  await screen.findByRole("region", { name: "CMMC score and Conditional status" });
  expectNoBlockerText(dashboard);
  expect(calls.some((url) => url.includes("close-readiness") || url.includes("issue-checklist"))).toBe(false);
});

test("a new CMMC project shows no blocker text: not started, checks not yet evaluated, nothing red", async () => {
  const blank = cmmcScoreFixture(
    [{ record_id: "AC.L2-3.1.1", title: "Authorized Access Control", points: 5, state: "not_assessed" }],
    { complete: false, started: false, allDecided: false, blockers: ["320 requirement(s) are not yet Met or Not Met."] },
  );
  mockCmmcServer({ overview: newCmmcOverview, score: blank });
  renderOverview();
  const score = await screen.findByRole("region", { name: "CMMC score and Conditional status" });
  expect(score).toHaveTextContent("Not started");
  // The worst possible score is never printed on a blank project.
  expect(score).not.toHaveTextContent(/[−-]\d{2,3}/);
  expect(score).not.toHaveTextContent("Projected");
  const checks = within(score).getByRole("region", { name: "32 CFR 170.21 Conditional status checks" });
  expect(checks).toHaveTextContent("Not yet evaluated");
  expect(checks).toHaveTextContent("Evaluated once every requirement is decided");
  expect(checks.querySelector(".fail")).toBeNull();
  expect(checks.querySelector(".pass")).toBeNull();
  expect(within(checks).getAllByText("Not yet evaluated").length).toBeGreaterThanOrEqual(3);
  // The old bullet list of score blockers is gone.
  expect(score).not.toHaveTextContent("not yet Met or Not Met");
  const dashboard = score.closest("main")!;
  expectNoBlockerText(dashboard);
  expect(dashboard).toHaveTextContent("Nothing decided yet");
});

test("the score reads normally once started, and a check shows red only when every requirement is decided and it fails", async () => {
  mockCmmcServer({ score: cmmcScoreFixture([{ record_id: "AC.L2-3.1.3", title: "Control CUI Flow", points: 5, state: "not_met" }], { started: true, allDecided: true }) });
  renderOverview();
  const score = await screen.findByRole("region", { name: "CMMC score and Conditional status" });
  expect(score).toHaveTextContent("VERIFIED SPRS105of 110");
  const checks = within(score).getByRole("region", { name: "32 CFR 170.21 Conditional status checks" });
  expect(checks).toHaveTextContent("Not eligible");
  expect(checks.querySelector("li.fail")).not.toBeNull();
  expect(checks).not.toHaveTextContent("Not yet evaluated");
});

test("started but not fully decided: the verified score shows, undecided checks stay grey and only a check already failed by decided work is red", async () => {
  mockCmmcServer({ score: cmmcScoreFixture([{ record_id: "AC.L2-3.1.3", title: "Control CUI Flow", points: 5, state: "not_met" }], { complete: false, started: true, allDecided: false }) });
  renderOverview();
  const score = await screen.findByRole("region", { name: "CMMC score and Conditional status" });
  expect(score).toHaveTextContent("VERIFIED SPRS105of 110 · provisional");
  const checks = within(score).getByRole("region", { name: "32 CFR 170.21 Conditional status checks" });
  expect(checks.querySelectorAll("li.fail")).toHaveLength(1);
  expect(checks).toHaveTextContent("Fails: AC.L2-3.1.3 is decided Not Met and is worth 5 points");
  expect(checks.querySelectorAll("li.neutral")).toHaveLength(2);
  expect(checks).toHaveTextContent("Not yet evaluated");
});

test("with only evidence-pending Met or one-point gaps decided, every check stays grey", async () => {
  mockCmmcServer({ score: cmmcScoreFixture([{ record_id: "AC.L2-3.1.1", title: "Authorized Access Control", points: 5, state: "evidence_pending" }], { complete: false, started: true, allDecided: false }) });
  renderOverview();
  const score = await screen.findByRole("region", { name: "CMMC score and Conditional status" });
  const checks = within(score).getByRole("region", { name: "32 CFR 170.21 Conditional status checks" });
  expect(checks.querySelector("li.fail")).toBeNull();
  expect(checks).not.toHaveTextContent("Fails:");
  expect(within(checks).getAllByText("Not yet evaluated").length).toBeGreaterThanOrEqual(3);
});

test("next-work hints show on the score panel as plain progress text", async () => {
  mockCmmcServer({ score: cmmcScoreFixture([{ record_id: "AC.L2-3.1.1", title: "x", points: 5, state: "pending" }], { complete: false, started: true, allDecided: false, hints: ["Record partial or no implementation for IA.L2-3.5.3 / SC.L2-3.13.11.", "An up-to-date SSP is needed to complete the assessment."] }) });
  renderOverview();
  const score = await screen.findByRole("region", { name: "CMMC score and Conditional status" });
  expect(score).toHaveTextContent("Record partial or no implementation for IA.L2-3.5.3 / SC.L2-3.13.11.");
  expect(score).toHaveTextContent("An up-to-date SSP is needed to complete the assessment.");
  expect(score).not.toHaveTextContent(/blocker/i);
});

test("once everything is decided but the assessment is incomplete, the reason replaces a bare 'not complete'", async () => {
  mockCmmcServer({ score: cmmcScoreFixture([{ record_id: "CA.L2-3.12.4", title: "SSP", points: 0, state: "not_met" }], { complete: false, started: true, allDecided: true, hints: ["An up-to-date SSP is needed to complete the assessment."] }) });
  renderOverview();
  const score = await screen.findByRole("region", { name: "CMMC score and Conditional status" });
  const checks = within(score).getByRole("region", { name: "32 CFR 170.21 Conditional status checks" });
  expect(checks).toHaveTextContent("An up-to-date SSP is needed to complete the assessment.");
  expect(checks).not.toHaveTextContent("assessment not complete");
});

test("drafting and Finalize are reachable from Deliverables", async () => {
  mockCmmcServer();
  renderOverview();
  const user = userEvent.setup();
  await screen.findByRole("navigation", { name: "Engagement steps" });
  await user.click(screen.getByRole("button", { name: "Deliverables" }));
  expect(await screen.findByRole("button", { name: "Download draft" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Finalize…" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Deliverables" })).toHaveClass("active");
  expect(screen.queryByRole("navigation", { name: "Engagement steps" })).not.toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Reports" })).not.toBeInTheDocument();
});

function renderHipaaOverview(overview: unknown) {
  vi.mocked(fetch).mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith("/overview")) return Response.json(overview);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  return render(
    <OverviewView
      projectId="project-1" assessmentId="assessment-1" projectName="HIPAA 2026" clientName="Northwind Health"
      frameworkName="HIPAA 45 CFR Part 164" scored={false} refreshKey={0}
      onOpenStep={vi.fn()} onOpenGroup={vi.fn()} onOpenRecord={vi.fn()}
    />,
  );
}

test("HIPAA shows counts by status per rule and progress, no blockers, no score", async () => {
  renderHipaaOverview(hipaaOverview);
  const table = await screen.findByRole("region", { name: "Status by rule" });
  expect(within(table).getByRole("row", { name: /Security Rule 4 2 1 0 3/ })).toBeVisible();
  expect(within(table).getByRole("row", { name: /Privacy Rule/ })).toBeVisible();
  const rail = screen.getByRole("navigation", { name: "Engagement steps" });
  expect(rail).toHaveTextContent("0 of 149 decided");
  expect(rail).toHaveTextContent("Final v2 · 12 Oct 2026");
  expectNoBlockerText(rail.closest("main")!);
  expect(screen.queryByText(/SPRS/)).not.toBeInTheDocument();
  expect(screen.queryByText(/Projected/)).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "CMMC score and Conditional status" })).not.toBeInTheDocument();
  expect(screen.queryByRole("region", { name: "NOT MET requirements" })).not.toBeInTheDocument();
  expect(screen.queryByText(/%/)).not.toBeInTheDocument();
});

test("a new HIPAA project shows no blocker text and no 'Objectives' wording", async () => {
  renderHipaaOverview({ ...hipaaOverview, steps: hipaaOverview.steps.map((step) => (step.label === "Deliver" ? { ...step, figure: "Draft available", parts: [{ text: "Draft available", group: null }] } : step)) });
  const rail = await screen.findByRole("navigation", { name: "Engagement steps" });
  const page = rail.closest("main")!;
  expectNoBlockerText(page);
  expect(page).not.toHaveTextContent(/objectives/i);
  expect(rail).toHaveTextContent("Draft available");
});

test("Finalize is where blockers appear: its groups open the Profile, the SSP and Deliverables", async () => {
  mockCmmcServer({
    checklistGroups: [
      group("profile", "Profile not approved", 1, [], "profile"),
      group("ssp", "SSP not approved", 1, [], "ssp"),
      group("other", "Other items", 1, [], "overview"),
    ],
  });
  renderOverview();
  const user = userEvent.setup();
  async function openFinalize() {
    await user.click(screen.getByRole("button", { name: "Deliverables" }));
    await user.click(await screen.findByRole("button", { name: "Finalize…" }));
    return screen.findByRole("dialog", { name: "Finalize deliverables" });
  }
  await screen.findByRole("navigation", { name: "Engagement steps" });

  // SSP not approved opens the requirement view where the SSP is edited, never a dead end.
  let dialog = await openFinalize();
  await user.click(await within(dialog).findByRole("button", { name: "1 · SSP not approved" }));
  expect(screen.getByRole("button", { name: "Assessments" })).toHaveClass("active");
  expect(screen.queryByRole("status")).not.toBeInTheDocument();
  expect(await screen.findByRole("heading", { level: 1, name: "Authorized Access Control" })).toBeVisible();
  expect(await screen.findByText("System Security Plan")).toBeVisible();

  dialog = await openFinalize();
  await user.click(await within(dialog).findByRole("button", { name: "1 · Profile not approved" }));
  expect(screen.getByRole("button", { name: "Profile" })).toHaveClass("active");

  dialog = await openFinalize();
  await user.click(await within(dialog).findByRole("button", { name: "1 · Other items" }));
  expect(screen.getByRole("button", { name: "Deliverables" })).toHaveClass("active");
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

test("a progress-figure filter stays live: it is recomputed from the Overview as the work changes", async () => {
  // The first Overview read says 2; by the time the list opens, the server sees one already fixed.
  let reads = 0;
  mockCmmcServer();
  const base = vi.mocked(fetch).getMockImplementation()!;
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    if (String(input).endsWith("/overview")) {
      reads += 1;
      const fixed = group("met_no_evidence", "Met, evidence still needed", 1, ["AC.L2-3.1.1b"]);
      return Response.json(reads === 1 ? cmmcOverview : { ...cmmcOverview, evidence_progress: { text: "1 Met awaiting evidence", group: fixed } });
    }
    return base(input, init);
  });
  renderOverview();
  const user = userEvent.setup();
  const progress = await screen.findByLabelText("Evidence progress");
  await user.click(within(progress).getByRole("button", { name: "2 Met awaiting evidence" }));
  await waitFor(() => expect(screen.getByRole("status")).toHaveTextContent("Showing: Met, evidence still needed (1) · Show all"));
});

test("next-work figures after a reopen and for HIPAA are plain progress that open their lists", async () => {
  const steps = [
    { label: "Scope", figure: "Profile: 3 facts recorded", parts: [{ text: "Profile: 3 facts recorded", group: null }], target: "profile" },
    { label: "Assess", figure: "x", parts: [{ text: "10 of 149 decided", group: group("undecided", "Not decided yet", 139, []) }, { text: "2 N/A answers need a reason", group: group("na_reason", "N/A answers that need a reason", 2, ["a", "b"]) }, { text: "1 record to recheck", group: group("recheck", "Records to recheck", 1, ["c"]) }], target: "assessments" },
    { label: "Remediate", figure: "x", parts: [{ text: "3 Not Met need a corrective action", group: group("gaps_no_action", "Not Met without a corrective action", 3, ["d"]) }, { text: "0 corrective actions open", group: null }], target: "assessments" },
    { label: "Deliver", figure: "Final v2 · new version in progress", parts: [{ text: "Final v2 · new version in progress", group: null }], target: "reports" },
  ];
  renderHipaaOverview({ ...hipaaOverview, steps });
  const rail = await screen.findByRole("navigation", { name: "Engagement steps" });
  for (const text of ["2 N/A answers need a reason", "1 record to recheck", "3 Not Met need a corrective action", "Final v2 · new version in progress"]) {
    expect(within(rail).getByRole("button", { name: text })).toBeVisible();
  }
  expectNoBlockerText(rail.closest("main")!);
});
