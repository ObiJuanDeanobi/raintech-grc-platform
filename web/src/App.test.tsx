import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import App, { Workspace } from "./App";
import { activeRevisionFixture, clientAssessmentProjectsFixture, clientProjectsFixture, cmmcScoreFixture, delayedResponse as deferredResponse } from "./activeAssessmentFixtures";

const assessment = {
  id: "assessment-1",
  project: {
    id: "project-1",
    name: "HIPAA 2026",
    client_id: "client-1",
    client_name: "Northwind Health",
  },
  framework: {
    id: "hipaa-45cfr164-2026-07-01",
    name: "HIPAA 45 CFR Part 164",
    record_count: 194,
    walkthrough_record_count: 194,
    prompt_count: 1163,
    determination_record_count: 149,
    declarations: {
      record_shape: {
        hierarchy: ["standard", "implementation_specification", "paragraph"],
        determination_rule: "records_without_children",
      },
      rollup_rule: {
        precedence: ["Not Met", "Pending"],
        blank_children_prevent_met: true,
        satisfied_child_statuses: ["Met", "N/A"],
        satisfied_rollup_status: "Met",
        blank_status: "",
      },
      status_set: ["", "Met", "Not Met", "Pending", "N/A"],
      presentation_mode: "one_record_with_parent_context",
      close_readiness: { fieldwork_ready_for_generation: {} },
    },
  },
  progress: {
    resolved_determination_count: 37,
    determination_record_count: 149,
  },
  work_list: [
    {
      record_id: "child-1",
      citation: "45 CFR 164.308(a)(1)(ii)(A)",
      title: "Risk analysis",
      work_area: "security",
      record_type: "implementation_specification",
      parent_id: "parent-1",
      designation: "required",
      sort_order: 1,
    },
    {
      record_id: "child-2",
      citation: "45 CFR 164.308(a)(1)(ii)(B)",
      title: "Risk management",
      work_area: "security",
      record_type: "implementation_specification",
      parent_id: "parent-1",
      designation: "required",
      sort_order: 2,
    },
    {
      record_id: "parent-1",
      citation: "45 CFR 164.308(a)(1)(i)",
      title: "Security management process",
      work_area: "security",
      record_type: "standard",
      parent_id: null,
      designation: null,
      sort_order: 3,
      editable_determination: false,
    },
  ],
  record_index: [],
};

const detail = {
  record: {
    record_id: "child-1",
    citation: "45 CFR 164.308(a)(1)(ii)(A)",
    title: "Risk analysis",
    regulation_text: "Conduct an accurate and thorough assessment.",
    work_area: "security",
    record_type: "implementation_specification",
    parent_id: "parent-1",
    designation: "required",
    editable_determination: true,
  },
  determination: {
    status: "",
    derived: false,
    na_rationale: "",
    addressable_disposition: null,
    disposition_reason: "",
    interview_observation: "",
  },
  parent: {
    record_id: "parent-1",
    citation: "45 CFR 164.308(a)(1)(i)",
    title: "Security management process",
    regulation_text: "Implement policies and procedures.",
    editable_determination: false,
    prompts_collapsed_by_default: true,
    determination: { status: "Pending", derived: true },
  },
  parent_prompts: [
    {
      id: "parent-prompt",
      text: "How is the security management process governed?",
      source: "NIST SP 800-66r2",
      source_detail: "Governance",
      cfr_paragraph: "",
      group: "Governance",
      role: "assessment_check",
      role_reason: "bears on the mapped CFR determination",
      render_checkbox: true,
      answer: "",
      moved_from: null,
      placement: null,
    },
  ],
  context_prompts: [],
  children: [],
  prompts: [
    {
      id: "prompt-check",
      text: "Has all ePHI been identified?",
      source: "NIST SP 800-66r2",
      source_detail: "Identify all ePHI",
      cfr_paragraph: "",
      group: "Identify",
      role: "assessment_check",
      role_reason: "bears on the mapped CFR determination",
      render_checkbox: true,
      answer: "",
      moved_from: null,
      placement: null,
    },
    {
      id: "prompt-context",
      text: "Consider the broader operating context.",
      source: "NIST SP 800-66r2",
      source_detail: "Context",
      cfr_paragraph: "",
      group: "Context",
      role: "context",
      role_reason: "recommended practice beyond the CFR requirement",
      render_checkbox: false,
      answer: "",
      moved_from: null,
      placement: null,
    },
  ],
  no_prompt_explanation: null,
  note: "",
  evidence: [],
  position: {
    current: 2,
    total: 194,
    previous_record_id: "parent-1",
    next_record_id: null,
  },
};

const refreshedDeterminationDetail = {
  ...detail,
  determination: { ...detail.determination, status: "Not Met" },
  parent: {
    ...detail.parent,
    determination: { status: "Not Met", derived: true },
  },
};

const secondRecordDetail = {
  ...detail,
  record: {
    ...detail.record,
    record_id: "child-2",
    citation: "45 CFR 164.308(a)(1)(ii)(B)",
    title: "Risk management",
  },
  prompts: detail.prompts.map((prompt) => ({ ...prompt, id: `${prompt.id}-child-2` })),
};

const clients = clientProjectsFixture();

const readiness = {
  project_id: "project-1",
  state: "Intake complete",
  assessment_exists: true,
  supported_states: [
    "Intake started",
    "Intake complete",
    "Needs follow-up",
    "Profile complete",
  ],
  allowed_next_states: ["Needs follow-up", "Profile complete"],
  follow_up_work_required_states: ["Needs follow-up"],
  follow_up_work_required_when_unresolved_required_fields: true,
  assessment_entry_allowed: true,
  assessment_entry_blocking_reasons: [],
  profile_completion_blocking_reasons: ["Approve the Profile version."],
  current_details: {
    unresolved_required_fields: [],
    follow_up_work: "",
    reviewed_by: "",
    approval_evidence: "",
  },
};

function mockApi(
  implementation: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>,
) {
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    const url = String(input);
    const match = url.match(/^\/api\/projects\/([^/]+)\/profile-readiness$/);
    if (match) {
      return Response.json({ ...readiness, project_id: match[1] });
    }
    return implementation(input, init);
  });
}

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/clients") {
        return Response.json([
          {
            id: "client-1",
            name: "Northwind Health",
            projects: [
              {
                id: "project-1",
                name: "HIPAA 2026",
                framework_version_id: "hipaa-45cfr164-2026-07-01",
              },
            ],
          },
        ]);
      }
      if (url === "/api/projects/project-1/assessment") {
        return Response.json(assessment);
      }
      if (url === "/api/projects/project-1/profile-readiness") {
        return Response.json(readiness);
      }
      if (url.includes("/records/child-1")) {
        return Response.json(detail);
      }
      if (url.includes("/determinations/child-1") && init?.method === "PUT") {
        return Response.json({ ...detail.determination, status: "Pending" });
      }
      if (url === "/api/projects/project-1/evidence") {
        return Response.json([]);
      }
      return Response.json({ detail: "not found" }, { status: 404 });
    }),
  );
});

const issueChecklist = (overrides: Record<string, unknown> = {}) => ({
  ready: true,
  groups: [],
  warnings: [],
  current_issue: null,
  ...overrides,
});

test("Review and issue lists what must be fixed, and each group opens its filtered list", async () => {
  const calls: string[] = [];
  vi.mocked(fetch).mockImplementation(async (input) => {
    const url = String(input); calls.push(url);
    if (url.includes("profile-readiness")) return Response.json({ ...readiness, assessment_exists: true });
    if (url.endsWith("/assessment")) return Response.json(assessment);
    if (url.endsWith("/packages")) return Response.json([]);
    if (url.endsWith("/issue-checklist")) return Response.json(issueChecklist({
      ready: false,
      groups: [{ key: "undecided", label: "Objectives not decided", count: 2, record_ids: ["child-1"], target: "assessments" }],
      warnings: [{ key: "evidence_due_soon", label: "Evidence due for review soon", count: 1, detail: "Worth refreshing before the report goes out.", target: "evidence" }],
    }));
    if (url.includes("/records/child-1")) return Response.json(detail);
    if (url.includes("/evidence")) return Response.json([]);
    return Response.json({});
  });
  render(<Workspace clients={clients} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} initialView="reports" />);
  const user = userEvent.setup();
  await user.click(await screen.findByRole("button", { name: "Review and issue…" }));
  const dialog = await screen.findByRole("dialog", { name: "Review and issue" });
  expect(within(dialog).getByText("Must be fixed before issue")).toBeVisible();
  expect(within(dialog).getByText("Worth checking")).toBeVisible();
  expect(within(dialog).getByText(/Evidence due for review soon/)).toBeVisible();
  // Hard gates stop the issue; warnings never do.
  expect(within(dialog).getByRole("button", { name: "Issue" })).toBeDisabled();
  expect(calls.some((url) => url.endsWith("/issue-checklist"))).toBe(true);
  await user.click(within(dialog).getByRole("button", { name: "2 · Objectives not decided" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  // The group opens Assessments narrowed to its records.
  expect(screen.getByRole("button", { name: "Assessments" })).toHaveClass("active");
  expect(await screen.findByText(/Objectives not decided/)).toBeVisible();
});

test("Reports lists only issued versions, offers a draft, and no longer offers generation or review steps", async () => {
  vi.mocked(fetch).mockImplementation(async (input) => {
    const url = String(input);
    if (url.includes("profile-readiness")) return Response.json({ ...readiness, assessment_exists: true });
    if (url.endsWith("/assessment")) return Response.json(assessment);
    if (url.endsWith("/packages")) return Response.json([
      { id: "staged", assessment_id: "assessment-1", state: "staged", lifecycle: "Draft", created_at: "2026-01-01T00:00:00Z", components: [] },
      { id: "pkg-draft", assessment_id: "assessment-1", state: "promoted", lifecycle: "Draft", created_at: "2026-01-01T12:00:00Z", components: [{ id: "unissued", kind: "assessment_report", filename: "never-issued.docx" }] },
      { id: "pkg-1", assessment_id: "assessment-1", state: "promoted", lifecycle: "Issued", issuance_status: "Current", issued_at: "2026-01-02T00:00:00Z", reviewer: "Johnathan", review_note: "October report.", created_at: "2026-01-02T00:00:00Z", source_snapshot_id: "snap-1", manifest: { source_snapshot_sha256: "abc", components: [] }, components: [{ id: "report", kind: "assessment_report", filename: "report.docx" }, { id: "poam", kind: "poam", filename: "poam.xlsx" }] },
    ]);
    if (url.includes("/records/child-1")) return Response.json(detail);
    if (url.includes("/evidence")) return Response.json([]);
    return Response.json({});
  });
  render(<Workspace clients={clients} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} initialView="reports" />);
  expect(await screen.findByText("report.docx")).toBeVisible();
  expect(screen.getByText(/Issued version · /)).toBeVisible();
  expect(screen.getByText("Current")).toBeVisible();
  expect(screen.getByText(/Reviewed by Johnathan · October report\./)).toBeVisible();
  expect(screen.getByText("report.docx")).toBeVisible();
  expect(screen.getByText("poam.xlsx")).toBeVisible();
  expect(screen.queryByText("never-issued.docx")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Download draft" })).toBeEnabled();
  for (const gone of ["Generate package", "Start review", "Mark reviewed", "Sign off: Ready to issue", "Create and validate backup", "Issue final deliverables"]) {
    expect(screen.queryByRole("button", { name: gone })).not.toBeInTheDocument();
  }
});

test("issuing is one act: one request with the account and note, no backup or review steps", async () => {
  const calls: Array<{ url: string; method?: string; body?: Record<string, unknown> }> = [];
  let issued = false;
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    const url = String(input);
    if (init?.method === "POST") calls.push({ url, method: init.method, body: JSON.parse(String(init.body)) as Record<string, unknown> });
    if (url.includes("profile-readiness")) return Response.json({ ...readiness, assessment_exists: true });
    if (url.endsWith("/assessment")) return Response.json(assessment);
    if (url.endsWith("/issue-checklist")) return Response.json(issueChecklist());
    if (url.endsWith("/assessments/assessment-1/issue") && init?.method === "POST") {
      issued = true;
      return Response.json({ package_id: "pkg-new", issued_snapshot_id: "issued-123", issued_at: "2026-01-03T00:01:00Z", reviewer: "Johnathan", note: "Reviewed for October.", backup_id: "backup-123", superseded_package_id: null }, { status: 201 });
    }
    if (url.endsWith("/packages")) return Response.json(issued ? [{ id: "pkg-new", assessment_id: "assessment-1", state: "promoted", lifecycle: "Issued", issuance_status: "Current", issued_at: "2026-01-03T00:01:00Z", reviewer: "Johnathan", review_note: "Reviewed for October.", created_at: "2026-01-03T00:00:00Z", components: [{ id: "report-new", kind: "assessment_report", filename: "report.docx" }] }] : []);
    if (url.includes("/records/child-1")) return Response.json(detail);
    if (url.includes("/evidence")) return Response.json([]);
    return Response.json({});
  });
  render(<Workspace clients={clients} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} initialView="reports" />);
  const user = userEvent.setup();
  expect(await screen.findByText("Nothing has been issued yet.")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Review and issue…" }));
  const dialog = await screen.findByRole("dialog", { name: "Review and issue" });
  await user.type(within(dialog).getByLabelText(/Note/), "Reviewed for October.");
  await user.click(await within(dialog).findByRole("button", { name: "Issue" }));
  expect(await screen.findByText(/Issued\. Reviewed by Johnathan/)).toBeVisible();
  expect(await screen.findByText("report.docx")).toBeVisible();
  expect(calls).toEqual([
    { url: "/api/projects/project-1/assessments/assessment-1/issue", method: "POST", body: { actor_id: "johnathan", note: "Reviewed for October." } },
  ]);
});

