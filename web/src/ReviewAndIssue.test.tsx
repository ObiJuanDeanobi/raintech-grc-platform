import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import type { BlockerGroup, IssueChecklist } from "./types";
import { ReportsView } from "./views/reports/ReportsView";

/**
 * Issue #145, ADR 0022: one Finalize dialog. What must be fixed is separate from
 * what is only worth a look and what will be locked; nothing is ticked, there is
 * no role field and no separate backup step; a failed backup says nothing was issued.
 */

const warnings = [
  { key: "open_corrective_work", label: "Corrective work still open", count: 3, detail: "It will be listed as open in the POA&M. Issuing does not close it.", target: "poam" },
  { key: "evidence_due_soon", label: "Evidence due for review soon", count: 2, detail: "Worth refreshing before the report goes out.", target: "evidence" },
  { key: "profile_follow_up", label: "Profile follow-up recorded", count: 1, detail: "Still to be confirmed with the client: Final endpoint count.", target: "profile" },
];

const blocking: BlockerGroup[] = [
  { key: "undecided", label: "Objectives not decided", count: 4, record_ids: ["a", "b"], target: "assessments" },
  { key: "profile", label: "Profile not approved", count: 1, record_ids: [], target: "profile" },
];

function checklist(overrides: Partial<IssueChecklist> = {}): IssueChecklist {
  return { ready: true, groups: [], warnings: [], current_issue: null, ...overrides };
}

interface Server {
  posts: Array<{ url: string; body: Record<string, unknown> }>;
  checklist: IssueChecklist;
  issue: () => Response;
}

function serve(server: Server) {
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    const url = String(input);
    if (url.endsWith("/issue-checklist")) return Response.json(server.checklist);
    if (url.endsWith("/packages")) return Response.json([]);
    if (url.endsWith("/profile")) return Response.json({ active_version_id: "pv-3", versions: [{ id: "pv-3", version_number: 3 }, { id: "pv-2", version_number: 2 }] });
    if (url.endsWith("/issue") && init?.method === "POST") {
      server.posts.push({ url, body: JSON.parse(String(init.body)) as Record<string, unknown> });
      return server.issue();
    }
    return Response.json({ detail: "not found" }, { status: 404 });
  });
}

function renderReports(handlers: { onOpenGroup?: (group: BlockerGroup) => void; onOpenTarget?: (target: string) => void } = {}) {
  return render(
    <ReportsView
      projectId="project-1"
      assessmentId="assessment-1"
      records={[]}
      hasClose
      refreshKey={0}
      onReopened={async () => undefined}
      onOpenGroup={handlers.onOpenGroup ?? vi.fn()}
      onOpenTarget={handlers.onOpenTarget ?? vi.fn()}
    />,
  );
}

async function openDialog(user: ReturnType<typeof userEvent.setup>) {
  await user.click(await screen.findByRole("button", { name: "Finalize…" }));
  return screen.findByRole("dialog", { name: "Finalize deliverables" });
}

const issued = () => Response.json({ package_id: "pkg-1", issued_snapshot_id: "iss-1", issued_at: "2026-10-12T09:00:00Z", reviewer: "Johnathan", note: "", backup_id: "b-1", superseded_package_id: null }, { status: 201 });

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

