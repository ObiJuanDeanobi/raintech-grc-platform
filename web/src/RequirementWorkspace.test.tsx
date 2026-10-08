import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import { Workspace } from "./App";
import { clientProjectsFixture } from "./activeAssessmentFixtures";
import { parseObjectiveNotes, serializeObjectiveNotes } from "./lib/objectiveNotes";

/**
 * Issue #140: the CMMC assessment is worked one requirement at a time, with
 * every objective decided from the requirement view. A small in-memory API
 * keeps determinations, notes, evidence and the SSP so each test sees the
 * server's answer, not the component's optimism.
 */

const MET_RULE = "Met requires mapped evidence or a documented interview/observation";

const requirements = [
  { id: "AC.L2-3.1.1", title: "Authorized Access Control", family: "Access Control", objectives: ["a", "b"] },
  { id: "AC.L2-3.1.2", title: "Transaction & Function Control", family: "Access Control", objectives: ["a", "b"] },
  { id: "AU.L2-3.3.1", title: "System Auditing", family: "Audit and Accountability", objectives: ["a"] },
];

const workList = requirements.flatMap((requirement, index) => [
  {
    record_id: requirement.id, citation: requirement.id, title: requirement.title, work_area: requirement.family,
    record_type: "requirement", parent_id: null, designation: null, sort_order: index * 10, editable_determination: false,
  },
  ...requirement.objectives.map((letter, offset) => ({
    record_id: `${requirement.id}${letter}`, citation: `${requirement.id}[${letter}]`, title: `Objective [${letter}]`,
    work_area: requirement.family, record_type: "objective", parent_id: requirement.id, designation: null,
    sort_order: index * 10 + offset + 1, editable_determination: true,
  })),
]);

const objectiveText = (id: string) => `Objective text for ${id}.`;

const readiness = {
  project_id: "project-1", state: "Intake complete", assessment_exists: true,
  supported_states: ["Intake started", "Intake complete"], allowed_next_states: [],
  follow_up_work_required_states: [], follow_up_work_required_when_unresolved_required_fields: true,
  assessment_entry_allowed: true, assessment_entry_blocking_reasons: [], profile_completion_blocking_reasons: [],
  current_details: { unresolved_required_fields: [], follow_up_work: "", reviewed_by: "", approval_evidence: "" },
};

interface ServerOptions {
  statuses?: Record<string, string>;
  notes?: Record<string, string>;
  ssp?: boolean;
}

function derived(statuses: string[]): string {
  if (statuses.includes("Not Met")) return "Not Met";
  if (statuses.includes("Pending")) return "Pending";
  if (statuses.length > 0 && statuses.every((status) => status === "Met")) return "Met";
  return "";
}