test("a reissue with new wording is one act on the current issue and keeps the older version visible", async () => {
  const posts: Array<{ url: string; body: Record<string, unknown> }> = [];
  let reissued = false;
  const component = (id: string) => [{ id: `report-${id}`, kind: "assessment_report", filename: "report.docx" }];
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    const url = String(input);
    if (url.includes("profile-readiness")) return Response.json({ ...readiness, assessment_exists: true });
    if (url.endsWith("/assessment")) return Response.json(assessment);
    if (url.endsWith("/issue-now") && init?.method === "POST") {
      posts.push({ url, body: JSON.parse(String(init.body)) as Record<string, unknown> });
      reissued = true;
      return Response.json({ package_id: "pkg-new", issued_snapshot_id: "iss-2", issued_at: "2026-01-04T00:00:00Z", reviewer: "Johnathan", note: "Fix cover date format.", backup_id: "b-2", superseded_package_id: "pkg-old" }, { status: 201 });
    }
    if (url.endsWith("/packages")) return Response.json(reissued ? [
      { id: "pkg-new", assessment_id: "assessment-1", state: "promoted", lifecycle: "Issued", issuance_status: "Current", issued_at: "2026-01-04T00:00:00Z", reviewer: "Johnathan", created_at: "2026-01-04T00:00:00Z", components: component("new"), correction: { id: "corr-1", classification: "presentation_only", reason: "Reissued by Johnathan: Fix cover date format.", actor_id: "johnathan", prior_package_id: "pkg-old", prior_issuance_id: "iss-1", result_package_id: "pkg-new", created_at: "2026-01-04T00:00:00Z" } },
      { id: "pkg-old", assessment_id: "assessment-1", state: "promoted", lifecycle: "Superseded", issuance_status: "Superseded", issued_at: "2026-01-02T00:00:00Z", created_at: "2026-01-02T00:00:00Z", components: component("old"), superseded_by_package_id: "pkg-new" },
    ] : [
      { id: "pkg-old", assessment_id: "assessment-1", state: "promoted", lifecycle: "Issued", issuance_status: "Current", issued_at: "2026-01-02T00:00:00Z", reviewer: "Johnathan", created_at: "2026-01-02T00:00:00Z", components: component("old") },
    ]);
    if (url.includes("/records/child-1")) return Response.json(detail);
    if (url.includes("/evidence")) return Response.json([]);
    return Response.json({});
  });
  render(<Workspace clients={clients} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} initialView="reports" />);
  const user = userEvent.setup();
  await user.click(await screen.findByRole("button", { name: "Reissue with new wording or layout…" }));
  // No attestation checkboxes: reissuing is only ever offered on the same findings.
  expect(screen.queryByLabelText(/changes presentation only|are unchanged/)).not.toBeInTheDocument();
  await user.type(screen.getByLabelText(/Note/), "Fix cover date format.");
  await user.click(screen.getByRole("button", { name: "Issue" }));
  expect(await screen.findByText(/It replaces the earlier issued version/)).toBeVisible();
  expect(screen.getAllByText("Replaced")).toHaveLength(1);
  expect(screen.getByText(/Replaced by a later issued version/)).toBeVisible();
  expect(posts).toEqual([{ url: "/api/projects/project-1/packages/pkg-old/issue-now", body: { actor_id: "johnathan", note: "Fix cover date format." } }]);
});

test("substantive reopening requires selected records and revalidation before the next issue", async () => {
  const posts: Array<{ url: string; body: Record<string, unknown> }> = [];
  let reopened = false;
  let revalidated = false;
  const index = [{ ...assessment.work_list[0], editable_determination: true }];
  const successor = { ...assessment, id: "assessment-2", record_index: index, reopening: { id: "open-1", classification: "substantive", rationale: "Evidence was superseded.", affected_record_ids_json: '["child-1"]', predecessor_assessment_id: "assessment-1", successor_assessment_id: "assessment-2", prior_package_id: "pkg-old", prior_issuance_id: "iss-1", actor_id: "johnathan", created_at: "2026-01-04T00:00:00Z" }, revalidation_items: [{ id: "item-1", record_id: "child-1", revalidated_by: null, revalidated_at: null, note: "" }] };
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    const url = String(input);
    if (url.includes("profile-readiness")) return Response.json({ ...readiness, assessment_exists: true });
    if (url.endsWith("/assessment")) return Response.json(reopened ? successor : { ...assessment, record_index: index });
    if (url.endsWith("/reopen") && init?.method === "POST") {
      posts.push({ url, body: JSON.parse(String(init.body)) as Record<string, unknown> });
      reopened = true;
      return Response.json({ successor_assessment_id: "assessment-2" }, { status: 201 });
    }
    if (url.endsWith("/revalidate") && init?.method === "POST") {
      posts.push({ url, body: JSON.parse(String(init.body)) as Record<string, unknown> });
      revalidated = true;
      return Response.json({ id: "item-1" }, { status: 201 });
    }
    if (url.endsWith("/issue-checklist")) return Response.json(reopened && !revalidated
      ? issueChecklist({ ready: false, groups: [{ key: "recheck", label: "Records to recheck", count: 1, record_ids: ["child-1"], target: "assessments" }] })
      : issueChecklist());
    if (url.endsWith("/packages")) return Response.json([{ id: "pkg-old", assessment_id: "assessment-1", state: "promoted", lifecycle: "Issued", created_at: "2026-01-02T00:00:00Z", source_snapshot_id: "snap-1", components: [{ id: "report-old", kind: "assessment_report", filename: "report.docx" }], issuance_status: "Current", issued_snapshot_id: "iss-1" }]);
    if (url.includes("/records/child-1")) return Response.json(detail);
    if (url.includes("/evidence")) return Response.json([]);
    return Response.json({});
  });
  render(<Workspace clients={clients} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} initialView="reports" />);
  const user = userEvent.setup();
  await user.click(await screen.findByRole("button", { name: "Reopen for substantive correction…" }));
  const submit = screen.getByRole("button", { name: "Reopen assessment" });
  expect(submit).toBeDisabled();
  await user.click(screen.getByLabelText("This correction changes assessment content"));
  await user.click(screen.getByLabelText(/Risk analysis/));
  await user.type(screen.getByLabelText("Reason for reopening"), "Evidence was superseded.");
  expect(submit).toBeEnabled();
  await user.click(submit);
  expect(await screen.findByText("Needs Revalidation")).toBeVisible();
  expect(screen.getByText("1 of 1 remaining")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Reports" }));
  await user.click(await screen.findByRole("button", { name: "Review and issue…" }));
  const dialog = await screen.findByRole("dialog", { name: "Review and issue" });
  expect(await within(dialog).findByText("1 · Records to recheck")).toBeVisible();
  expect(within(dialog).getByRole("button", { name: "Issue" })).toBeDisabled();
  await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
  await user.click(screen.getByRole("button", { name: "Assessments" }));
  await user.type(screen.getByLabelText("Revalidation note"), "Re-examined.");
  await user.click(screen.getByRole("button", { name: "Mark revalidated" }));
  expect(await screen.findByText("All revalidated")).toBeVisible();
  expect(posts).toEqual([
    { url: "/api/projects/project-1/packages/pkg-old/reopen", body: { actor_id: "johnathan", classification: "substantive", affected_record_ids: ["child-1"], rationale: "Evidence was superseded." } },
    { url: "/api/projects/project-1/assessments/assessment-2/records/child-1/revalidate", body: { actor_id: "johnathan", note: "Re-examined." } },
  ]);
});

test("Not Met reconciliation uses project-scoped PUT and create payload", async () => {
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    const url = String(input); calls.push({ url, init });
    if (url.includes("profile-readiness")) return Response.json({ ...readiness, assessment_exists: true });
    if (url.endsWith("/assessment")) return Response.json(assessment);
    if (url.includes("/records/child-1/reconciliation")) return Response.json({ outcome: "unresolved", prefill: { citation: "45 CFR 164.308", finding_title: "Prefilled finding", action_title: "Prefilled action" }, links: [], history: [] });
    if (url.includes("/records/child-1")) return Response.json(refreshedDeterminationDetail);
    if (url.includes("/evidence")) return Response.json([]);
    return Response.json({});
  });
  render(<Workspace clients={clients} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} />);
  expect(await screen.findByText("Prefilled context")).toBeVisible();
  expect(screen.getByDisplayValue("Prefilled finding")).toBeVisible();
  await userEvent.setup().click(screen.getByRole("button", { name: "Save reconciliation" }));
  await waitFor(() => expect(calls.some((call) => call.url === "/api/projects/project-1/assessments/assessment-1/records/child-1/reconciliation" && call.init?.method === "PUT")).toBe(true));
  const call = calls.find((item) => item.url.includes("reconciliation") && item.init?.method === "PUT")!;
  expect(JSON.parse(String(call.init?.body))).toMatchObject({ outcome: "create", title: "Prefilled finding" });
});

