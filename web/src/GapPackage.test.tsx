import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import type { BlockerGroup, IssueChecklist } from "./types";
import { ReportsView } from "./views/reports/ReportsView";

/**
 * Issue #146: a CMMC finalize offers the gap assessment (the default) and the final
 * self-assessment as two plain options. The draft and the issue follow the choice;
 * HIPAA has no choice at all.
 */

const gapWarnings = [
  { key: "poam_open", label: "POA&M items still open", count: 2, detail: "1 of them are drafts.", target: "poam" },
  { key: "met_no_evidence", label: "Met, evidence still needed", count: 3, detail: "Not counted as verified Met.", target: "assessments" },
];
const selfGroups: BlockerGroup[] = [
  { key: "undecided", label: "Objectives not decided", count: 307, record_ids: [], target: "assessments" },
  { key: "not_met", label: "Objectives still Not Met", count: 6, record_ids: [], target: "assessments" },
];

const checklists: Record<string, IssueChecklist> = {
  gap_assessment: { package_type: "gap_assessment", ready: true, groups: [], warnings: gapWarnings, current_issue: null },
  readiness_close: { package_type: "readiness_close", ready: false, groups: selfGroups, warnings: [], current_issue: null },
};

interface Call { url: string; method: string; body?: Record<string, unknown> }

function serve(calls: Call[]) {
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    calls.push({ url, method, body: init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : undefined });
    if (url.includes("/issue-checklist")) {
      const choice = new URL(url, "http://localhost").searchParams.get("package") ?? "gap_assessment";
      return Response.json(checklists[choice]);
    }
    if (url.endsWith("/packages")) return Response.json([]);
    if (url.includes("/draft")) {
      return new Response(new Blob(["zip"]), { status: 200, headers: { "Content-Disposition": 'attachment; filename="DRAFT_x.zip"' } });
    }
    if (url.endsWith("/issue") && method === "POST") {
      return Response.json({ package_id: "pkg-1", issued_snapshot_id: "iss-1", issued_at: "2026-10-12T09:00:00Z", reviewer: "Johnathan", note: "", backup_id: "b-1", superseded_package_id: null }, { status: 201 });
    }
    return Response.json({ detail: "not found" }, { status: 404 });
  });
}

function renderReports(hasPackageChoice: boolean) {
  return render(
    <ReportsView
      projectId="project-1"
      assessmentId="assessment-1"
      records={[]}
      hasClose
      hasPackageChoice={hasPackageChoice}
      refreshKey={0}
      onReopened={async () => undefined}
      onOpenGroup={vi.fn()}
      onOpenTarget={vi.fn()}
    />,
  );
}

async function openDialog(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole("button", { name: "Finalize…" }));
  return screen.findByRole("dialog", { name: "Finalize deliverables" });
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
  URL.createObjectURL = vi.fn(() => "blob:draft");
  URL.revokeObjectURL = vi.fn();
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);
});
afterEach(() => vi.restoreAllMocks());

test("the dialog offers two options with one plain sentence each, Gap assessment first and chosen", async () => {
  serve([]);
  renderReports(true);
  const user = userEvent.setup();
  const dialog = await openDialog(user);
  const group = within(dialog).getByRole("group", { name: "Package" });
  const options = within(group).getAllByRole("radio");
  expect(options).toHaveLength(2);
  expect(within(group).getByRole("radio", { name: /^Gap assessment/ })).toBeChecked();
  expect(within(group).getByRole("radio", { name: /^Final self-assessment \(all requirements Met\)/ })).not.toBeChecked();
  expect(within(group).getByText("Shows where the client stands today, including requirements that are not met. It can be finalized with gaps.")).toBeVisible();
  expect(within(group).getByText("The close-out once every requirement is Met and verified. It cannot be finalized while any are left.")).toBeVisible();
});

test("the default gap assessment can be finalized with gaps: warnings, no blockers, and it issues as the gap assessment", async () => {
  const calls: Call[] = [];
  serve(calls);
  renderReports(true);
  const user = userEvent.setup();
  const dialog = await openDialog(user);
  expect(await within(dialog).findByText(/2 · POA&M items still open/)).toBeVisible();
  expect(within(dialog).queryByText("Fix before finalizing")).not.toBeInTheDocument();
  expect(calls.some((call) => call.url.endsWith("/issue-checklist?package=gap_assessment"))).toBe(true);

  await user.click(within(dialog).getByRole("button", { name: "Finalize" }));
  await waitFor(() => expect(calls.some((call) => call.method === "POST")).toBe(true));
  const posted = calls.find((call) => call.method === "POST")!;
  expect(posted.url).toBe("/api/projects/project-1/assessments/assessment-1/issue");
  expect(posted.body).toEqual({ actor_id: "johnathan", note: "", package: "gap_assessment" });
});

