import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import { SraPanel } from "./SraPanel";

function response(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function workspace(projectId = "project-1") {
  return {
    project_id: projectId,
    assessment_id: `assessment-${projectId}`,
    profile_version_id: `profile-${projectId}`,
    work_area: "Security Risk Analysis",
    status: "Incomplete",
    anchor: {
      record_id: "164.308(a)(1)(ii)(A)",
      citation: "45 CFR 164.308(a)(1)(ii)(A)",
      title: "Risk analysis",
      regulation_text: "Conduct an accurate and thorough assessment.",
      work_area: "security",
    },
    scope_items: [
      {
        id: null,
        scope_type: "system",
        target_key: "item:workstation",
        name: `Workstation ${projectId}`,
        included: null,
        exclusion_rationale: "",
        reviewed_by: "",
        reviewed_at: null,
      },
    ],
    risks: [],
    blockers: [`Review system scope: Workstation ${projectId}`],
    completion: {
      complete: false,
      percentage: 0,
      missing: [`Review system scope: Workstation ${projectId}`],
    },
  };
}

beforeEach(() => {
  vi.restoreAllMocks();
});

test("renders the declaration-selected fourth HIPAA work area and blockers", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response(workspace())));
  render(<SraPanel projectId="project-1" onDirtyChange={vi.fn()} />);
  expect(await screen.findByRole("heading", { name: "Security Risk Analysis" })).toBeVisible();
  expect(screen.getByText("45 CFR 164.308(a)(1)(ii)(A) · Risk analysis")).toBeVisible();
  expect(screen.getByText("Review system scope: Workstation project-1")).toBeVisible();
});

test("requires rationale before saving an explicit exclusion", async () => {
  const fetchMock = vi.fn().mockImplementation(async () => response(workspace()));
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();
  render(<SraPanel projectId="project-1" onDirtyChange={vi.fn()} />);
  await screen.findByText("Workstation project-1");
  await user.click(screen.getByRole("button", { name: "Exclude" }));
  expect(screen.getByText("Exclusion requires a rationale.")).toBeVisible();
  expect(fetchMock).toHaveBeenCalledTimes(1);

  await user.type(screen.getByLabelText("Exclusion rationale"), "Hosted outside the boundary");
  await user.click(screen.getByRole("button", { name: "Exclude" }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
  const body = JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body)) as Record<string, unknown>;
  expect(body).toMatchObject({
    profile_version_id: "profile-project-1",
    scope_type: "system",
    target_key: "item:workstation",
    included: false,
    exclusion_rationale: "Hosted outside the boundary",
  });
});

test("submits a complete threat-vulnerability risk against pinned identities", async () => {
  const fetchMock = vi.fn().mockImplementation(async () => response(workspace()));
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();
  render(<SraPanel projectId="project-1" onDirtyChange={vi.fn()} />);
  await screen.findByRole("heading", { name: "Add risk" });
  await user.type(screen.getByLabelText("Risk title"), "Lost workstation");
  await user.type(screen.getByLabelText("Threat"), "Theft");
  await user.type(screen.getByLabelText("Vulnerability"), "Portable device");
  await user.type(screen.getByLabelText("CIA impact"), "Confidentiality exposure");
  await user.type(screen.getByLabelText("Existing safeguards"), "Full disk encryption");
  await user.type(screen.getByLabelText("Owner"), "Security Officer");
  await user.click(screen.getByRole("button", { name: "Save risk" }));
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
  const body = JSON.parse(String(fetchMock.mock.calls[1]?.[1]?.body)) as Record<string, unknown>;
  expect(body).toMatchObject({
    assessment_id: "assessment-project-1",
    profile_version_id: "profile-project-1",
    threat: "Theft",
    vulnerability: "Portable device",
    inherent_likelihood: 1,
    residual_likelihood: 1,
  });
});

test("ignores a delayed response from the previously selected project", async () => {
  let releaseFirst!: (value: Response) => void;
  const first = new Promise<Response>((resolve) => { releaseFirst = resolve; });
  const fetchMock = vi.fn()
    .mockReturnValueOnce(first)
    .mockResolvedValueOnce(response(workspace("project-2")));
  vi.stubGlobal("fetch", fetchMock);
  const dirty = vi.fn();
  const view = render(<SraPanel projectId="project-1" onDirtyChange={dirty} />);
  view.rerender(<SraPanel projectId="project-2" onDirtyChange={dirty} />);
  expect(await screen.findByText("Workstation project-2")).toBeVisible();
  releaseFirst(response(workspace("project-1")));
  await waitFor(() => expect(screen.queryByText("Workstation project-1")).not.toBeInTheDocument());
});