test("Pending reconciliation explains that no work is created", async () => {
  vi.mocked(fetch).mockImplementation(async (input) => {
    const url = String(input);
    if (url.includes("profile-readiness")) return Response.json({ ...readiness, assessment_exists: true });
    if (url.endsWith("/assessment")) return Response.json(assessment);
    if (url.includes("/records/child-1")) return Response.json({ ...detail, determination: { ...detail.determination, status: "Pending" } });
    return Response.json([]);
  });
  render(<Workspace clients={clients} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} />);
  expect(await screen.findByText(/Pending does not create reconciliation work/i)).toBeVisible();
  expect(vi.mocked(fetch).mock.calls.some(([url]) => String(url).includes("reconciliation"))).toBe(false);
});

test("Issue 68 validation marks the action ready and records binary validation with notes", async () => {
  const calls: Array<{ url: string; init?: RequestInit }> = [];
  let actionStatus = "In Progress";
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    const url = String(input); calls.push({ url, init });
    if (url.includes("profile-readiness")) return Response.json({ ...readiness, assessment_exists: true });
    if (url.endsWith("/assessment")) return Response.json(assessment);
    if (url.includes("/records/child-1/reconciliation")) return Response.json({
      outcome: "create", finding_id: "finding-1", corrective_action_id: "action-1", links: [
        { id: "finding-1", type: "finding", title: "Risk finding", status: "Open" },
        { id: "action-1", type: "corrective_action", title: "Remediate risk", status: actionStatus },
      ], history: [],
    });
    if (url.includes("/corrective-actions/action-1/validation") && init?.method === "POST") { actionStatus = "In Progress"; return Response.json({ id: "event-1" }); }
    if (url.includes("/corrective-actions/action-1/validation")) return Response.json({
      finding: { id: "finding-1", title: "Risk finding", description: "Gap", status: "Open" },
      corrective_action: { id: "action-1", title: "Remediate risk", description: "Fix it", status: actionStatus, validation_state: actionStatus === "Ready for Validation" ? "Ready" : "Failed" },
      determination: { status: "Not Met", interview_observation: "Observed" }, events: [],
    });
    if (url.endsWith("/corrective-actions/action-1") && init?.method === "PUT") { actionStatus = "Ready for Validation"; return Response.json({ id: "action-1", status: actionStatus }); }
    if (url.includes("/records/child-1")) return Response.json(refreshedDeterminationDetail);
    if (url.includes("/evidence")) return Response.json([]);
    return Response.json({});
  });
  render(<Workspace clients={clients} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} />);
  expect(await screen.findByText("Risk finding")).toBeVisible();
  await userEvent.setup().click(screen.getByRole("button", { name: "Mark Ready for Validation" }));
  await waitFor(() => expect(calls.some((call) => call.url.endsWith("/corrective-actions/action-1") && call.init?.method === "PUT")).toBe(true));
  const stateCall = calls.find((call) => call.url.endsWith("/corrective-actions/action-1") && call.init?.method === "PUT")!;
  expect(JSON.parse(String(stateCall.init?.body))).toEqual({ actor_id: "johnathan", state: "Ready for Validation" });
  expect(screen.getByRole("option", { name: "Validated" })).toBeVisible();
  expect(screen.getByRole("option", { name: "Failed" })).toBeVisible();
  const submit = screen.getByRole("button", { name: "Record validation" });
  const notes = screen.getByLabelText(/Validation notes/);
  expect(notes).toBeRequired();
  await userEvent.setup().type(notes, "Control evidence reviewed.");
  await userEvent.setup().selectOptions(screen.getByLabelText("Outcome"), "Failed");
  await userEvent.setup().click(submit);
  await waitFor(() => expect(calls.some((call) => call.url.includes("/corrective-actions/action-1/validation") && call.init?.method === "POST")).toBe(true));
  const validationCall = calls.find((call) => call.url.includes("/corrective-actions/action-1/validation") && call.init?.method === "POST")!;
  expect(JSON.parse(String(validationCall.init?.body))).toEqual({ actor_id: "johnathan", outcome: "Failed", notes: "Control evidence reviewed." });
  await waitFor(() => expect(screen.getByText("In Progress")).toBeVisible());
  expect(screen.getByText("Remediate risk · In Progress")).toBeVisible();
});

test("shows readiness state and concrete assessment blocking before an assessment exists", async () => {
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/projects/project-1/profile-readiness") {
      return Response.json({
        ...readiness,
        state: "Needs follow-up",
        assessment_exists: false,
        assessment_entry_allowed: false,
        assessment_entry_blocking_reasons: [
          "Resolve the recorded follow-up before starting a new assessment.",
        ],
      });
    }
    if (url === "/api/projects/project-1/assessment") {
      return Response.json({ detail: "Assessment not found" }, { status: 404 });
    }
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  render(
    <Workspace
      clients={clients}
      projectId="project-1"
      onProjectChange={vi.fn()}
      onWorkspaceCreated={vi.fn()}
    />,
  );

  expect(await screen.findByRole("heading", { name: "Ready to begin" })).toBeVisible();
  expect(
    screen.getByText("Resolve the recorded follow-up before starting a new assessment."),
  ).toBeVisible();
  expect(screen.getByRole("button", { name: "Start assessment" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Profile" })).toBeEnabled();
  expect(screen.queryByRole("heading", { name: "Operating boundary" })).toBeNull();
  expect(fetch).not.toHaveBeenCalledWith(
    "/api/projects/project-1/assessment",
    expect.anything(),
  );
});

test("keeps an existing assessment readable while a readiness regression blocks new entry", async () => {
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/clients") {
      return Response.json([{ ...clients[0], projects: [clients[0].projects[0]] }]);
    }
    if (url === "/api/projects/project-1/profile-readiness") {
      return Response.json({
        ...readiness,
        state: "Needs follow-up",
        assessment_entry_allowed: false,
        assessment_entry_blocking_reasons: [
          "Resolve the recorded follow-up before starting a new assessment.",
        ],
      });
    }
    if (url === "/api/projects/project-1/assessment") return Response.json(assessment);
    if (url.includes("/records/child-1")) return Response.json(detail);
    if (url === "/api/projects/project-1/evidence") return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });

  render(<App />);
  expect(await screen.findByRole("heading", { level: 1, name: "Risk analysis" })).toBeVisible();
  expect(screen.getByText("Needs follow-up")).toBeVisible();
  expect(
    screen.getByText("Resolve the recorded follow-up before starting a new assessment."),
  ).toBeVisible();
});

test("requires explicit work before submitting Needs follow-up", async () => {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { level: 1, name: "Risk analysis" });
  await user.click(screen.getByRole("button", { name: "Profile" }));
  await user.selectOptions(screen.getByLabelText("Next state"), "Needs follow-up");
  await user.type(screen.getByLabelText("Decision note"), "Follow-up is required.");

  expect(screen.getByLabelText("Explicit follow-up work")).toBeRequired();
  await user.click(screen.getByRole("button", { name: "Record transition" }));
  expect(
    vi.mocked(fetch).mock.calls.some(
      ([input, init]) =>
        String(input).endsWith("/profile-readiness/transitions") && init?.method === "POST",
    ),
  ).toBe(false);
});

test("a late Project A action reload cannot clear the loaded Project B assessment", async () => {
  const projectAReload = deferredResponse();
  const projectBAssessment = {
    ...assessment,
    id: "assessment-2",
    project: { ...assessment.project, id: "project-2", name: "HIPAA B" },
  };
  const projectBReadiness = {
    ...readiness,
    project_id: "project-2",
    state: "Profile complete",
    allowed_next_states: ["Needs follow-up"],
  };
  let projectAReadinessReads = 0;
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/projects/project-1/profile-readiness") {
      projectAReadinessReads += 1;
      if (projectAReadinessReads === 2) return projectAReload.promise;
      return Response.json(readiness);
    }
    if (
      url === "/api/projects/project-1/profile-readiness/transitions"
      && init?.method === "POST"
    ) {
      return Response.json(readiness, { status: 201 });
    }
    if (url === "/api/projects/project-2/profile-readiness") {
      return Response.json(projectBReadiness);
    }
    if (url === "/api/projects/project-1/assessment") return Response.json(assessment);
    if (url === "/api/projects/project-2/assessment") {
      return Response.json(projectBAssessment);
    }
    if (url.includes("/records/child-1")) return Response.json(detail);
    if (url.endsWith("/evidence")) return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const user = userEvent.setup();
  const { rerender } = render(
    <Workspace
      clients={clients}
      projectId="project-1"
      onProjectChange={vi.fn()}
      onWorkspaceCreated={vi.fn()}
    />,
  );
  await screen.findByRole("heading", { level: 1, name: "Risk analysis" });
  await user.click(screen.getByRole("button", { name: "Profile" }));
  await user.selectOptions(screen.getByLabelText("Next state"), "Needs follow-up");
  await user.type(screen.getByLabelText("Decision note"), "Project A needs follow-up.");
  await user.type(screen.getByLabelText("Explicit follow-up work"), "Resolve Project A.");
  await user.click(screen.getByRole("button", { name: "Record transition" }));
  await waitFor(() => expect(projectAReadinessReads).toBe(2));

  rerender(
    <Workspace
      clients={clients}
      projectId="project-2"
      onProjectChange={vi.fn()}
      onWorkspaceCreated={vi.fn()}
    />,
  );
  expect(await screen.findByRole("heading", { level: 1, name: "Risk analysis" })).toBeVisible();
  expect(screen.getByText("Northwind Health · HIPAA B")).toBeVisible();
  expect(screen.getAllByText("Profile complete")).not.toHaveLength(0);

  projectAReload.resolve(Response.json({
    ...readiness,
    state: "Needs follow-up",
    assessment_entry_allowed: false,
  }));
  await act(async () => {
    await projectAReload.promise;
  });

  expect(screen.getByRole("heading", { level: 1, name: "Risk analysis" })).toBeVisible();
  expect(screen.getByText("Northwind Health · HIPAA B")).toBeVisible();
  expect(screen.getAllByText("Profile complete")).not.toHaveLength(0);
  expect(screen.queryByText("Project A needs follow-up.")).not.toBeInTheDocument();
});

