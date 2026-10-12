import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";

import { PoamView, type PoamItem, type PoamList } from "./views/poam/PoamView";

/** The POA&M list: counts as progress, filters, search, sort and opening a requirement. */

const eligible = { state: "eligible", reason: "1-point requirement (32 CFR 170.21(a)(2)(ii))." } as const;
const notEligible = { state: "not_eligible", reason: "5-point requirement; only 1-point requirements may be on a POA&M." } as const;
const notApplicable = { state: "not_applicable", reason: "The requirement is currently verified Met, so it is not a gap." } as const;

function item(over: Partial<PoamItem>): PoamItem {
  return {
    id: "a", record_id: "AC.L2-3.1.1", citation: "AC.L2-3.1.1", requirement_title: "Authorized Access Control",
    work_area: "AC", requirement_status: "Not Met", title: "Rebuild the user list", description: "", status: "Open",
    status_label: "Open", group: "open", linked: true, status_rank: 1, weight: 5, eligibility: notEligible, closure_rationale: null, closed_at: null,
    updated_at: "2026-10-12T00:00:00Z", ...over,
  };
}

const cmmc: PoamList = {
  variant: "cmmc", item_label: "POA&M item", scored: true,
  items: [
    item({ id: "1", status: "Ready for Validation", status_label: "Ready for validation", status_rank: 4, title: "Review session lock" , record_id: "AC.L2-3.1.10", citation: "AC.L2-3.1.10", requirement_title: "Session Lock", weight: 1, eligibility: eligible }),
    item({ id: "2" }),
    item({ id: "3", status: "Draft", status_label: "Draft", status_rank: 0, group: "draft", record_id: "AU.L2-3.3.2", citation: "AU.L2-3.3.2", requirement_title: "User Accountability", work_area: "AU", title: "Turn on audit logging", weight: 3, eligibility: notEligible }),
    item({ id: "4", status: "Closed", status_label: "Closed", status_rank: 5, group: "closed", record_id: "AC.L2-3.1.7", citation: "AC.L2-3.1.7", requirement_title: "Privileged Functions", title: "Restrict admin tools", weight: null, eligibility: notApplicable, closure_rationale: "Control restored and verified." }),
    item({ id: "5", status: "Withdrawn", status_label: "Withdrawn", status_rank: 6, group: "withdrawn", record_id: "AC.L2-3.1.8", citation: "AC.L2-3.1.8", requirement_title: "Unsuccessful Logon Attempts", title: "Duplicate entry", weight: 1, eligibility: eligible }),
  ],
  counts: { open: 3, draft: 1, closed: 1, withdrawn: 1, ready_for_validation: 1, total: 5 },
  work_areas: ["AC", "AU"],
  not_met_count: 4,
  not_met_without_plan: { count: 3, requirement_ids: ["x", "y", "z"], not_needed_count: 0 },
  missing_fields: ["owner", "due_date"],
};

const hipaa: PoamList = {
  variant: "hipaa", item_label: "corrective action", scored: false,
  items: [item({ id: "h1", record_id: "164.308(a)(1)(ii)(B)", citation: "164.308(a)(1)(ii)(B)", requirement_title: "Risk management", work_area: "security", title: "Document the risk plan", weight: null, eligibility: { state: "not_applicable", reason: "" } })],
  counts: { open: 1, draft: 0, closed: 0, withdrawn: 0, ready_for_validation: 0, total: 1 },
  work_areas: ["security"],
  not_met_count: 5,
  not_met_without_plan: { count: 4, requirement_ids: [], not_needed_count: 0 },
  missing_fields: ["owner", "due_date"],
};

function serve(body: PoamList) {
  vi.stubGlobal("fetch", vi.fn(async () => Response.json(body)));
}

function rowsOf(): string[] {
  return screen.getAllByRole("row").slice(1).map((row) => within(row).getByRole("button").textContent ?? "");
}

beforeEach(() => serve(cmmc));
afterEach(() => vi.unstubAllGlobals());

test("shows counts as progress and the not-on-a-POA&M figure, without blocker language", async () => {
  render(<PoamView projectId="p1" assessmentId="a1" onOpenRecord={() => {}} />);
  expect(await screen.findByText("3 open (1 draft) · 1 closed · 1 withdrawn")).toBeVisible();
  expect(screen.getByText("3 Not Met without a POA&M")).toBeVisible();
  expect(screen.queryByText(/block/i)).toBeNull();
  expect(vi.mocked(fetch)).toHaveBeenCalledWith("/api/projects/p1/assessments/a1/poam-items", expect.anything());
});

