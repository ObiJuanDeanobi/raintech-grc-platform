import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import App, { Workspace } from "./App";

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

const clients = [
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
];

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
  profile_completion_blocking_reasons: ["Record a named reviewer."],
  boundary_document: "docs/local-evidence-operating-boundary.md",
  acknowledgement: {
    document_path: "docs/local-evidence-operating-boundary.md",
    statement:
      "Acknowledges review of the local evidence operating boundary; this is not an attestation that content is free of CUI, PHI, or ePHI.",
    actor: { id: "johnathan", display_name: "Johnathan" },
    timestamp: "2026-08-26T00:00:00+00:00",
  },
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

test("renders close-readiness checks, blockers, later gates, and actionable record link", async () => {
  const calls: string[] = [];
  vi.mocked(fetch).mockImplementation(async (input) => {
    const url = String(input); calls.push(url);
    if (url.includes("profile-readiness")) return Response.json({ ...readiness, assessment_exists: true });
    if (url.endsWith("/assessment")) return Response.json(assessment);
    if (url.includes("close-readiness")) return Response.json({ target: "fieldwork_ready_for_generation", status: "Blocked", blockers: [{ message: "Resolve open findings" }], checks: [{ name: "Determinations", status: "pass" }], links: [{ label: "Open risk record", record_id: "child-1" }], metadata: { later_gates: ["Package sign-off"] } });
    if (url.includes("/records/child-1")) return Response.json(detail);
    if (url.includes("/evidence")) return Response.json([]);
    return Response.json({});
  });
  render(<Workspace clients={clients} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} />);
  expect(await screen.findByText("Fieldwork ready for generation")).toBeVisible();
  expect(screen.getByText("Resolve open findings")).toBeVisible();
  expect(screen.getByText("Determinations")).toBeVisible();
  expect(screen.getByText("Package sign-off")).toBeVisible();
  await userEvent.setup().click(screen.getByRole("button", { name: "Open risk record" }));
  expect(calls.some((url) => url.includes("close-readiness"))).toBe(true);
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
        state: "Intake started",
        assessment_exists: false,
        assessment_entry_allowed: false,
        assessment_entry_blocking_reasons: [
          "Complete the initial intake before starting a new assessment.",
        ],
        acknowledgement: null,
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

  expect(await screen.findByText("Intake started")).toBeVisible();
  expect(
    screen.getByText("Complete the initial intake before starting a new assessment."),
  ).toBeVisible();
  expect(screen.getByRole("button", { name: "Start assessment" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Profile" })).toBeEnabled();
  expect(screen.getByText(/not an attestation that content is free of CUI, PHI, or ePHI/i))
    .toBeVisible();
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
  await user.selectOptions(screen.getAllByRole("combobox")[0], "project-2");
  await waitFor(() =>
    expect(
      screen.getByRole("textbox", { name: "Answer: Has all ePHI been identified?" }),
    ).toHaveValue("Project B answer"),
  );
  expect(screen.queryByDisplayValue("Project A answer")).not.toBeInTheDocument();
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

function deferredResponse() {
  let resolve: (response: Response) => void;
  const promise = new Promise<Response>((done) => {
    resolve = done;
  });
  return { promise, resolve: resolve! };
}

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