test("project switching confirms before discarding unsaved Profile edits", async () => {
  const profile = {
    project_id: "project-1",
    active_version_id: null,
    template: { available: false, name: null, message: "Neutral form." },
    versions: [{
      id: "profile-v1",
      project_id: "project-1",
      version_number: 1,
      status: "Draft",
      created_by: "johnathan",
      created_at: "2026-08-26T00:00:00Z",
      content_revision: "revision-1",
      values: [{
        section: "project_metadata",
        field_key: "name",
        target_key: "field:project_metadata:name",
        label: "Name",
        value: "Project A Profile",
        source: "Synthetic",
        reviewer: "Johnathan",
        last_reviewed_at: "2026-08-26T00:00:00Z",
      }],
      items: [],
      lifecycle: [{
        id: "draft",
        status: "Draft",
        actor: { id: "johnathan", display_name: "Johnathan" },
        reviewer: "",
        timestamp: "2026-08-26T00:00:00Z",
      }],
      evidence: [],
    }],
  };
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/projects/project-1/profile-readiness") {
      return Response.json(readiness);
    }
    if (url === "/api/projects/project-1/assessment") return Response.json(assessment);
    if (url.includes("/records/child-1")) return Response.json(detail);
    if (url === "/api/projects/project-1/profile") return Response.json(profile);
    if (url === "/api/projects/project-1/evidence") return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  const onProjectChange = vi.fn();
  const user = userEvent.setup();
  render(
    <Workspace
      clients={clients}
      projectId="project-1"
      onProjectChange={onProjectChange}
      onWorkspaceCreated={vi.fn()}
    />,
  );
  await screen.findByRole("heading", { name: "Risk analysis" });
  await user.click(screen.getByRole("button", { name: "Profile" }));
  const name = await screen.findByDisplayValue("Project A Profile");
  await user.clear(name);
  await user.type(name, "Unsaved Project A");
  const projectSelect = screen.getAllByRole("combobox").find(
    (element) => (element as HTMLSelectElement).value === "project-1",
  );
  expect(projectSelect).toBeDefined();
  await user.selectOptions(projectSelect!, "project-2");
  expect(confirm).toHaveBeenCalled();
  expect(onProjectChange).not.toHaveBeenCalled();
  expect(screen.getByDisplayValue("Unsaved Project A")).toBeVisible();
});

test("renders a complete walkthrough with separate data-driven progress", async () => {
  const user = userEvent.setup();
  render(<App />);

  expect(await screen.findByRole("heading", { level: 1, name: "Risk analysis" })).toBeInTheDocument();
  expect(screen.getByText("2 of 194")).toBeInTheDocument();
  expect(screen.getByText("37 of 149 resolved")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Security management process/ })).toBeVisible();
  expect(screen.getByText("Derived · Pending")).toBeInTheDocument();
  expect(screen.getByRole("checkbox", { name: "Has all ePHI been identified?" })).toBeVisible();
  expect(
    screen.queryByRole("checkbox", { name: "Consider the broader operating context." }),
  ).not.toBeInTheDocument();
  await user.click(screen.getByText("Standard-level questions"));
  expect(screen.getByText("How is the security management process governed?")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Overview" }));
  expect(screen.getByRole("heading", { name: "Northwind Health · HIPAA 2026" })).toBeVisible();
});

test("contains no prompt placement controls or placement mutation requests", async () => {
  render(<App />);
  expect(await screen.findByRole("heading", { level: 1, name: "Risk analysis" })).toBeVisible();
  expect(screen.queryByRole("button", { name: /Move question/ })).not.toBeInTheDocument();
  expect(screen.queryByText("Move to")).not.toBeInTheDocument();
  expect(screen.queryByText("Save move")).not.toBeInTheDocument();
  expect(
    vi.mocked(fetch).mock.calls.some(([input]) => String(input).includes("/placement")),
  ).toBe(false);
});

test("renders the exact API-provided no-prompt explanation", async () => {
  const explanation =
    "versioned framework explanation supplied by the pinned prompt layer";
  mockApi(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/clients") {
      return Response.json([
        {
          id: "client-1",
          name: "Northwind Health",
          projects: [
            {
              id: "project-1",
              name: "HIPAA 2026",
              framework_version_id: "framework-version",
            },
          ],
        },
      ]);
    }
    if (url === "/api/projects/project-1/assessment") {
      return Response.json({ ...assessment, work_list: [assessment.work_list[2]] });
    }
    if (url.includes("/records/parent-1")) {
      return Response.json({
        ...detail,
        record: { ...detail.parent, work_area: "security", record_type: "standard" },
        determination: detail.parent.determination,
        parent: null,
        parent_prompts: [],
        prompts: [],
        no_prompt_explanation: explanation,
        position: {
          current: 1,
          total: 194,
          previous_record_id: null,
          next_record_id: "child-1",
        },
      });
    }
    if (url === "/api/projects/project-1/evidence") return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });

  render(<App />);
  expect(await screen.findByText(explanation)).toBeVisible();
  expect(screen.queryByText("Assess the cited requirement directly.")).not.toBeInTheDocument();
});

test("switching projects never displays another project's prompt answer", async () => {
  const projectBDetail = {
    ...detail,
    prompts: detail.prompts.map((prompt) => ({
      ...prompt,
      answer: prompt.id === "prompt-check" ? "Project B answer" : "",
    })),
  };
  mockApi(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/clients") {
      return Response.json([
        {
          id: "client-1",
          name: "Northwind Health",
          projects: [
            {
              id: "project-1",
              name: "HIPAA A",
              framework_version_id: "framework-version",
            },
            {
              id: "project-2",
              name: "HIPAA B",
              framework_version_id: "framework-version",
            },
          ],
        },
      ]);
    }
    if (url === "/api/projects/project-1/assessment") {
      return Response.json({
        ...assessment,
        id: "assessment-1",
        project: { ...assessment.project, id: "project-1", name: "HIPAA A" },
      });
    }
    if (url === "/api/projects/project-2/assessment") {
      return Response.json({
        ...assessment,
        id: "assessment-2",
        project: { ...assessment.project, id: "project-2", name: "HIPAA B" },
      });
    }
    if (url.includes("/projects/project-1/") && url.includes("/records/child-1")) {
      return Response.json({
        ...detail,
        prompts: detail.prompts.map((prompt) => ({
          ...prompt,
          answer: prompt.id === "prompt-check" ? "Project A answer" : "",
        })),
      });
    }
    if (url.includes("/projects/project-2/") && url.includes("/records/child-1")) {
      return Response.json(projectBDetail);
    }
    if (url.endsWith("/evidence")) return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const user = userEvent.setup();
  render(<App />);

  expect(
    await screen.findByRole("textbox", { name: "Answer: Has all ePHI been identified?" }),
  ).toHaveValue("Project A answer");
  const answeredIndicator = screen.getByRole("checkbox", { name: "Has all ePHI been identified?" });
  expect(answeredIndicator).toBeChecked();
  expect(answeredIndicator).toBeDisabled();
  await user.selectOptions(screen.getAllByRole("combobox")[0], "project-2");
  await waitFor(() =>
    expect(
      screen.getByRole("textbox", { name: "Answer: Has all ePHI been identified?" }),
    ).toHaveValue("Project B answer"),
  );
  expect(screen.queryByDisplayValue("Project A answer")).not.toBeInTheDocument();
});

test("a cross-client project switch clears the prior client's assessment while the new revision loads", async () => {
  const crossClientFixtures = clientAssessmentProjectsFixture(assessment, { crossClient: true });
  mockApi(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/clients") return Response.json(crossClientFixtures.clients);
    if (url.endsWith("/project-1/assessment")) return Response.json(crossClientFixtures.projects["project-1"]!.activeAssessment);
    if (url.endsWith("/project-2/assessment")) return Response.json(crossClientFixtures.projects["project-2"]!.activeAssessment);
    if (url.includes("/project-1/") && url.includes("records/child-1")) return Response.json({
      ...detail,
      prompts: detail.prompts.map((prompt) => ({ ...prompt, answer: prompt.id === "prompt-check" ? "Prior client answer" : "" })),
    });
    if (url.includes("/project-2/") && url.includes("records/child-1")) return Response.json({
      ...detail,
      prompts: detail.prompts.map((prompt) => ({ ...prompt, answer: prompt.id === "prompt-check" ? "New client answer" : "" })),
    });
    if (url.endsWith("/evidence")) return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const { rerender } = render(
    <Workspace clients={crossClientFixtures.clients} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} />,
  );
  expect(await screen.findByDisplayValue("Prior client answer")).toBeVisible();
  rerender(
    <Workspace clients={crossClientFixtures.clients} projectId="project-2" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} />,
  );
  expect(screen.queryByDisplayValue("Prior client answer")).not.toBeInTheDocument();
  expect(await screen.findByDisplayValue("New client answer")).toBeVisible();
  expect(screen.queryByText("Northwind Health · HIPAA 2026")).not.toBeInTheDocument();
});

test("switching between projects without assessments hides the prior readiness immediately", async () => {
  let releaseNext!: (value: Response) => void;
  const nextReadiness = new Promise<Response>((resolve) => { releaseNext = resolve; });
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/projects/project-1/profile-readiness") {
      return Response.json({ ...readiness, state: "Needs follow-up", assessment_exists: false,
        assessment_entry_allowed: false, assessment_entry_blocking_reasons: ["Project A intake is incomplete."], });
    }
    if (url === "/api/projects/project-2/profile-readiness") return nextReadiness;
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const { rerender } = render(<Workspace clients={clients} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} />);
  expect(await screen.findByText("Project A intake is incomplete.")).toBeVisible();
  rerender(<Workspace clients={clients} projectId="project-2" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} />);
  expect(screen.queryByText("Project A intake is incomplete.")).not.toBeInTheDocument();
  expect(screen.getByText("Opening assessment workspace…")).toBeVisible();
  releaseNext(Response.json({ ...readiness, project_id: "project-2", state: "Needs follow-up",
    assessment_exists: false, assessment_entry_allowed: false,
    assessment_entry_blocking_reasons: ["Project B needs follow-up."], }));
  expect(await screen.findByText("Project B needs follow-up.")).toBeVisible();
});

