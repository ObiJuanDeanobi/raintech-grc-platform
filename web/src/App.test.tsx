import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import App from "./App";

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
  note: "",
  evidence: [],
  position: {
    current: 1,
    total: 149,
    previous_record_id: null,
    next_record_id: null,
  },
};

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

test("renders a determination-only work list with parent context", async () => {
  const user = userEvent.setup();
  render(<App />);

  expect(await screen.findByRole("heading", { level: 1, name: "Risk analysis" })).toBeInTheDocument();
  expect(screen.getByText("1 of 149")).toBeInTheDocument();
  expect(screen.getByText("Security management process")).toBeInTheDocument();
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

test("opens a creator after the first client project exists", async () => {
  const user = userEvent.setup();
  render(<App />);
  await screen.findByRole("heading", { level: 1, name: "Risk analysis" });

  await user.click(screen.getByRole("button", { name: "+ Client / project" }));

  expect(screen.getByRole("form", { name: "Create client project" })).toBeVisible();
  expect(screen.getByRole("option", { name: "Northwind Health" })).toBeInTheDocument();
  expect(screen.getByRole("option", { name: "New client…" })).toBeInTheDocument();
});