test("lists every item with plain status labels, points, eligibility with reason and the closure rationale", async () => {
  render(<PoamView projectId="p1" assessmentId="a1" onOpenRecord={() => {}} />);
  await screen.findByText("Review session lock");
  expect(rowsOf()).toEqual(["AC.L2-3.1.10", "AC.L2-3.1.1", "AU.L2-3.3.2", "AC.L2-3.1.7", "AC.L2-3.1.8"]);
  expect(within(screen.getByRole("table")).getByText("Ready for validation")).toBeVisible();
  expect(screen.getByText("Closed: Control restored and verified.")).toBeVisible();
  expect(screen.getAllByText("5-point requirement; only 1-point requirements may be on a POA&M.")).toHaveLength(2);
  expect(screen.getAllByText("Eligible").length).toBeGreaterThan(0);
  expect(screen.getByText(/Owner and due date are not recorded/)).toBeVisible();
});

test("filters by status, eligibility and family, and searches", async () => {
  const user = userEvent.setup();
  render(<PoamView projectId="p1" assessmentId="a1" onOpenRecord={() => {}} />);
  await screen.findByText("Review session lock");

  await user.selectOptions(screen.getByLabelText("Filter by status"), "Closed");
  expect(rowsOf()).toEqual(["AC.L2-3.1.7"]);
  await user.selectOptions(screen.getByLabelText("Filter by status"), "all");

  await user.selectOptions(screen.getByLabelText("Filter by eligibility"), "not_eligible");
  expect(rowsOf()).toEqual(["AC.L2-3.1.1", "AU.L2-3.3.2"]);
  await user.selectOptions(screen.getByLabelText("Filter by eligibility"), "all");

  await user.selectOptions(screen.getByLabelText("Filter by work area"), "AU");
  expect(rowsOf()).toEqual(["AU.L2-3.3.2"]);
  await user.selectOptions(screen.getByLabelText("Filter by work area"), "all");

  await user.type(screen.getByLabelText("Search items"), "audit");
  expect(rowsOf()).toEqual(["AU.L2-3.3.2"]);
  expect(screen.getByText("Showing 1 of 5")).toBeVisible();
  await user.clear(screen.getByLabelText("Search items"));
  await user.type(screen.getByLabelText("Search items"), "nothing like this");
  expect(screen.getByText("Nothing matches these filters.")).toBeVisible();
});

test("sorts by points, highest first", async () => {
  const user = userEvent.setup();
  render(<PoamView projectId="p1" assessmentId="a1" onOpenRecord={() => {}} />);
  await screen.findByText("Review session lock");
  await user.selectOptions(screen.getByLabelText("Sort by"), "points");
  expect(rowsOf()).toEqual(["AC.L2-3.1.1", "AU.L2-3.3.2", "AC.L2-3.1.10", "AC.L2-3.1.8", "AC.L2-3.1.7"]);
});

test("clicking a row, or its citation, opens that requirement", async () => {
  const user = userEvent.setup();
  const open = vi.fn();
  render(<PoamView projectId="p1" assessmentId="a1" onOpenRecord={open} />);
  await user.click(await screen.findByText("Turn on audit logging"));
  expect(open).toHaveBeenLastCalledWith("AU.L2-3.3.2");
  await user.click(screen.getByRole("button", { name: "Open AC.L2-3.1.7" }));
  expect(open).toHaveBeenLastCalledWith("AC.L2-3.1.7");
  expect(open).toHaveBeenCalledTimes(2);
});

test("HIPAA shows corrective actions with no points or eligibility columns", async () => {
  serve(hipaa);
  render(<PoamView projectId="p1" assessmentId="a1" onOpenRecord={() => {}} />);
  expect(await screen.findByRole("heading", { name: "Corrective actions" })).toBeVisible();
  expect(screen.getByText("1 open · 0 closed")).toBeVisible();
  expect(screen.getByText("4 Not Met without an open corrective action")).toBeVisible();
  expect(screen.queryByText("Points")).toBeNull();
  expect(screen.queryByText("32 CFR 170.21")).toBeNull();
  expect(screen.queryByLabelText("Filter by eligibility")).toBeNull();
  expect(screen.getByRole("option", { name: "Security Rule" })).toBeInTheDocument();
});