test("an active revision change reloads record detail before showing it", async () => {
  const revisions = activeRevisionFixture(assessment, {
    projectId: "project-1", projectName: "HIPAA 2026", clientId: "client-1", clientName: "Northwind Health",
  }, ["assessment-1", "assessment-2"]);
  expect(revisions.activeAssessment.id).toBe("assessment-2");
  let assessmentReads = 0;
  mockApi(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/clients") return Response.json([{ ...clients[0], projects: [clients[0].projects[0]] }]);
    if (url === "/api/projects/project-1/assessment") {
      assessmentReads += 1;
      return Response.json(revisions.revisions[assessmentReads - 1]);
    }
    if (url.includes("/assessments/assessment-1/records/child-1")) return Response.json({
      ...detail,
      prompts: detail.prompts.map((prompt) => ({ ...prompt, answer: prompt.id === "prompt-check" ? "Old revision answer" : "" })),
    });
    if (url.includes("/assessments/assessment-2/records/child-1")) return Response.json({
      ...detail,
      prompts: detail.prompts.map((prompt) => ({ ...prompt, answer: prompt.id === "prompt-check" ? "Active revision answer" : "" })),
    });
    if (url.includes("/determinations/child-1") && init?.method === "PUT") return Response.json(refreshedDeterminationDetail.determination);
    if (url.endsWith("/evidence")) return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const user = userEvent.setup();
  render(<App />);
  expect(await screen.findByDisplayValue("Old revision answer")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Pending" }));
  expect(await screen.findByDisplayValue("Active revision answer")).toBeVisible();
  expect(screen.queryByDisplayValue("Old revision answer")).not.toBeInTheDocument();
  expect(assessmentReads).toBe(2);
});

test("a late assessment response cannot overwrite the selected project", async () => {
  const projectA = deferredResponse();
  const projectBAssessment = {
    ...assessment,
    id: "assessment-2",
    project: { ...assessment.project, id: "project-2", name: "HIPAA B" },
  };
  const projectBDetail = {
    ...detail,
    prompts: detail.prompts.map((prompt) => ({
      ...prompt,
      answer: prompt.id === "prompt-check" ? "Project B answer" : "",
    })),
  };
  mockApi(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/projects/project-1/assessment") return projectA.promise;
    if (url === "/api/projects/project-2/assessment") {
      return Response.json(projectBAssessment);
    }
    if (url.includes("/projects/project-2/") && url.includes("/records/child-1")) {
      return Response.json(projectBDetail);
    }
    if (url === "/api/projects/project-2/evidence") return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const { rerender } = render(
    <Workspace
      clients={clients}
      projectId="project-1"
      onProjectChange={vi.fn()}
      onWorkspaceCreated={vi.fn()}
    />,
  );

  rerender(
    <Workspace
      clients={clients}
      projectId="project-2"
      onProjectChange={vi.fn()}
      onWorkspaceCreated={vi.fn()}
    />,
  );
  expect(await screen.findByRole("heading", { level: 1, name: "Risk analysis" })).toBeVisible();
  expect(
    screen.getByRole("textbox", { name: "Answer: Has all ePHI been identified?" }),
  ).toHaveValue("Project B answer");

  projectA.resolve(Response.json({
    ...assessment,
    id: "assessment-1",
    project: { ...assessment.project, id: "project-1", name: "HIPAA A" },
  }));
  await act(async () => {
    await projectA.promise;
  });

  expect(screen.getByText("Northwind Health · HIPAA B")).toBeVisible();
  expect(
    screen.getByRole("textbox", { name: "Answer: Has all ePHI been identified?" }),
  ).toHaveValue("Project B answer");
  expect(screen.queryByDisplayValue("Project A answer")).not.toBeInTheDocument();
  expect(
    vi.mocked(fetch).mock.calls.some(([input]) =>
      String(input).includes("/projects/project-1/assessments/assessment-1/records/"),
    ),
  ).toBe(false);
});

test("a late evidence response cannot replace the selected project's artifacts", async () => {
  const projectAEvidence = deferredResponse();
  const artifact = (id: string, name: string) => ({
    id,
    name,
    relative_path: `${id}/${name}`,
    shared_record_count: 0,
    version_id: `${id}-v1`,
    version_number: 1,
    sha256: id.repeat(8),
    version_relative_path: `${id}/v1/${name}`,
    version_created_at: "2026-08-26T00:00:00+00:00",
  });
  mockApi(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/projects/project-1/assessment") return Response.json(assessment);
    if (url === "/api/projects/project-2/assessment") {
      return Response.json({
        ...assessment,
        id: "assessment-2",
        project: { ...assessment.project, id: "project-2", name: "HIPAA B" },
      });
    }
    if (url.includes("/projects/project-1/") && url.includes("/records/child-1")) {
      return Response.json(detail);
    }
    if (url.includes("/projects/project-2/") && url.includes("/records/child-1")) {
      return Response.json(detail);
    }
    if (url === "/api/projects/project-1/evidence") return projectAEvidence.promise;
    if (url === "/api/projects/project-2/evidence") {
      return Response.json([artifact("b", "Project B evidence")]);
    }
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const { rerender } = render(
    <Workspace
      clients={clients}
      projectId="project-1"
      onProjectChange={vi.fn()}
      onWorkspaceCreated={vi.fn()}
    />,
  );
  await screen.findByRole("heading", { level: 1, name: "Risk analysis" });

  rerender(
    <Workspace
      clients={clients}
      projectId="project-2"
      onProjectChange={vi.fn()}
      onWorkspaceCreated={vi.fn()}
    />,
  );
  expect(await screen.findByRole("option", { name: /Project B evidence/ })).toBeVisible();

  projectAEvidence.resolve(Response.json([artifact("a", "Project A evidence")]));
  await act(async () => {
    await projectAEvidence.promise;
  });

  expect(screen.queryByRole("option", { name: /Project A evidence/ })).not.toBeInTheDocument();
  expect(screen.getByRole("option", { name: /Project B evidence/ })).toBeVisible();
});

test("autosaves a determination through the API", async () => {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { level: 1, name: "Risk analysis" });

  await user.click(screen.getByRole("button", { name: "Pending" }));

  expect(fetch).toHaveBeenCalledWith(
    "/api/assessments/assessment-1/determinations/child-1",
    expect.objectContaining({
      method: "PUT",
      body: expect.stringContaining('"status":"Pending"'),
    }),
  );
  expect(await screen.findByText("Saved")).toBeInTheDocument();
});

test("a refused HIPAA determination shows the API reason and keeps the last saved status (#140)", async () => {
  let attempts = 0;
  mockApi(async (input, init) => {
    const url = String(input);
    if (url.includes("/determinations/child-1") && init?.method === "PUT") {
      attempts += 1;
      return attempts === 1
        ? Response.json({ detail: "Met requires mapped evidence or a documented interview/observation" }, { status: 422 })
        : Response.json({ ...detail.determination, status: "Met" });
    }
    if (url === "/api/projects/project-1/assessment") return Response.json(assessment);
    if (url.includes("/records/child-1")) return Response.json(detail);
    if (url.includes("/evidence")) return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  render(<Workspace clients={clients} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} />);
  await screen.findByRole("heading", { level: 1, name: "Risk analysis" });
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Met" }));

  expect(await screen.findByText(/Met requires mapped evidence or a documented interview\/observation/)).toBeVisible();
  const decision = screen.getByRole("heading", { name: "Determination" }).closest("section")!;
  expect(within(decision).getByText("Blank")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Retry determination" }));
  await waitFor(() => expect(attempts).toBe(2));
  expect(await within(decision).findByText("Met", { selector: ".status-pill" })).toBeVisible();
});

test("refreshes assessment progress after the final determination save succeeds", async () => {
  let assessmentReads = 0;
  let detailReads = 0;
  mockApi(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/clients") {
      return Response.json([{ ...clients[0], projects: [clients[0].projects[0]] }]);
    }
    if (url === "/api/projects/project-1/assessment") {
      assessmentReads += 1;
      return Response.json({
        ...assessment,
        progress: {
          ...assessment.progress,
          resolved_determination_count: assessmentReads === 1 ? 37 : 38,
        },
      });
    }
    if (url.includes("/records/child-1")) {
      detailReads += 1;
      return Response.json(detailReads === 1 ? detail : refreshedDeterminationDetail);
    }
    if (url.includes("/determinations/child-1") && init?.method === "PUT") {
      return Response.json(refreshedDeterminationDetail.determination);
    }
    if (url === "/api/projects/project-1/evidence") return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const user = userEvent.setup();
  render(<App />);
  expect(await screen.findByText("37 of 149 resolved")).toBeVisible();

  await user.click(screen.getByRole("button", { name: "Not Met" }));

  expect(await screen.findByText("38 of 149 resolved")).toBeVisible();
  expect(assessmentReads).toBe(2);
});

test("opens a creator after the first client project exists", async () => {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { level: 1, name: "Risk analysis" });

  await user.click(screen.getByRole("button", { name: "+ Client / project" }));

  expect(screen.getByRole("form", { name: "Create client project" })).toBeVisible();
  expect(screen.getByRole("option", { name: "Northwind Health" })).toBeInTheDocument();
  expect(screen.getByRole("option", { name: "New client…" })).toBeInTheDocument();
});

test("keeps direct file selection and shows the initial evidence version, hash, and review state", async () => {
  mockApi(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/clients") {
      return Response.json([
        {
          id: "client-1",
          name: "Northwind Health",
          projects: [{ id: "project-1", name: "HIPAA 2026", framework_version_id: "hipaa-45cfr164-2026-07-01" }],
        },
      ]);
    }
    if (url === "/api/projects/project-1/assessment") return Response.json(assessment);
    if (url.includes("/records/child-1")) {
      return Response.json({
        ...detail,
        evidence: [{
          mapping_id: "mapping-1",
          artifact_id: "artifact-1",
          name: "synthetic-risk-register.txt",
          relative_path: "project-1/artifact-1-synthetic-risk-register.txt",
          rationale: "Synthetic evidence supports the risk analysis.",
          shared_record_count: 1,
          version_number: 1,
          sha256: "1a2b3c4d5e6f",
          review_state: "Not reviewed",
        }],
      });
    }
    if (url === "/api/projects/project-1/evidence") return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  render(<App />);

  expect(await screen.findByText("Version 1")).toBeVisible();
  expect(screen.getByText("SHA-256: 1a2b3c4d5e6f")).toBeVisible();
  expect(screen.getByText("Not reviewed")).toBeVisible();
  expect(screen.getByLabelText("Add evidence file")).toHaveAttribute("type", "file");
  expect(screen.queryByText(/scanner/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/attest/i)).not.toBeInTheDocument();
  expect(screen.queryByText(/reference-only/i)).not.toBeInTheDocument();
});

test("serializes prompt autosaves without acknowledging a newer draft early", async () => {
  const first = deferredResponse();
  const second = deferredResponse();
  let saves = 0;
  mockApi(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/prompts/prompt-check/answer") && init?.method === "PUT") {
      saves += 1;
      return saves === 1 ? first.promise : second.promise;
    }
    if (url === "/api/clients") return Response.json([
      { id: "client-1", name: "Northwind Health", projects: [{ id: "project-1", name: "HIPAA 2026", framework_version_id: "hipaa-45cfr164-2026-07-01" }] },
      { id: "client-2", name: "Contoso Health", projects: [{ id: "project-2", name: "HIPAA 2026", framework_version_id: "hipaa-45cfr164-2026-07-01" }] },
    ]);
    if (url === "/api/projects/project-1/assessment") return Response.json(assessment);
    if (url.includes("/records/child-1")) return Response.json(detail);
    if (url === "/api/projects/project-1/evidence") return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const user = userEvent.setup();
  render(<App />);
  const answer = await screen.findByRole("textbox", { name: "Answer: Has all ePHI been identified?" });

  await user.type(answer, "first");
  fireEvent.blur(answer);
  await waitFor(() => expect(saves).toBe(1));
  await user.clear(answer);
  await user.type(answer, "second");
  fireEvent.blur(answer);

  expect(screen.getAllByText("Saving").length).toBeGreaterThan(0);
  expect(saves).toBe(1);
  first.resolve(Response.json({ answer: "first" }));
  await waitFor(() => expect(saves).toBe(2));
  expect(screen.getAllByText("Saving").length).toBeGreaterThan(0);
  expect(answer).toHaveValue("second");

  second.resolve(Response.json({ answer: "second" }));
  expect(await screen.findByText("Saved")).toBeInTheDocument();
  expect(answer).toHaveValue("second");
});

test("refreshes the derived determination only after the latest queued save succeeds", async () => {
  const first = deferredResponse();
  const second = deferredResponse();
  let saves = 0;
  let detailReads = 0;
  mockApi(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/determinations/child-1") && init?.method === "PUT") {
      saves += 1;
      return saves === 1 ? first.promise : second.promise;
    }
    if (url === "/api/clients") {
      return Response.json([{ id: "client-1", name: "Northwind Health", projects: [{ id: "project-1", name: "HIPAA 2026", framework_version_id: "hipaa-45cfr164-2026-07-01" }] }]);
    }
    if (url === "/api/projects/project-1/assessment") return Response.json(assessment);
    if (url.includes("/records/child-1")) {
      detailReads += 1;
      return Response.json(detailReads === 1 ? detail : refreshedDeterminationDetail);
    }
    if (url === "/api/projects/project-1/evidence") return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { level: 1, name: "Risk analysis" });

  await user.click(screen.getByRole("button", { name: "Pending" }));
  await waitFor(() => expect(saves).toBe(1));
  await user.click(screen.getByRole("button", { name: "Not Met" }));
  first.resolve(Response.json({ ...detail.determination, status: "Pending" }));
  await waitFor(() => expect(saves).toBe(2));

  expect(detailReads).toBe(1);
  expect(screen.getByRole("button", { name: "Not Met" })).toHaveClass("selected");
  expect(screen.getAllByText("Saving").length).toBeGreaterThan(0);

  second.resolve(Response.json({ ...detail.determination, status: "Not Met" }));
  await waitFor(() => expect(detailReads).toBe(2));
  expect(screen.getByText("Derived · Not Met")).toBeVisible();
  expect(screen.getByRole("button", { name: "Not Met" })).toHaveClass("selected");
});

test("keeps the newest same-record determination refresh when earlier detail reads resolve late", async () => {
  const firstRefresh = deferredResponse();
  const secondRefresh = deferredResponse();
  let detailReads = 0;
  mockApi(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/determinations/child-1") && init?.method === "PUT") {
      return Response.json({ ...detail.determination, status: "Pending" });
    }
    if (url === "/api/clients") {
      return Response.json([{ id: "client-1", name: "Northwind Health", projects: [{ id: "project-1", name: "HIPAA 2026", framework_version_id: "hipaa-45cfr164-2026-07-01" }] }]);
    }
    if (url === "/api/projects/project-1/assessment") return Response.json(assessment);
    if (url.includes("/records/child-1")) {
      detailReads += 1;
      if (detailReads === 1) return Response.json(detail);
      return detailReads === 2 ? firstRefresh.promise : secondRefresh.promise;
    }
    if (url === "/api/projects/project-1/evidence") return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { level: 1, name: "Risk analysis" });

  await user.click(screen.getByRole("button", { name: "Pending" }));
  await waitFor(() => expect(detailReads).toBe(2));
  await user.click(screen.getByRole("button", { name: "Not Met" }));
  await waitFor(() => expect(detailReads).toBe(3));

  secondRefresh.resolve(Response.json(refreshedDeterminationDetail));
  expect(await screen.findByText("Derived · Not Met")).toBeVisible();
  await act(async () => {
    firstRefresh.resolve(Response.json(detail));
    await firstRefresh.promise;
  });
  expect(screen.getByText("Derived · Not Met")).toBeVisible();
  expect(screen.queryByText("Derived · Pending")).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Not Met" })).toHaveClass("selected");
});

test("keeps a failed note draft and retries it without retyping", async () => {
  const retry = deferredResponse();
  let attempts = 0;
  mockApi(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/records/child-1/note") && init?.method === "PUT") {
      attempts += 1;
      return attempts === 1
        ? Response.json({ detail: "offline" }, { status: 503 })
        : retry.promise;
    }
    if (url === "/api/clients") {
      return Response.json([{ id: "client-1", name: "Northwind Health", projects: [{ id: "project-1", name: "HIPAA 2026", framework_version_id: "hipaa-45cfr164-2026-07-01" }] }]);
    }
    if (url === "/api/projects/project-1/assessment") return Response.json(assessment);
    if (url.includes("/records/child-1")) return Response.json(detail);
    if (url === "/api/projects/project-1/evidence") return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const user = userEvent.setup();
  render(<App />);
  const note = await screen.findByRole("textbox", { name: "Record notes" });

  await user.type(note, "Keep this exact draft");
  fireEvent.blur(note);
  expect((await screen.findAllByText("Save failed")).length).toBeGreaterThan(0);
  expect(note).toHaveValue("Keep this exact draft");
  await user.click(screen.getByRole("button", { name: "Retry note" }));
  await waitFor(() => expect(attempts).toBe(2));
  expect(note).toHaveValue("Keep this exact draft");

  retry.resolve(Response.json({ note: "Keep this exact draft" }));
  expect(await screen.findByText("Saved")).toBeInTheDocument();
});

test("warns on failed-save navigation and retries the existing note without duplicate client work", async () => {
  let noteWrites = 0;
  let clientReads = 0;
  mockApi(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/records/child-1/note") && init?.method === "PUT") {
      noteWrites += 1;
      return noteWrites === 1
        ? Response.json({ detail: "offline" }, { status: 503 })
        : Response.json({ note: "Retry this record only" });
    }
    if (url === "/api/clients") {
      clientReads += 1;
      return Response.json([{ id: "client-1", name: "Northwind Health", projects: [{ id: "project-1", name: "HIPAA 2026", framework_version_id: "hipaa-45cfr164-2026-07-01" }] }]);
    }
    if (url === "/api/projects/project-1/assessment") return Response.json(assessment);
    if (url.includes("/records/child-1")) return Response.json(detail);
    if (url === "/api/projects/project-1/evidence") return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  const user = userEvent.setup();
  render(<App />);
  const note = await screen.findByRole("textbox", { name: "Record notes" });

  await user.type(note, "Retry this record only");
  fireEvent.blur(note);
  await screen.findByText("Save failed");
  await user.click(screen.getByRole("button", { name: "Overview" }));
  expect(confirm).toHaveBeenCalledTimes(1);
  expect(screen.getByRole("heading", { level: 1, name: "Risk analysis" })).toBeVisible();

  const failedBeforeUnload = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(failedBeforeUnload);
  expect(failedBeforeUnload.defaultPrevented).toBe(true);

  await user.click(screen.getByRole("button", { name: "Retry note" }));
  await waitFor(() => expect(noteWrites).toBe(2));
  expect(clientReads).toBe(1);
  expect(note).toHaveValue("Retry this record only");
  expect(await screen.findByText("Saved")).toBeInTheDocument();
});

test("serializes prompt, note, and determination autosaves for the same assessment record", async () => {
  const promptSave = deferredResponse();
  const noteSave = deferredResponse();
  const determinationSave = deferredResponse();
  const started: string[] = [];
  mockApi(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/prompts/prompt-check/answer") && init?.method === "PUT") {
      started.push("prompt");
      return promptSave.promise;
    }
    if (url.includes("/records/child-1/note") && init?.method === "PUT") {
      started.push("note");
      return noteSave.promise;
    }
    if (url.includes("/determinations/child-1") && init?.method === "PUT") {
      started.push("determination");
      return determinationSave.promise;
    }
    if (url === "/api/clients") {
      return Response.json([{ id: "client-1", name: "Northwind Health", projects: [{ id: "project-1", name: "HIPAA 2026", framework_version_id: "hipaa-45cfr164-2026-07-01" }] }]);
    }
    if (url === "/api/projects/project-1/assessment") return Response.json(assessment);
    if (url.includes("/records/child-1")) return Response.json(detail);
    if (url === "/api/projects/project-1/evidence") return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const user = userEvent.setup();
  render(<App />);
  const answer = await screen.findByRole("textbox", { name: "Answer: Has all ePHI been identified?" });
  const note = screen.getByRole("textbox", { name: "Record notes" });

  await user.type(answer, "prompt draft");
  fireEvent.blur(answer);
  await waitFor(() => expect(started).toEqual(["prompt"]));
  await user.type(note, "note draft");
  fireEvent.blur(note);
  await user.click(screen.getByRole("button", { name: "Pending" }));
  expect(started).toEqual(["prompt"]);
  promptSave.resolve(Response.json({ answer: "prompt draft" }));
  await waitFor(() => expect(started).toEqual(["prompt", "note"]));
  noteSave.resolve(Response.json({ note: "note draft" }));
  await waitFor(() => expect(started).toEqual(["prompt", "note", "determination"]));
  determinationSave.resolve(Response.json({ ...detail.determination, status: "Pending" }));
  expect(await screen.findByText("Saved")).toBeInTheDocument();
});

test("does not make different assessment records wait on one global queue", async () => {
  const firstRecordSave = deferredResponse();
  const secondRecordSave = deferredResponse();
  const started: string[] = [];
  mockApi(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/prompts/prompt-check/answer") && init?.method === "PUT") {
      started.push("child-1");
      return firstRecordSave.promise;
    }
    if (url.includes("/records/child-2/note") && init?.method === "PUT") {
      started.push("child-2");
      return secondRecordSave.promise;
    }
    if (url === "/api/clients") {
      return Response.json([{ id: "client-1", name: "Northwind Health", projects: [{ id: "project-1", name: "HIPAA 2026", framework_version_id: "hipaa-45cfr164-2026-07-01" }] }]);
    }
    if (url === "/api/projects/project-1/assessment") return Response.json(assessment);
    if (url.includes("/records/child-1")) return Response.json(detail);
    if (url.includes("/records/child-2")) return Response.json(secondRecordDetail);
    if (url === "/api/projects/project-1/evidence") return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  vi.spyOn(window, "confirm").mockReturnValue(true);
  const user = userEvent.setup();
  render(<App />);
  const answer = await screen.findByRole("textbox", { name: "Answer: Has all ePHI been identified?" });

  await user.type(answer, "first record draft");
  fireEvent.blur(answer);
  await waitFor(() => expect(started).toEqual(["child-1"]));
  await user.click(screen.getByRole("button", { name: /Risk management/ }));
  const note = await screen.findByRole("textbox", { name: "Record notes" });
  await user.type(note, "second record draft");
  fireEvent.blur(note);

  await waitFor(() => expect(started).toEqual(expect.arrayContaining(["child-1", "child-2"])));
  firstRecordSave.resolve(Response.json({ answer: "first record draft" }));
  secondRecordSave.resolve(Response.json({ note: "second record draft" }));
  expect(await screen.findByText("Saved")).toBeInTheDocument();
});

test("warns before record navigation and before unload until the latest save succeeds", async () => {
  const pending = deferredResponse();
  let pendingRequests = 0;
  mockApi(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.includes("/prompts/prompt-check/answer") && init?.method === "PUT") {
      pendingRequests += 1;
      return pending.promise;
    }
    if (url === "/api/clients") {
      return Response.json([{ id: "client-1", name: "Northwind Health", projects: [{ id: "project-1", name: "HIPAA 2026", framework_version_id: "hipaa-45cfr164-2026-07-01" }] }]);
    }
    if (url === "/api/projects/project-1/assessment") return Response.json(assessment);
    if (url.includes("/records/child-1")) return Response.json(detail);
    if (url === "/api/projects/project-1/evidence") return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  const user = userEvent.setup();
  render(<App />);
  const answer = await screen.findByRole("textbox", { name: "Answer: Has all ePHI been identified?" });

  await user.type(answer, "draft");
  fireEvent.blur(answer);
  await waitFor(() => expect(pendingRequests).toBe(1));
  await user.click(screen.getByRole("button", { name: /Risk management/ }));
  expect(confirm).toHaveBeenCalled();
  expect(screen.getByRole("heading", { level: 1, name: "Risk analysis" })).toBeVisible();
  fireEvent.change(screen.getAllByRole("combobox")[0], { target: { value: "project-2" } });
  expect(confirm).toHaveBeenCalledTimes(2);
  expect(screen.getByRole("heading", { level: 1, name: "Risk analysis" })).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Overview" }));
  expect(confirm).toHaveBeenCalledTimes(3);
  expect(screen.getByRole("heading", { level: 1, name: "Risk analysis" })).toBeVisible();

  const beforeUnload = new Event("beforeunload", { cancelable: true });
  window.dispatchEvent(beforeUnload);
  expect(beforeUnload.defaultPrevented).toBe(true);
  pending.resolve(Response.json({ answer: "draft" }));
  await waitFor(() => {
    const afterSave = new Event("beforeunload", { cancelable: true });
    window.dispatchEvent(afterSave);
    expect(afterSave.defaultPrevented).toBe(false);
  });
});

function cmmcFixtures() {
  const requirement = (id: string, title: string, sort: number) => ({
    record_id: id, citation: id, title, work_area: "Access Control", record_type: "requirement",
    parent_id: null, designation: null, sort_order: sort, editable_determination: false,
  });
  const objective = (parent: string, letter: string, sort: number) => ({
    record_id: `${parent}${letter}`, citation: `${parent}[${letter}]`, title: `Objective [${letter}]`,
    work_area: "Access Control", record_type: "objective", parent_id: parent, designation: null,
    sort_order: sort, editable_determination: true,
  });
  const workList = [
    requirement("AC.L2-3.1.1", "Authorized Access Control", 0),
    objective("AC.L2-3.1.1", "a", 1),
    objective("AC.L2-3.1.1", "b", 2),
    requirement("AC.L2-3.1.2", "Transaction & Function Control", 3),
    objective("AC.L2-3.1.2", "a", 4),
  ];
  const cmmc = {
    ...assessment,
    framework: {
      ...assessment.framework,
      id: "cmmc-l2-ag-v2.13",
      name: "CMMC Level 2",
      declarations: {
        ...assessment.framework.declarations,
        record_shape: { hierarchy: ["requirement", "objective"], determination_rule: "records_without_children" },
        status_set: ["", "Met", "Not Met", "Pending"],
        presentation_mode: "requirement_with_objectives",
        close_readiness: undefined,
      },
    },
    work_list: workList,
  };
  const requirementDetail = {
    ...detail,
    record: { ...workList[0], regulation_text: "Limit system access to authorized users." },
    determination: { ...detail.determination, status: "Not Met", derived: true },
    parent: null,
    parent_prompts: [],
    prompts: [],
    practitioner_guidance: {
      provenance: "RainTech CMMC assessment worksheet - practitioner guidance. Not DoD or NIST authority.",
      fields: { c3pao_guidance: "Access control lists and RBAC exports.", worksheet_level: "L1" },
    },
    children: [
      { ...workList[1], regulation_text: "authorized users are identified;", determination: { status: "Not Met" } },
      { ...workList[2], regulation_text: "processes acting on behalf of authorized users are identified;", determination: { status: "Met" } },
    ],
  };
  return { workList, cmmc, requirementDetail };
}

test("CMMC shows each requirement with every objective decidable on one view and lists only requirements", async () => {
  const { cmmc, requirementDetail } = cmmcFixtures();
  mockApi(async (input) => {
    const url = String(input);
    if (url.endsWith("/assessment")) return Response.json(cmmc);
    if (url.includes("/records/AC.L2-3.1.1")) return Response.json(requirementDetail);
    if (url.includes("/evidence")) return Response.json([]);
    if (url.endsWith("/finding")) return Response.json(null);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  render(<Workspace clients={clients} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} />);
  const objectives = await screen.findByRole("region", { name: "Assessment objectives" });
  expect(objectives).toHaveTextContent("authorized users are identified;");
  expect(objectives).toHaveTextContent("processes acting on behalf of authorized users are identified;");
  expect(screen.getByText("Derived · Not Met")).toBeVisible();
  // Every objective carries its own one-click determination on this view (#140).
  for (const citation of ["AC.L2-3.1.1[a]", "AC.L2-3.1.1[b]"]) {
    const group = within(objectives).getByRole("group", { name: `Determination for ${citation}` });
    expect(within(group).getAllByRole("button").map((button) => button.textContent)).toEqual(["Met", "Not Met", "Pending"]);
  }
  // The rail lists requirements by family; objectives are not rail rows.
  const rail = screen.getByRole("navigation", { name: "Requirements by family" });
  expect(within(rail).getByRole("button", { name: /Transaction & Function Control/ })).toBeVisible();
  expect(within(rail).queryByRole("button", { name: /Objective \[a\]/ })).not.toBeInTheDocument();
  expect(screen.getByRole("option", { name: "Access Control" })).toBeInTheDocument();
  expect(screen.queryByRole("option", { name: "Breach notification" })).not.toBeInTheDocument();
  // Close, packages, and HIPAA-shaped Not Met reconciliation are not offered for CMMC yet.
  expect(screen.queryByText("Assessment package")).not.toBeInTheDocument();
  expect(screen.queryByText("Not Met corrective work")).not.toBeInTheDocument();
  const guidance = screen.getByRole("region", { name: "RainTech practitioner guidance" });
  expect(guidance).toHaveTextContent("NOT DOD OR NIST TEXT");
  expect(guidance).toHaveTextContent("Access control lists and RBAC exports.");
  expect(guidance).not.toHaveTextContent("worksheet_level");
  expect(screen.getByRole("heading", { level: 1 }).closest("section")).not.toHaveTextContent("RBAC");
});

test("a project with no assessment offers one Start button that begins the assessment", async () => {
  let started = false;
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/projects/project-1/profile-readiness") {
      return Response.json({
        ...readiness,
        state: started ? "Intake complete" : "Intake started",
        assessment_exists: started,
        assessment_entry_allowed: started,
        assessment_entry_blocking_reasons: started ? [] : ["Complete the initial intake before starting a new assessment."],
      });
    }
    if (url === "/api/projects/project-1/start-assessment" && init?.method === "POST") {
      started = true;
      return Response.json({ assessment: { id: "assessment-1" }, readiness }, { status: 201 });
    }
    if (url === "/api/projects/project-1/assessment" && !started) {
      return Response.json({ detail: "Assessment not found" }, { status: 404 });
    }
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const user = userEvent.setup();
  render(
    <Workspace
      clients={clients}
      projectId="project-1"
      onProjectChange={vi.fn()}
      onWorkspaceCreated={vi.fn()}
    />,
  );

  expect(await screen.findByRole("heading", { name: "Ready to begin" })).toBeVisible();
  expect(screen.getByRole("button", { name: "+ Client / project" })).toBeVisible();
  expect(screen.getAllByRole("button", { name: "Start assessment" })).toHaveLength(1);
  await user.click(screen.getByRole("button", { name: "Start assessment" }));
  await waitFor(() => expect(
    vi.mocked(fetch).mock.calls.some(
      ([input, init]) => String(input).endsWith("/start-assessment") && init?.method === "POST",
    ),
  ).toBe(true));
});

test("the Profile view keeps the readiness decision form in a collapsed advanced section", async () => {
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/projects/project-1/profile-readiness") {
      return Response.json({ ...readiness, state: "Intake started", assessment_exists: false });
    }
    if (url === "/api/projects/project-1/assessment") {
      return Response.json({ detail: "Assessment not found" }, { status: 404 });
    }
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  render(
    <Workspace
      clients={clients}
      projectId="project-1"
      onProjectChange={vi.fn()}
      onWorkspaceCreated={vi.fn()}
      initialView="profile"
    />,
  );

  expect(await screen.findByRole("button", { name: "Profile" })).toHaveClass("active");
  const summary = screen.getByText("Readiness history (advanced)");
  expect(summary.closest("details")).not.toHaveAttribute("open");
  expect(screen.queryByRole("button", { name: "Start assessment" })).not.toBeInTheDocument();
});

test("the readiness form has no reviewer or approval-evidence fields and cannot type Profile complete", async () => {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { level: 1, name: "Risk analysis" });
  await user.click(screen.getByRole("button", { name: "Profile" }));
  const next = screen.getByLabelText("Next state");
  expect(within(next).getAllByRole("option").map((option) => option.textContent)).toEqual(["Needs follow-up"]);
  expect(screen.queryByLabelText("Named reviewer")).not.toBeInTheDocument();
  expect(screen.queryByLabelText("Review / approval evidence")).not.toBeInTheDocument();
  // Profile complete is recorded by approving the Profile version.
  expect(screen.queryByRole("option", { name: "Profile complete" })).not.toBeInTheDocument();
});