function cmmcServer(options: ServerOptions = {}) {
  const statuses: Record<string, string> = { ...options.statuses };
  const observations: Record<string, string> = {};
  const notes: Record<string, string> = { ...options.notes };
  const evidence: Record<string, number> = {};
  const writes: { method: string; url: string; body: string }[] = [];
  let scoreReads = 0;
  let sspStatement = "Drafted from notes.";
  let sspVersion = 1;
  const refuseNextDetermination: { reason: string | null } = { reason: null };

  const objectivesOf = (requirementId: string) => workList.filter((record) => record.parent_id === requirementId);
  const requirementStatus = (requirementId: string) => derived(objectivesOf(requirementId).map((o) => statuses[o.record_id] ?? ""));
  const determination = (recordId: string, isDerived = false) => ({
    status: isDerived ? requirementStatus(recordId) : statuses[recordId] ?? "",
    derived: isDerived, na_rationale: "", addressable_disposition: null, disposition_reason: "",
    interview_observation: observations[recordId] ?? "",
  });
  const recordStates = () => Object.fromEntries(workList.map((record) => [record.record_id, {
    status: record.parent_id ? statuses[record.record_id] ?? "" : requirementStatus(record.record_id),
    evidence_count: evidence[record.record_id] ?? 0,
    open_poam_count: 0,
  }]));
  const decidedCount = () => Object.values(statuses).filter((status) => status === "Met" || status === "Not Met").length;
  const evidenceRows = (recordId: string) => Array.from({ length: evidence[recordId] ?? 0 }, (_, index) => ({
    mapping_id: `map-${recordId}-${index}`, artifact_id: "art-1", name: "synthetic-policy.txt", relative_path: "p",
    rationale: "Synthetic policy.", review_state: "Not reviewed", shared_record_count: 1, version_id: "v1",
    version_project_id: "project-1", version_number: 1, sha256: "abc",
  }));
  const recordDetail = (recordId: string) => {
    const record = workList.find((item) => item.record_id === recordId)!;
    const isRequirement = !record.parent_id;
    return {
      record: { ...record, regulation_text: isRequirement ? `Requirement text for ${recordId}.` : objectiveText(recordId) },
      determination: determination(recordId, isRequirement),
      parent: null, parent_prompts: [], context_prompts: [], prompts: [], no_prompt_explanation: null,
      children: isRequirement
        ? objectivesOf(recordId).map((objective) => ({ ...objective, regulation_text: objectiveText(objective.record_id), determination: determination(objective.record_id) }))
        : [],
      note: notes[recordId] ?? "",
      evidence: evidenceRows(recordId),
      position: { current: 1, total: workList.length, previous_record_id: null, next_record_id: null },
      practitioner_guidance: null,
    };
  };
  const sspView = () => ({
    id: "ssp-1", template_version: "cmmc-ssp-v1", source_sha256: "abc",
    source: { requirements: requirements.map((r) => ({ record_id: r.id, citation: r.id, status: "Implemented", poam_items: [] })) },
    versions: Array.from({ length: sspVersion }, (_, index) => ({ id: `v${index + 1}`, version_number: index + 1, note: "", created_at: "2026-10-08" })),
    latest: {
      id: `v${sspVersion}`, version_number: sspVersion,
      content: { system_description: "", environment_narrative: "", requirements: Object.fromEntries(requirements.map((r) => [r.id, { implementation: r.id === "AC.L2-3.1.1" ? sspStatement : "" }])) },
    },
    missing_for_approval: ["system_description"], approval: null,
  });

  vi.mocked(fetch).mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (method !== "GET") writes.push({ method, url, body: String(init?.body ?? "") });
    if (url.endsWith("/profile-readiness")) return Response.json(readiness);
    if (url === "/api/projects/project-1/assessment") {
      return Response.json({
        id: "assessment-1",
        project: { id: "project-1", name: "CMMC 2026", client_id: "client-1", client_name: "Synthetic Defense" },
        framework: {
          id: "cmmc-l2", name: "CMMC Level 2", record_count: workList.length, walkthrough_record_count: workList.length,
          prompt_count: 0, determination_record_count: 5,
          declarations: {
            record_shape: { hierarchy: ["requirement", "objective"], determination_rule: "records_without_children" },
            rollup_rule: { precedence: ["Not Met", "Pending"], blank_children_prevent_met: true, satisfied_child_statuses: ["Met"], satisfied_rollup_status: "Met", blank_status: "" },
            status_set: ["", "Met", "Not Met", "Pending"],
            presentation_mode: "requirement_with_objectives",
            scoring: { authority: "32 CFR 170.24", requirements: Object.fromEntries(requirements.map((r) => [r.id, { rule: "fixed", points: 5, source: "32 CFR 170.24" }])) },
          },
        },
        progress: { resolved_determination_count: decidedCount(), determination_record_count: 5 },
        work_list: workList, record_index: workList, record_states: recordStates(),
      });
    }
    const determinationMatch = url.match(/\/determinations\/([^/]+)$/);
    if (determinationMatch && method === "PUT") {
      const recordId = decodeURIComponent(determinationMatch[1]);
      const body = JSON.parse(String(init?.body));
      if (refuseNextDetermination.reason) {
        const reason = refuseNextDetermination.reason;
        refuseNextDetermination.reason = null;
        return Response.json({ detail: reason }, { status: 422 });
      }
      if (body.status === "Met" && !body.interview_observation?.trim() && !evidence[recordId]) {
        return Response.json({ detail: MET_RULE }, { status: 422 });
      }
      statuses[recordId] = body.status;
      observations[recordId] = body.interview_observation ?? "";
      return Response.json(determination(recordId));
    }
    const noteMatch = url.match(/\/records\/([^/]+)\/note$/);
    if (noteMatch && method === "PUT") {
      const recordId = decodeURIComponent(noteMatch[1]);
      notes[recordId] = JSON.parse(String(init?.body)).note;
      return Response.json({ note: notes[recordId], updated_at: "now" });
    }
    const recordMatch = url.match(/\/records\/([^/]+)$/);
    if (recordMatch) return Response.json(recordDetail(decodeURIComponent(recordMatch[1])));
    if (url.endsWith("/cmmc-score")) {
      scoreReads += 1;
      const notMet = requirements.filter((r) => requirementStatus(r.id) === "Not Met");
      const unscored = requirements.filter((r) => !["Met", "Not Met"].includes(requirementStatus(r.id)));
      return Response.json({
        authority: "32 CFR 170.24", maximum_score: 110, minimum_score: -203, score: 110 - 5 * notMet.length,
        complete: unscored.length === 0, blockers: [],
        deductions: notMet.map((r) => ({ record_id: r.id, citation: r.id, title: r.title, points: 5, source: "x", conditional_poam_allowed: true })),
        unscored: unscored.map((r) => ({ record_id: r.id, status: requirementStatus(r.id) || "Blank" })),
        partial_inputs_needed: [], partial_implementations: {}, follow_up: [],
        conditional: { source: "32 CFR 170.21", score_ratio: 1, eligible: false },
      });
    }
    if (url.endsWith("/ssp") && method === "GET") return Response.json(options.ssp ? sspView() : null);
    if (url.endsWith("/ssp/ssp-1") && method === "PUT") {
      const body = JSON.parse(String(init?.body));
      sspStatement = body.requirements?.["AC.L2-3.1.1"] ?? sspStatement;
      sspVersion += 1;
      return Response.json(sspView());
    }
    if (url.endsWith("/finding")) return Response.json(null);
    if (url.includes("/evidence")) return Response.json([]);
    if (url === "/api/backups") return Response.json({ warning: null, backups: [] });
    return Response.json({ detail: "not found" }, { status: 404 });
  });

  return {
    statuses, notes, evidence, writes, refuseNextDetermination,
    scoreReads: () => scoreReads,
    determinationWrites: () => writes.filter((write) => write.url.includes("/determinations/")),
  };
}

