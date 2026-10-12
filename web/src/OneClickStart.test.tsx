import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import App from "./App";

/**
 * One click from creating a client to the first requirement: the Start click is the
 * intake decision, so nobody visits the Profile first.
 */

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

const readinessBase = {
  project_id: "project-1",
  supported_states: ["Intake started", "Intake complete", "Needs follow-up", "Profile complete"],
  allowed_next_states: ["Needs follow-up", "Profile complete"],
  follow_up_work_required_states: ["Needs follow-up"],
  follow_up_work_required_when_unresolved_required_fields: true,
  profile_completion_blocking_reasons: ["Approve the Profile version."],
  current_details: { unresolved_required_fields: [], follow_up_work: "", reviewed_by: "", approval_evidence: "" },
};

const clientsAfterCreate = [
  {
    id: "client-1",
    name: "Northwind Health",
    projects: [{ id: "project-1", name: "HIPAA 2026", framework_version_id: "hipaa-45cfr164-2026-07-01" }],
  },
];

let calls: Array<{ url: string; method: string }> = [];
let clientsList: unknown[] = [];
let started = false;
let startFails = false;
let assessmentFails = false;
let followUp = false;

beforeEach(() => {
  calls = [];
  clientsList = [];
  started = false;
  startFails = false;
  assessmentFails = false;
  followUp = false;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      const method = init?.method ?? "GET";
      calls.push({ url, method });
      if (url === "/api/frameworks") return Response.json([]);
      if (url === "/api/clients" && method === "POST") return Response.json({ id: "client-1" });
      if (url === "/api/clients") return Response.json(clientsList);
      if (url === "/api/clients/client-1/projects" && method === "POST") {
        clientsList = clientsAfterCreate;
        return Response.json({ id: "project-1" });
      }
      if (url === "/api/projects/project-1/start-assessment" && method === "POST") {
        if (startFails) return Response.json({ detail: "The database is busy. Try again." }, { status: 500 });
        started = true;
        return Response.json({ assessment: { id: "assessment-1" } }, { status: 201 });
      }
      if (url === "/api/projects/project-1/profile-readiness") {
        if (followUp) {
          return Response.json({
            ...readinessBase,
            state: "Needs follow-up",
            allowed_next_states: ["Intake complete"],
            assessment_exists: false,
            assessment_entry_allowed: false,
            assessment_entry_blocking_reasons: ["Resolve the recorded follow-up before starting."],
          });
        }
        return Response.json({
          ...readinessBase,
          state: started ? "Intake complete" : "Intake started",
          assessment_exists: started,
          assessment_entry_allowed: started,
          assessment_entry_blocking_reasons: started ? [] : ["Complete the initial intake before starting a new assessment."],
        });
      }
      if (url === "/api/projects/project-1/assessment") {
        if (assessmentFails) return Response.json({ detail: "boom" }, { status: 500 });
        return started ? Response.json(assessment) : Response.json({ detail: "Assessment not found" }, { status: 404 });
      }
      if (url.includes("/records/child-1")) return Response.json(detail);
      if (url === "/api/projects/project-1/evidence") return Response.json([]);
      return Response.json({ detail: "not found" }, { status: 404 });
    }),
  );
});

test("creating a client lands on the first requirement without visiting the Profile", async () => {
  const user = userEvent.setup();
  render(<App />);
  await user.type(await screen.findByPlaceholderText("e.g. Northwind Health"), "Northwind Health");
  await user.type(screen.getByPlaceholderText("e.g. CMMC L2 2026"), "HIPAA 2026");
  await user.click(screen.getByRole("button", { name: "Create and start" }));

  expect(await screen.findByRole("heading", { level: 1, name: "Risk analysis" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Assessments" })).toHaveClass("active");
  expect(screen.getByRole("button", { name: "Profile" })).not.toHaveClass("active");
  const posts = calls.filter((call) => call.method === "POST").map((call) => call.url);
  expect(posts).toEqual([
    "/api/clients",
    "/api/clients/client-1/projects",
    "/api/projects/project-1/start-assessment",
  ]);
  expect(posts.some((url) => url.includes("profile-readiness"))).toBe(false);
});

test("the assessment navigation has no Actions placeholder", async () => {
  started = true;
  clientsList = clientsAfterCreate;
  render(<App />);
  expect(await screen.findByRole("heading", { level: 1, name: "Risk analysis" })).toBeVisible();
  expect(screen.queryByRole("button", { name: "Actions" })).not.toBeInTheDocument();
});

test("a project with no assessment shows one Start button and no Actions placeholder", async () => {
  clientsList = clientsAfterCreate;
  render(<App />);
  expect(await screen.findByRole("heading", { name: "Ready to begin" })).toBeVisible();
  expect(screen.getAllByRole("button", { name: "Start assessment" })).toHaveLength(1);
  expect(screen.queryByRole("button", { name: "Actions" })).not.toBeInTheDocument();
  expect(
    screen.getByText(/Starting records that intake is done; you can fill in the Profile as you go/),
  ).toBeVisible();
  await waitFor(() => expect(calls.some((call) => call.url.endsWith("/start-assessment"))).toBe(false));
});

test("a failed start after create still opens the project and says why on the Start card", async () => {
  startFails = true;
  const user = userEvent.setup();
  render(<App />);
  await user.type(await screen.findByPlaceholderText("e.g. Northwind Health"), "Northwind Health");
  await user.type(screen.getByPlaceholderText("e.g. CMMC L2 2026"), "HIPAA 2026");
  await user.click(screen.getByRole("button", { name: "Create and start" }));

  expect(await screen.findByRole("heading", { name: "Ready to begin" })).toBeVisible();
  expect(await screen.findByRole("alert")).toHaveTextContent("The database is busy. Try again.");
  expect(screen.getByRole("button", { name: "Start assessment" })).toBeEnabled();
});

test("an assessment that cannot be loaded shows a retry, not an endless spinner", async () => {
  started = true;
  assessmentFails = true;
  clientsList = clientsAfterCreate;
  render(<App />);
  expect(await screen.findByRole("heading", { name: "The assessment did not open" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Try again" })).toBeEnabled();
  expect(screen.queryByText(/Opening the first requirement/)).not.toBeInTheDocument();
});

test("needs follow-up offers a way to the Profile instead of a dead end", async () => {
  followUp = true;
  clientsList = clientsAfterCreate;
  const user = userEvent.setup();
  render(<App />);
  expect(await screen.findByRole("heading", { name: "Ready to begin" })).toBeVisible();
  expect(screen.getByRole("button", { name: "Start assessment" })).toBeDisabled();
  expect(screen.getByText("Resolve the recorded follow-up before starting.")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Open the Profile to resolve the follow-up" }));
  expect(screen.getByRole("button", { name: "Profile" })).toHaveClass("active");
  expect(screen.getByText(/Readiness history \(advanced\)/).closest("details")).toHaveAttribute("open");
});