test("project creation sends the chosen framework version", async () => {
  const posted: string[] = [];
  mockApi(async (input, init) => {
    const url = String(input);
    if (url === "/api/frameworks") {
      return Response.json([
        { id: "cmmc-l2-ag-v2.13", name: "CMMC Level 2", record_count: 430 },
        { id: "hipaa-45cfr164-2026-07-01", name: "HIPAA 45 CFR Part 164", record_count: 194 },
      ]);
    }
    if (url === "/api/clients" && init?.method === "POST") return Response.json({ id: "client-new" });
    if (url === "/api/clients") return Response.json([]);
    if (url.endsWith("/projects") && init?.method === "POST") {
      posted.push(String(init.body));
      return Response.json({ id: "project-new" });
    }
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  render(<App />);
  const user = userEvent.setup();
  await user.type(await screen.findByPlaceholderText("e.g. Northwind Health"), "Contoso Defense");
  await user.type(screen.getByPlaceholderText("e.g. CMMC L2 2026"), "CMMC L2 2026");
  await user.selectOptions(await screen.findByLabelText("Framework"), "cmmc-l2-ag-v2.13");
  await user.click(screen.getByRole("button", { name: /Create and start/ }));
  await waitFor(() => expect(posted).toHaveLength(1));
  expect(JSON.parse(posted[0])).toMatchObject({ framework_version_id: "cmmc-l2-ag-v2.13" });
});

test("CMMC shows the official score and the requirement finding with POA&M items", async () => {
  const { cmmc, requirementDetail } = cmmcFixtures();
  const scored = {
    ...cmmc,
    framework: {
      ...cmmc.framework,
      declarations: {
        ...cmmc.framework.declarations,
        scoring: {
          authority: "32 CFR 170.24 CMMC Scoring Methodology",
          requirements: { "AC.L2-3.1.1": { rule: "fixed", points: 5, source: "32 CFR 170.24(c)(2)(i)(B)(1)" } },
        },
      },
    },
  };
  mockApi(async (input) => {
    const url = String(input);
    if (url.endsWith("/assessment")) return Response.json(scored);
    if (url.endsWith("/cmmc-score")) {
      return Response.json(cmmcScoreFixture(
        [{ record_id: "AC.L2-3.1.1", title: "Authorized Access Control", points: 5, state: "not_met" }],
        { complete: false, blockers: ["108 requirement(s) are not yet Met or Not Met."] },
      ));
    }
    if (url.endsWith("/finding")) {
      return Response.json({
        finding: { id: "finding-1", title: "Not Met: AC.L2-3.1.1 Authorized Access Control", status: "Open" },
        requirement_id: "AC.L2-3.1.1", requirement_status: "Not Met",
        failed_objectives: [{ record_id: "AC.L2-3.1.1a", citation: "AC.L2-3.1.1[a]", regulation_text: "authorized users are identified;", note: "List is stale.", interview_observation: "", evidence: [{ name: "users.txt", rationale: "Current list" }] }],
        poam_items: [{ id: "action-1", title: "Rebuild the authorized user list", description: "", status: "Open", validation_state: "Not Ready" }],
        history: [{ event: "opened", failed_objectives: ["AC.L2-3.1.1a"], created_at: "2026-10-06T18:00:00Z" }],
      });
    }
    if (url.includes("/records/AC.L2-3.1.1")) return Response.json(requirementDetail);
    if (url.includes("/evidence")) return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  render(<Workspace clients={clients} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} />);
  const score = await screen.findByRole("region", { name: "Official CMMC score" });
  expect(score).toHaveTextContent("105");
  expect(score).toHaveTextContent("of 110 · provisional");
  expect(score).toHaveTextContent("Not eligible");
  const finding = await screen.findByRole("region", { name: "Requirement finding" });
  expect(finding).toHaveTextContent("5 points if Not Met");
  expect(finding).toHaveTextContent("32 CFR 170.24(c)(2)(i)(B)(1)");
  expect(await within(finding).findByText(/List is stale/)).toBeVisible();
  expect(finding).toHaveTextContent("Evidence: users.txt");
  expect(finding).toHaveTextContent("Rebuild the authorized user list");
  // Already on an open POA&M item: no second draft (#143).
  expect(within(finding).getByRole("button", { name: "Create POA&M draft" })).toBeDisabled();
  expect(finding).toHaveTextContent("Already on POA&M item “Rebuild the authorized user list” (Open).");

  // The Overview carries the same two scores and the 32 CFR 170.21 checks (#141).
  await userEvent.setup().click(screen.getAllByRole("button", { name: "Overview" })[0]);
  const overview = await screen.findByRole("region", { name: "CMMC score and Conditional status" });
  expect(overview).toHaveTextContent("VERIFIED SPRS105of 110 · provisional");
  expect(overview).toHaveTextContent("105 Projected (includes Met awaiting evidence)");
  expect(within(overview).getByRole("region", { name: "32 CFR 170.21 Conditional status checks" })).toHaveTextContent("Not eligible");
});

test("shows a persistent backup warning and backs up on request", async () => {
  const posts: string[] = [];
  let failing = true;
  mockApi(async (input, init) => {
    const url = String(input);
    if (url === "/api/backups" && init?.method === "POST") {
      posts.push(url);
      failing = false;
      return Response.json({ id: "b1", kind: "manual", status: "complete" }, { status: 201 });
    }
    if (url === "/api/backups") {
      return Response.json({
        warning: failing ? "The last automatic daily backup failed: disk full" : null,
        backups: [{ status: failing ? "failed" : "complete", completed_at: "2026-10-06T18:00:00Z" }],
      });
    }
    if (url.endsWith("/assessment")) return Response.json(assessment);
    if (url.includes("/records/child-1")) return Response.json(detail);
    if (url.includes("/evidence")) return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  render(<Workspace clients={clients} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} />);
  const warning = await screen.findByTitle("The last automatic daily backup failed: disk full");
  expect(warning).toHaveTextContent("Backup failed");
  await userEvent.setup().click(screen.getByRole("button", { name: "Back up now" }));
  await waitFor(() => expect(posts).toHaveLength(1));
  await waitFor(() =>
    expect(screen.queryByTitle("The last automatic daily backup failed: disk full")).not.toBeInTheDocument(),
  );
});

test("offers the latest evidence version explicitly and manages the recycle bin", async () => {
  const calls: string[] = [];
  const withEvidence = {
    ...detail,
    evidence: [{
      mapping_id: "map-1", artifact_id: "art-1", name: "policy.txt", relative_path: "p/policy.txt",
      rationale: "Policy.", review_state: "Not reviewed", shared_record_count: 1, version_id: "v1",
      version_project_id: "project-1", version_number: 1, sha256: "abc", latest_version_number: 2,
      review_date: "2020-01-01",
    }],
  };
  mockApi(async (input, init) => {
    const url = String(input);
    if (init?.method && init.method !== "GET") calls.push(`${init.method} ${url}`);
    if (url.endsWith("/assessment")) return Response.json(assessment);
    if (url.includes("/records/child-1")) return Response.json(withEvidence);
    if (url.endsWith("/evidence?binned=true")) {
      return Response.json([{ id: "art-9", name: "old.txt", shared_record_count: 0, version_number: 1, sha256: "x", deleted_at: "2026-10-06" }]);
    }
    if (url.endsWith("/evidence")) return Response.json([]);
    if (url.endsWith("/evidence-library")) return Response.json({ today: "2026-10-08", lead_days: 30, assessment_id: "assessment-1", artifacts: [] });
    if (init?.method === "PUT" || init?.method === "POST") return Response.json({});
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  render(<Workspace clients={clients} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} />);
  expect(await screen.findByText(/Version 2 is available/)).toBeVisible();
  expect(screen.getByText("Review overdue since 2020-01-01")).toBeVisible();
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Use latest version" }));
  await waitFor(() => expect(calls).toContain("PUT /api/projects/project-1/assessments/assessment-1/evidence-mappings/map-1/version"));
  // The recycle bin moved from every record to the Evidence view (#142).
  await user.click(screen.getByRole("button", { name: "Evidence" }));
  await user.click(await screen.findByRole("button", { name: "Restore" }));
  await waitFor(() => expect(calls).toContain("POST /api/projects/project-1/evidence/art-9/restore"));
});

test("CMMC implementation statement saves one SSP version on request and the SSP panel approves", async () => {
  const { cmmc, requirementDetail } = cmmcFixtures();
  const scored = { ...cmmc, framework: { ...cmmc.framework, declarations: { ...cmmc.framework.declarations, scoring: { authority: "32 CFR 170.24", requirements: {} } } } };
  const sent: { method: string; url: string; body?: string }[] = [];
  const view = (approved: boolean, missing: string[]) => ({
    id: "ssp-1", template_version: "cmmc-ssp-v1", source_sha256: "abc",
    source: { requirements: [{ record_id: "AC.L2-3.1.1", citation: "AC.L2-3.1.1", status: "Implemented", poam_items: [] }] },
    versions: [{ id: "v1", version_number: 1, note: "Generated", created_at: "2026-10-06" }],
    latest: { id: "v1", version_number: approved ? 2 : 1, content: { system_description: "", environment_narrative: "", requirements: { "AC.L2-3.1.1": { implementation: "Drafted from notes." } } } },
    missing_for_approval: missing,
    approval: approved ? { approver_id: "johnathan", approved_at: "2026-10-06" } : null,
  });
  mockApi(async (input, init) => {
    const url = String(input);
    if (init?.method && init.method !== "GET") sent.push({ method: init.method, url, body: init.body as string });
    if (url.endsWith("/assessment")) return Response.json(scored);
    if (url.endsWith("/ssp") && !init?.method) return Response.json(view(false, []));
    if (url.endsWith("/ssp/ssp-1") && init?.method === "PUT") return Response.json(view(false, []));
    if (url.endsWith("/approve")) return Response.json(view(true, []));
    if (url.includes("/records/AC.L2-3.1.1")) return Response.json(requirementDetail);
    if (url.endsWith("/finding")) return Response.json(null);
    if (url.endsWith("/cmmc-score")) return Response.json(null);
    if (url.includes("/evidence")) return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  render(<Workspace clients={clients} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} />);
  const statementSection = await screen.findByRole("region", { name: "Implementation statement" });
  const statement = await within(statementSection).findByLabelText("Implementation statement for AC.L2-3.1.1");
  expect(statement).toHaveValue("Drafted from notes.");
  const user = userEvent.setup();
  await user.clear(statement);
  await user.type(statement, "Accounts reviewed quarterly.");
  // Typing never writes an SSP version; the explicit save writes exactly one.
  expect(sent.filter((c) => c.method === "PUT")).toHaveLength(0);
  await user.click(within(statementSection).getByRole("button", { name: "Save to SSP draft" }));
  await waitFor(() => expect(sent.filter((c) => c.method === "PUT" && c.body?.includes("Accounts reviewed quarterly."))).toHaveLength(1));
  // The full SSP panel is folded away below the requirement work.
  await user.click(screen.getByText("System Security Plan"));
  const panel = await screen.findByRole("region", { name: "System Security Plan" });
  expect(within(panel).queryByLabelText("Implementation statement for AC.L2-3.1.1")).not.toBeInTheDocument();
  await user.click(within(panel).getByRole("button", { name: "Approve and freeze" }));
  expect(await within(panel).findByText(/approved and frozen/)).toBeVisible();
  expect(within(panel).queryByRole("button", { name: "Save new version" })).not.toBeInTheDocument();
});

test("closes a CMMC POA&M item only after the requirement derives Met", async () => {
  const { cmmc, requirementDetail } = cmmcFixtures();
  const scored = { ...cmmc, framework: { ...cmmc.framework, declarations: { ...cmmc.framework.declarations, scoring: { authority: "32 CFR 170.24", requirements: { "AC.L2-3.1.1": { rule: "fixed", points: 5, source: "32 CFR 170.24(c)(2)(i)(B)(1)" } } } } } };
  const posts: string[] = [];
  const finding = (status: string) => ({
    finding: { id: "f1", title: "Not Met: AC.L2-3.1.1", status: "Open" },
    requirement_id: "AC.L2-3.1.1", requirement_status: "Met", failed_objectives: [],
    poam_items: [{ id: "act-1", title: "Rebuild the list", description: "", status, validation_state: "Not Ready" }],
    history: [],
  });
  mockApi(async (input, init) => {
    const url = String(input);
    if (init?.method === "POST") posts.push(url);
    if (url.endsWith("/assessment")) return Response.json(scored);
    if (url.endsWith("/poam/act-1/close")) return Response.json(finding("Closed"));
    if (url.endsWith("/finding")) return Response.json(finding("Open"));
    if (url.includes("/records/AC.L2-3.1.1")) return Response.json(requirementDetail);
    if (url.includes("/evidence")) return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  render(<Workspace clients={clients} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} />);
  const panel = await screen.findByRole("region", { name: "Requirement finding" });
  const user = userEvent.setup();
  // The verification rationale is written inline, not in a browser prompt (#143).
  await user.click(await within(panel).findByRole("button", { name: "Close item" }));
  const close = within(panel).getByRole("button", { name: "Close POA&M item" });
  expect(close).toBeDisabled();
  await user.type(within(panel).getByLabelText(/How was the remediation verified/), "List rebuilt and reviewed.");
  await user.click(close);
  await waitFor(() => expect(posts.some((url) => url.endsWith("/requirements/AC.L2-3.1.1/poam/act-1/close"))).toBe(true));
  expect(await within(panel).findByText(/Rebuild the list · Closed/)).toBeVisible();
  expect(within(panel).queryByRole("button", { name: "Close item" })).not.toBeInTheDocument();
});