test("choosing the final self-assessment reloads its own gates and blocks the issue", async () => {
  const calls: Call[] = [];
  serve(calls);
  renderReports(true);
  const user = userEvent.setup();
  const dialog = await openDialog(user);
  await within(dialog).findByText(/2 · POA&M items still open/);
  await user.click(within(dialog).getByRole("radio", { name: /^Final self-assessment/ }));

  const section = await within(dialog).findByRole("region", { name: "Fix before finalizing" });
  expect(within(section).getByText(/307 · Objectives not decided/)).toBeVisible();
  expect(within(dialog).queryByText(/POA&M items still open/)).not.toBeInTheDocument();
  expect(within(dialog).getByRole("button", { name: "Finalize" })).toBeDisabled();
  expect(calls.some((call) => call.url.endsWith("/issue-checklist?package=readiness_close"))).toBe(true);
});

test("the draft download follows the same choice", async () => {
  const calls: Call[] = [];
  serve(calls);
  renderReports(true);
  const user = userEvent.setup();
  // The control sits above the draft button too.
  const page = await screen.findByRole("group", { name: "Package" });
  await user.click(screen.getByRole("button", { name: "Download draft" }));
  await waitFor(() => expect(calls.some((call) => call.url.includes("/draft"))).toBe(true));
  expect(calls.find((call) => call.url.includes("/draft"))!.url).toBe("/api/projects/project-1/assessments/assessment-1/draft?package=gap_assessment");

  await user.click(within(page).getByRole("radio", { name: /^Final self-assessment/ }));
  await user.click(screen.getByRole("button", { name: "Download draft" }));
  await waitFor(() => expect(calls.filter((call) => call.url.includes("/draft"))).toHaveLength(2));
  expect(calls.filter((call) => call.url.includes("/draft"))[1].url).toBe("/api/projects/project-1/assessments/assessment-1/draft?package=readiness_close");

  // The dialog opens on the choice already made.
  const dialog = await openDialog(user);
  expect(within(dialog).getByRole("radio", { name: /^Final self-assessment/ })).toBeChecked();
});

test("a framework with no choice (HIPAA) shows no package control and sends no package", async () => {
  const calls: Call[] = [];
  serve(calls);
  renderReports(false);
  const user = userEvent.setup();
  expect(screen.queryByRole("group", { name: "Package" })).not.toBeInTheDocument();
  const dialog = await openDialog(user);
  expect(within(dialog).queryByRole("radio")).not.toBeInTheDocument();
  await user.click(await within(dialog).findByRole("button", { name: "Finalize" }));
  await waitFor(() => expect(calls.some((call) => call.method === "POST")).toBe(true));
  expect(calls.find((call) => call.method === "POST")!.body).toEqual({ actor_id: "johnathan", note: "" });
  expect(calls.every((call) => !call.url.includes("package="))).toBe(true);
});

test("the dialog follows the kind of the current issue, so a plain reissue is not refused", async () => {
  const held = { package_id: "pkg-0", issued_at: "2026-10-01T00:00:00Z", assessment_id: "assessment-1", package_type: "readiness_close" as const };
  vi.mocked(fetch).mockImplementation(async (input) => {
    const url = String(input);
    if (url.includes("/issue-checklist")) {
      return Response.json({ package_type: "readiness_close", ready: true, groups: [], warnings: [], current_issue: held });
    }
    if (url.endsWith("/packages")) return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  renderReports(true);
  const user = userEvent.setup();
  const dialog = await openDialog(user);
  // It opens on the held kind instead of the gap default.
  await waitFor(() => expect(within(dialog).getByRole("radio", { name: /^Final self-assessment/ })).toBeChecked());
  expect(within(dialog).queryByRole("alert")).not.toBeInTheDocument();
  await waitFor(() => expect(within(dialog).getByRole("button", { name: "Finalize" })).toBeEnabled());

  // The other kind says why it cannot be issued, and the button stays off.
  await user.click(within(dialog).getByRole("radio", { name: /^Gap assessment/ }));
  expect(await within(dialog).findByText(/To issue the other kind, reopen the assessment first/)).toBeVisible();
  expect(within(dialog).getByRole("button", { name: "Finalize" })).toBeDisabled();
});