function renderWorkspace() {
  return render(
    <Workspace clients={clientProjectsFixture()} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} />,
  );
}

function objectiveRow(citation: string) {
  return screen.getByRole("listitem", { name: `Objective ${citation}` });
}

function pressed(citation: string): string[] {
  return within(objectiveRow(citation))
    .getAllByRole("button")
    .filter((button) => button.getAttribute("aria-pressed") === "true")
    .map((button) => button.textContent ?? "");
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

test("opens on the first requirement with an undecided objective and shows family counts and markers", async () => {
  const server = cmmcServer({ statuses: { "AC.L2-3.1.1a": "Met", "AC.L2-3.1.1b": "Not Met" } });
  server.evidence["AC.L2-3.1.1a"] = 1;
  renderWorkspace();

  expect(await screen.findByRole("heading", { level: 1, name: "Transaction & Function Control" })).toBeVisible();
  const list = screen.getByRole("navigation", { name: "Requirements by family" });
  expect(within(list).getByRole("button", { name: /^Access Control/ })).toHaveTextContent("2/4");
  expect(within(list).getByLabelText("2 of 4 objectives decided")).toBeVisible();
  const done = within(list).getByRole("button", { name: /Authorized Access Control/ });
  expect(done).toHaveTextContent("2/2");
  expect(done).toHaveTextContent("No POA&M");
  expect(within(done).getByLabelText("Evidence on 1")).toBeVisible();
  expect(within(list).getByRole("button", { name: /Transaction & Function Control/ })).toHaveAttribute("aria-current", "true");
  // Objectives are not rows in the list any more.
  expect(within(list).queryByText("Objective [a]")).not.toBeInTheDocument();
  // Only CMMC statuses are offered, one click each.
  const group = within(objectiveRow("AC.L2-3.1.2[a]")).getByRole("group", { name: "Determination for AC.L2-3.1.2[a]" });
  expect(within(group).getAllByRole("button").map((button) => button.textContent)).toEqual(["Met", "Not Met", "Pending"]);
  expect(screen.queryByRole("button", { name: "N/A" })).not.toBeInTheDocument();
});

test("decides every objective with the keyboard only, updates the score, and moves between requirements", async () => {
  const server = cmmcServer();
  server.evidence["AC.L2-3.1.1a"] = 1;
  renderWorkspace();
  await screen.findByRole("heading", { level: 1, name: "Authorized Access Control" });
  expect(screen.getByLabelText("Keyboard shortcuts")).toHaveTextContent("M Met");
  const score = await screen.findByRole("region", { name: "Official CMMC score" });
  expect(score).toHaveTextContent("110");
  const readsBefore = server.scoreReads();
  const user = userEvent.setup();

  await user.keyboard("m");
  await waitFor(() => expect(server.statuses["AC.L2-3.1.1a"]).toBe("Met"));
  await user.keyboard("{ArrowDown}");
  expect(objectiveRow("AC.L2-3.1.1[b]")).toHaveAttribute("aria-current", "true");
  await user.keyboard("n");
  await waitFor(() => expect(server.statuses["AC.L2-3.1.1b"]).toBe("Not Met"));
  // The derived status and the official score follow without a reload.
  expect(await screen.findByText("Derived · Not Met")).toBeVisible();
  await waitFor(() => expect(server.scoreReads()).toBeGreaterThan(readsBefore));
  await waitFor(() => expect(screen.getByRole("region", { name: "Official CMMC score" })).toHaveTextContent("105"));
  expect(pressed("AC.L2-3.1.1[a]")).toEqual(["Met"]);
  expect(pressed("AC.L2-3.1.1[b]")).toEqual(["Not Met"]);

  // Keys are not hijacked while typing.
  await user.click(screen.getByRole("button", { name: "Notes for AC.L2-3.1.1[b]" }));
  const examine = await screen.findByRole("textbox", { name: "Examine notes for AC.L2-3.1.1[b]" });
  await user.type(examine, "pjm");
  expect(examine).toHaveValue("pjm");
  expect(server.statuses["AC.L2-3.1.1b"]).toBe("Not Met");
  fireEvent.blur(examine);
  (document.activeElement as HTMLElement | null)?.blur();
  await waitFor(() => expect(server.notes["AC.L2-3.1.1b"]).toBe("Examine: pjm"));
  await waitFor(() => expect(screen.getByText("Saved")).toBeInTheDocument());

  await user.keyboard("j");
  expect(await screen.findByRole("heading", { level: 1, name: "Transaction & Function Control" })).toBeVisible();
  await user.keyboard("p");
  await waitFor(() => expect(server.statuses["AC.L2-3.1.2a"]).toBe("Pending"));
  await user.keyboard("{ArrowDown}p");
  await waitFor(() => expect(server.statuses["AC.L2-3.1.2b"]).toBe("Pending"));
  await user.keyboard("]");
  expect(await screen.findByRole("heading", { level: 1, name: "System Auditing" })).toBeVisible();
  await user.keyboard("[[");
  expect(await screen.findByRole("heading", { level: 1, name: "Transaction & Function Control" })).toBeVisible();
  await user.keyboard("k");
  expect(await screen.findByRole("heading", { level: 1, name: "Authorized Access Control" })).toBeVisible();
  // Every determination was a single PUT for its objective.
  expect(server.determinationWrites().map((write) => decodeURIComponent(write.url.split("/").pop()!))).toEqual([
    "AC.L2-3.1.1a", "AC.L2-3.1.1b", "AC.L2-3.1.2a", "AC.L2-3.1.2b",
  ]);
});

test("a refused Met shows the API reason and the last saved status, and Retry succeeds once evidence exists", async () => {
  const server = cmmcServer({ statuses: { "AC.L2-3.1.1a": "Pending" } });
  renderWorkspace();
  await screen.findByRole("heading", { level: 1, name: "Authorized Access Control" });
  const user = userEvent.setup();

  await user.click(within(objectiveRow("AC.L2-3.1.1[a]")).getByRole("button", { name: "Met" }));
  const row = objectiveRow("AC.L2-3.1.1[a]");
  expect(await within(row).findByText(new RegExp(MET_RULE))).toBeVisible();
  expect(row).toHaveTextContent("Saved status is still Pending");
  expect(pressed("AC.L2-3.1.1[a]")).toEqual(["Pending"]);
  expect(within(row).getByRole("button", { name: "Met" })).toHaveClass("attempted");
  expect(server.statuses["AC.L2-3.1.1a"]).toBe("Pending");

  server.evidence["AC.L2-3.1.1a"] = 1;
  await user.click(within(row).getByRole("button", { name: "Retry AC.L2-3.1.1[a] determination" }));
  await waitFor(() => expect(server.statuses["AC.L2-3.1.1a"]).toBe("Met"));
  await waitFor(() => expect(pressed("AC.L2-3.1.1[a]")).toEqual(["Met"]));
  expect(within(objectiveRow("AC.L2-3.1.1[a]")).queryByText(new RegExp(MET_RULE))).not.toBeInTheDocument();
  expect(await screen.findByText("Saved")).toBeInTheDocument();
});

test("per-objective examine, interview and test notes autosave as labelled text and load back", async () => {
  const server = cmmcServer({ notes: { "AC.L2-3.1.1b": "Interview: Synthetic IT lead." } });
  renderWorkspace();
  await screen.findByRole("heading", { level: 1, name: "Authorized Access Control" });
  const user = userEvent.setup();

  await user.click(screen.getByRole("button", { name: "Notes for AC.L2-3.1.1[a]" }));
  const examine = await screen.findByRole("textbox", { name: "Examine notes for AC.L2-3.1.1[a]" });
  await user.type(examine, "Synthetic access policy v3.");
  const test = screen.getByRole("textbox", { name: "Test notes for AC.L2-3.1.1[a]" });
  await user.click(test);
  await waitFor(() => expect(server.notes["AC.L2-3.1.1a"]).toBe("Examine: Synthetic access policy v3."));
  await user.type(test, "Disabled account refused.");
  fireEvent.blur(test);
  await waitFor(() => expect(server.notes["AC.L2-3.1.1a"]).toBe("Examine: Synthetic access policy v3.\nTest: Disabled account refused."));

  await user.click(screen.getByRole("button", { name: "Notes for AC.L2-3.1.1[b]" }));
  expect(await screen.findByRole("textbox", { name: "Interview notes for AC.L2-3.1.1[b]" })).toHaveValue("Synthetic IT lead.");
});

test("the implementation statement feeds the SSP: requirement note before generation, one explicit SSP version after", async () => {
  const before = cmmcServer();
  const { unmount } = renderWorkspace();
  const statement = await screen.findByRole("textbox", { name: "Implementation statement for AC.L2-3.1.1" });
  const user = userEvent.setup();
  await user.type(statement, "Accounts come only from the HR ticket.");
  expect(before.writes.filter((write) => write.url.includes("/ssp"))).toHaveLength(0);
  fireEvent.blur(statement);
  await waitFor(() => expect(before.notes["AC.L2-3.1.1"]).toBe("Accounts come only from the HR ticket."));
  expect(before.writes.filter((write) => write.url.endsWith("/records/AC.L2-3.1.1/note"))).toHaveLength(1);
  unmount();

  const after = cmmcServer({ ssp: true });
  renderWorkspace();
  const sspStatement = await screen.findByRole("textbox", { name: "Implementation statement for AC.L2-3.1.1" });
  expect(sspStatement).toHaveValue("Drafted from notes.");
  await user.clear(sspStatement);
  await user.type(sspStatement, "Quarterly account review.");
  fireEvent.blur(sspStatement);
  expect(after.writes.filter((write) => write.url.endsWith("/ssp/ssp-1"))).toHaveLength(0);
  await user.click(screen.getByRole("button", { name: "Save to SSP draft" }));
  await waitFor(() => expect(after.writes.filter((write) => write.url.endsWith("/ssp/ssp-1"))).toHaveLength(1));
  const body = JSON.parse(after.writes.find((write) => write.url.endsWith("/ssp/ssp-1"))!.body);
  expect(body.requirements).toEqual({ "AC.L2-3.1.1": "Quarterly account review." });
  expect(await screen.findByText(/SSP version 2/)).toBeVisible();
});

test("the interview view walks one objective at a time over the same data", async () => {
  const server = cmmcServer();
  renderWorkspace();
  await screen.findByRole("heading", { level: 1, name: "Authorized Access Control" });
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Interview view" }));

  expect(screen.getByText("Objective 1 of 2")).toBeVisible();
  expect(objectiveRow("AC.L2-3.1.1[a]")).not.toHaveClass("interview-hidden");
  expect(objectiveRow("AC.L2-3.1.1[b]")).toHaveClass("interview-hidden");
  expect(screen.getByRole("textbox", { name: "Interview or observation record for AC.L2-3.1.1[a]" })).toBeInTheDocument();
  await user.type(screen.getByRole("textbox", { name: "Interview or observation record for AC.L2-3.1.1[a]" }), "Synthetic: observed the admin console.");
  await user.click(within(objectiveRow("AC.L2-3.1.1[a]")).getByRole("button", { name: "Met" }));
  await waitFor(() => expect(server.statuses["AC.L2-3.1.1a"]).toBe("Met"));

  await user.click(screen.getByRole("button", { name: /Next objective/ }));
  expect(screen.getByText("Objective 2 of 2")).toBeVisible();
  expect(objectiveRow("AC.L2-3.1.1[b]")).not.toHaveClass("interview-hidden");
  expect(objectiveRow("AC.L2-3.1.1[a]")).toHaveClass("interview-hidden");

  await user.click(screen.getByRole("button", { name: "Requirement view" }));
  expect(objectiveRow("AC.L2-3.1.1[a]")).not.toHaveClass("interview-hidden");
  expect(pressed("AC.L2-3.1.1[a]")).toEqual(["Met"]);
});

test("objective notes round-trip through the labelled format", () => {
  const notes = parseObjectiveNotes("Older free text.\nExamine: Policy v3.\nsecond line\nTest: Disabled login.");
  expect(notes).toEqual({ general: "Older free text.", examine: "Policy v3.\nsecond line", interview: "", test: "Disabled login." });
  expect(parseObjectiveNotes(serializeObjectiveNotes(notes))).toEqual(notes);
  expect(serializeObjectiveNotes({ general: "", examine: "", interview: " ", test: "" })).toBe("");
});