test("an empty project says so, and a failed load shows the error", async () => {
  serve({ ...cmmc, items: [], counts: { open: 0, draft: 0, closed: 0, withdrawn: 0, ready_for_validation: 0, total: 0 }, not_met_count: 2, not_met_without_plan: { count: 0, requirement_ids: [], not_needed_count: 0 } });
  const { unmount } = render(<PoamView projectId="p1" assessmentId="a1" onOpenRecord={() => {}} />);
  expect(await screen.findByText(/No POA&M items yet/)).toBeVisible();
  expect(screen.getByText("Every Not Met requirement has a POA&M")).toBeVisible();
  unmount();
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ detail: "Assessment not found for project" }, { status: 404 })));
  render(<PoamView projectId="p1" assessmentId="a1" onOpenRecord={() => {}} />);
  await waitFor(() => expect(screen.getByText("Assessment not found for project")).toBeVisible());
});

test("the gap pill opens Assessments narrowed to those records", async () => {
  const user = userEvent.setup();
  const group = vi.fn();
  render(<PoamView projectId="p1" assessmentId="a1" onOpenRecord={() => {}} onOpenGap={group} />);
  await user.click(await screen.findByRole("button", { name: "3 Not Met without a POA&M" }));
  expect(group).toHaveBeenCalledWith("Not Met without a POA&M", ["x", "y", "z"]);
});

test("sorting by status follows the workflow order", async () => {
  const user = userEvent.setup();
  render(<PoamView projectId="p1" assessmentId="a1" onOpenRecord={() => {}} />);
  await screen.findByText("Review session lock");
  await user.selectOptions(screen.getByLabelText("Sort by"), "status");
  expect(rowsOf()).toEqual(["AU.L2-3.3.2", "AC.L2-3.1.1", "AC.L2-3.1.10", "AC.L2-3.1.7", "AC.L2-3.1.8"]);
});

test("search covers what the row shows, not hidden text", async () => {
  const user = userEvent.setup();
  serve({ ...cmmc, items: [{ ...cmmc.items[1], description: "secret hidden words" }] });
  render(<PoamView projectId="p1" assessmentId="a1" onOpenRecord={() => {}} />);
  await screen.findByText("Rebuild the user list");
  await user.type(screen.getByLabelText("Search items"), "hidden");
  expect(screen.getByText("Nothing matches these filters.")).toBeVisible();
});

test("HIPAA wording never says every Not Met has an action when some are Not needed or none are Not Met", async () => {
  const none = { ...hipaa, not_met_count: 0, not_met_without_plan: { count: 0, requirement_ids: [], not_needed_count: 0 } };
  serve(none);
  const first = render(<PoamView projectId="p1" assessmentId="a1" onOpenRecord={() => {}} />);
  await screen.findByRole("heading", { name: "Corrective actions" });
  expect(screen.queryByText(/Every Not Met/)).toBeNull();
  expect(screen.queryByText(/without an open corrective action/)).toBeNull();
  first.unmount();
  serve({ ...hipaa, not_met_without_plan: { count: 2, requirement_ids: ["a", "b"], not_needed_count: 1 } });
  const second = render(<PoamView projectId="p1" assessmentId="a1" onOpenRecord={() => {}} />);
  expect(await screen.findByText("2 Not Met without an open corrective action (1 marked Not needed)")).toBeVisible();
  second.unmount();
  serve({ ...hipaa, not_met_without_plan: { count: 0, requirement_ids: [], not_needed_count: 1 } });
  render(<PoamView projectId="p1" assessmentId="a1" onOpenRecord={() => {}} />);
  expect(await screen.findByText("No Not Met without an open corrective action (1 marked Not needed)")).toBeVisible();
});

test("an action no longer linked to a record is still listed, without a row link", async () => {
  const user = userEvent.setup();
  const open = vi.fn();
  serve({ ...hipaa, items: [item({ id: "o", record_id: null, linked: false, citation: "Not linked to a record", requirement_title: "", work_area: "", title: "Orphaned action" })] });
  render(<PoamView projectId="p1" assessmentId="a1" onOpenRecord={open} />);
  await user.click(await screen.findByText("Orphaned action"));
  expect(screen.getByText("Not linked to a record")).toBeVisible();
  expect(open).not.toHaveBeenCalled();
});