test("one dialog: reviewer, date, optional note, one Finalize button, and no role, ticks or separate steps", async () => {
  serve({ posts: [], checklist: checklist(), issue: issued });
  renderReports();
  const user = userEvent.setup();
  const dialog = await openDialog(user);
  await within(dialog).findByRole("button", { name: "Finalize" });

  expect(within(dialog).getByText("Locks your data as it is now.")).toBeVisible();
  expect(screen.queryByText(/Review and issue/)).not.toBeInTheDocument();
  expect(within(dialog).getByText("Reviewer")).toBeVisible();
  expect(within(dialog).getByText("Johnathan")).toBeVisible();
  expect(within(dialog).getByText("Date")).toBeVisible();
  expect(within(dialog).getByText(new Date().toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" }))).toBeVisible();
  expect(within(dialog).getByLabelText(/Note/)).not.toBeRequired();

  // Nothing to tick, no role, and none of the old chain's controls anywhere.
  expect(within(dialog).queryAllByRole("checkbox")).toHaveLength(0);
  expect(within(dialog).queryByLabelText(/role/i)).not.toBeInTheDocument();
  expect(within(dialog).queryByLabelText(/reviewer name/i)).not.toBeInTheDocument();
  for (const gone of ["Start review", "Mark reviewed", "Sign off: Ready to issue", "Create and validate backup", "Issue final deliverables", "Generate package"]) {
    expect(screen.queryByRole("button", { name: gone })).not.toBeInTheDocument();
  }
  expect(screen.getAllByRole("dialog")).toHaveLength(1);
  // The report page offers exactly the draft and the dialog.
  expect(screen.getByRole("button", { name: "Download draft" })).toBeEnabled();
});

test("must-fix items stop Finalize and each opens its filtered list or target", async () => {
  const onOpenGroup = vi.fn();
  serve({ posts: [], checklist: checklist({ ready: false, groups: blocking }), issue: issued });
  renderReports({ onOpenGroup });
  const user = userEvent.setup();
  const dialog = await openDialog(user);
  const section = await within(dialog).findByRole("region", { name: "Fix before finalizing" });
  expect(within(section).getByText(/Profile not approved/)).toBeVisible();
  expect(within(dialog).getByRole("button", { name: "Finalize" })).toBeDisabled();
  await user.click(within(dialog).getByRole("button", { name: "4 · Objectives not decided" }));
  expect(onOpenGroup).toHaveBeenCalledWith(blocking[0]);
  // The dialog closes so the list it opened is visible.
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

test("the dialog says what will be locked: the Profile version, the assessment and the documents", async () => {
  serve({ posts: [], checklist: checklist(), issue: issued });
  renderReports();
  const user = userEvent.setup();
  const dialog = await openDialog(user);
  const locked = await within(dialog).findByRole("region", { name: "What will be locked" });
  await waitFor(() => expect(locked).toHaveTextContent("Profile version 3"));
  expect(locked).toHaveTextContent("The assessment, as it is now");
  expect(locked).toHaveTextContent("The documents made from them");
  // Blockers never appear when nothing blocks.
  expect(within(dialog).queryByRole("region", { name: "Fix before finalizing" })).not.toBeInTheDocument();
});

test("warnings are shown, never block, and need nothing ticked", async () => {
  const onOpenTarget = vi.fn();
  const server: Server = { posts: [], checklist: checklist({ warnings }), issue: issued };
  serve(server);
  renderReports({ onOpenTarget });
  const user = userEvent.setup();
  const dialog = await openDialog(user);
  expect(await within(dialog).findByText("Worth a look")).toBeVisible();
  expect(within(dialog).queryByText("Fix before finalizing")).not.toBeInTheDocument();
  expect(within(dialog).getByText(/3 · Corrective work still open/)).toBeVisible();
  expect(within(dialog).getByText(/2 · Evidence due for review soon/)).toBeVisible();
  expect(within(dialog).getByText(/1 · Profile follow-up recorded/)).toBeVisible();
  expect(within(dialog).getByText(/Final endpoint count/)).toBeVisible();
  expect(within(dialog).queryAllByRole("checkbox")).toHaveLength(0);

  // Finalize is available with every warning showing, and goes in one request.
  const issue = within(dialog).getByRole("button", { name: "Finalize" });
  expect(issue).toBeEnabled();
  await user.type(within(dialog).getByLabelText(/Note/), "Issued with open corrective work.");
  await user.click(issue);
  await waitFor(() => expect(server.posts).toHaveLength(1));
  expect(server.posts[0]).toEqual({ url: "/api/projects/project-1/assessments/assessment-1/issue", body: { actor_id: "johnathan", note: "Issued with open corrective work." } });
  expect(await screen.findByText(/Finalized\. Reviewed by Johnathan/)).toBeVisible();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
});

test("a warning opens the place to look at it", async () => {
  const onOpenTarget = vi.fn();
  serve({ posts: [], checklist: checklist({ warnings }), issue: issued });
  renderReports({ onOpenTarget });
  const user = userEvent.setup();
  const dialog = await openDialog(user);
  const evidence = (await within(dialog).findByText(/2 · Evidence due for review soon/)).closest("li")!;
  await user.click(within(evidence).getByRole("button", { name: "Open" }));
  expect(onOpenTarget).toHaveBeenCalledWith("evidence");
});

test("a failed backup shows the message, nothing is issued and the dialog stays open", async () => {
  const message = "Backup failed: disk is full. Nothing was issued; the last issued version is still current.";
  const server: Server = { posts: [], checklist: checklist(), issue: () => Response.json({ detail: message }, { status: 409 }) };
  serve(server);
  renderReports();
  const user = userEvent.setup();
  const dialog = await openDialog(user);
  await user.click(await within(dialog).findByRole("button", { name: "Finalize" }));
  const alert = await within(dialog).findByRole("alert");
  expect(alert).toHaveTextContent(message);
  expect(screen.queryByText(/Finalized\. Reviewed by/)).not.toBeInTheDocument();
  expect(screen.getByRole("dialog", { name: "Finalize deliverables" })).toBeVisible();
  // The consultant can simply try again.
  expect(within(dialog).getByRole("button", { name: "Finalize" })).toBeEnabled();
  expect(server.posts).toHaveLength(1);
});

test("a refused issue because the data changed reloads what is left to fix", async () => {
  let calls = 0;
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    const url = String(input);
    if (url.endsWith("/issue-checklist")) { calls += 1; return Response.json(calls === 1 ? checklist() : checklist({ ready: false, groups: blocking })); }
    if (url.endsWith("/packages")) return Response.json([]);
    if (url.endsWith("/issue") && init?.method === "POST") return Response.json({ detail: { message: "Fix these before issuing.", groups: blocking, blockers: [] } }, { status: 409 });
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  renderReports();
  const user = userEvent.setup();
  const dialog = await openDialog(user);
  await user.click(await within(dialog).findByRole("button", { name: "Finalize" }));
  expect(await within(dialog).findByText("Fix before finalizing")).toBeVisible();
  expect(within(dialog).getByRole("alert")).toHaveTextContent("Fix these before issuing.");
  expect(within(dialog).getByRole("button", { name: "Finalize" })).toBeDisabled();
});

test("cancel closes the dialog without finalizing", async () => {
  const server: Server = { posts: [], checklist: checklist(), issue: issued };
  serve(server);
  renderReports();
  const user = userEvent.setup();
  const dialog = await openDialog(user);
  await user.click(within(dialog).getByRole("button", { name: "Cancel" }));
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(server.posts).toHaveLength(0);
});

test("the dialog says when finalizing again replaces the current final version", async () => {
  serve({ posts: [], checklist: checklist({ current_issue: { package_id: "pkg-1", issued_at: "2026-10-01T00:00:00Z" } }), issue: issued });
  renderReports();
  const user = userEvent.setup();
  const dialog = await openDialog(user);
  expect(await within(dialog).findByText("Finalizing again replaces the current final version (it will be marked Replaced).")).toBeVisible();
});

test("without a current issue the dialog does not mention replacing", async () => {
  serve({ posts: [], checklist: checklist(), issue: issued });
  renderReports();
  const user = userEvent.setup();
  const dialog = await openDialog(user);
  await within(dialog).findByRole("button", { name: "Finalize" });
  expect(within(dialog).queryByText(/replaces the current final version/)).not.toBeInTheDocument();
});

test("Download draft shows the API's message when the draft cannot be made, instead of opening JSON", async () => {
  vi.mocked(fetch).mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith("/draft")) return Response.json({ detail: "The SSP template changed; approve a new template version first" }, { status: 409 });
    if (url.endsWith("/packages")) return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  renderReports();
  const user = userEvent.setup();
  await user.click(await screen.findByRole("button", { name: "Download draft" }));
  expect(await screen.findByRole("alert")).toHaveTextContent("The SSP template changed; approve a new template version first");
  expect(screen.getByRole("button", { name: "Download draft" })).toBeEnabled();
});

test("Download draft saves the file under the name the API gives it", async () => {
  vi.mocked(fetch).mockImplementation(async (input) => {
    const url = String(input);
    if (url.endsWith("/draft")) return new Response("zip-bytes", { status: 200, headers: { "Content-Disposition": 'attachment; filename="DRAFT_Clinic.zip"' } });
    if (url.endsWith("/packages")) return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const create = vi.fn(() => "blob:draft");
  vi.stubGlobal("URL", Object.assign(URL, { createObjectURL: create, revokeObjectURL: vi.fn() }));
  const clicked: string[] = [];
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (this: HTMLAnchorElement) { clicked.push(this.download); });
  renderReports();
  const user = userEvent.setup();
  await user.click(await screen.findByRole("button", { name: "Download draft" }));
  await waitFor(() => expect(clicked).toEqual(["DRAFT_Clinic.zip"]));
  expect(create).toHaveBeenCalled();
  expect(screen.queryByRole("alert")).not.toBeInTheDocument();
});
