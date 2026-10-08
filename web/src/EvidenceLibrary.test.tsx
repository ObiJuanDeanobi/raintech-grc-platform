import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import { Workspace } from "./App";
import { clientProjectsFixture, cmmcScoreFixture } from "./activeAssessmentFixtures";
import { artifactLabel, shortHash } from "./lib/evidence";
import type { EvidenceLibrary, LibraryArtifact } from "./types";
import { EvidenceLibraryView } from "./views/evidence/EvidenceLibraryView";

/**
 * Issue #142: an evidence library view, one artifact linked to several
 * objectives in one act, and staleness shown where it changes verification.
 * Synthetic data only.
 */

const FULL_HASH = "9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08";

function artifact(overrides: Partial<LibraryArtifact>): LibraryArtifact {
  return {
    id: "art-1", name: "access-policy.pdf", created_at: "2026-09-01", review_date: null,
    version_id: "v1", version_number: 1, sha256: FULL_HASH, version_created_at: "2026-09-01",
    review_status: "current", days_until_review: null, used_by: [], other_use_count: 0,
    ...overrides,
  };
}

const libraryFixture: EvidenceLibrary = {
  today: "2026-10-08",
  lead_days: 30,
  assessment_id: "assessment-1",
  artifacts: [
    artifact({ id: "art-current", name: "network-diagram.png", review_date: "2027-03-01", days_until_review: 144 }),
    artifact({
      id: "art-due", name: "user-access-review.xlsx", review_date: "2026-10-20", review_status: "due_soon", days_until_review: 12,
      used_by: [{ mapping_id: "m-1", artifact_id: "art-due", assessment_id: "assessment-1", record_id: "AC.L2-3.1.1a", citation: "AC.L2-3.1.1[a]", title: "Objective [a]", parent_id: "AC.L2-3.1.1", rationale: "Quarterly review.", review_state: "Not reviewed", version_number: 1 }],
    }),
    artifact({
      id: "art-stale", name: "access-policy.pdf", review_date: "2026-09-30", review_status: "stale", days_until_review: -8, version_number: 2,
      used_by: [
        { mapping_id: "m-2", artifact_id: "art-stale", assessment_id: "assessment-1", record_id: "AC.L2-3.1.1a", citation: "AC.L2-3.1.1[a]", title: "Objective [a]", parent_id: "AC.L2-3.1.1", rationale: "Section 2 lists authorized users.", review_state: "Not reviewed", version_number: 2 },
        { mapping_id: "m-3", artifact_id: "art-stale", assessment_id: "assessment-1", record_id: "AC.L2-3.1.2b", citation: "AC.L2-3.1.2[b]", title: "Objective [b]", parent_id: "AC.L2-3.1.2", rationale: "Section 3 limits transactions.", review_state: "Not reviewed", version_number: 1 },
      ],
    }),
  ],
};

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

function libraryServer() {
  const writes: { method: string; url: string; body: BodyInit | null | undefined }[] = [];
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (method !== "GET") writes.push({ method, url, body: init?.body });
    if (url.endsWith("/evidence-library")) return Response.json(libraryFixture);
    if (url.endsWith("/evidence?binned=true")) {
      return Response.json([{ id: "art-old", name: "old-policy.pdf", shared_record_count: 0, version_number: 1, sha256: "x", deleted_at: "2026-10-01" }]);
    }
    return Response.json({});
  });
  return writes;
}

test("the Evidence view lists every artifact with its review status, short hash and uses", async () => {
  libraryServer();
  const onOpenRecord = vi.fn();
  render(<EvidenceLibraryView projectId="project-1" onOpenRecord={onOpenRecord} onChanged={vi.fn()} />);
  const table = await screen.findByRole("table");
  const rows = within(table).getAllByRole("row").slice(1);
  expect(rows).toHaveLength(3);
  expect(within(rows[0]).getByText("Current")).toBeVisible();
  expect(within(rows[1]).getByText("Due soon")).toBeVisible();
  expect(within(rows[1]).getByText("Review due in 12 days (2026-10-20)")).toBeVisible();
  expect(within(rows[2]).getByText("Stale")).toBeVisible();
  expect(within(rows[2]).getByText("Review overdue since 2026-09-30")).toBeVisible();
  // Short hash in the label, the full SHA-256 only in the tooltip.
  expect(within(rows[0]).getByText(`SHA-256 ${shortHash(FULL_HASH)}`)).toHaveAttribute("title", `SHA-256 ${FULL_HASH}`);
  expect(screen.queryByText(new RegExp(FULL_HASH))).not.toBeInTheDocument();
  expect(within(rows[0]).getByText("Not linked")).toBeVisible();
  expect(within(rows[0]).getByRole("button", { name: "Move to bin" })).toBeEnabled();
  expect(within(rows[2]).getByRole("button", { name: "Move to bin" })).toBeDisabled();

  const user = userEvent.setup();
  await user.click(within(rows[2]).getByRole("button", { name: /Used by 2/ }));
  const uses = screen.getByRole("list", { name: "Objectives using access-policy.pdf" });
  expect(within(uses).getAllByRole("listitem")).toHaveLength(2);
  expect(within(uses).getByText("pinned to v1")).toBeVisible();
  await user.click(within(uses).getByRole("button", { name: /AC.L2-3.1.2\[b\]/ }));
  expect(onOpenRecord).toHaveBeenCalledWith("AC.L2-3.1.2b");

  // Status filter.
  await user.click(screen.getByRole("button", { name: "Stale 1" }));
  expect(within(screen.getByRole("table")).getAllByRole("row")).toHaveLength(2 + 1); // header, row, used-by
  expect(screen.getByRole("region", { name: "Recycle bin" })).toHaveTextContent("old-policy.pdf");
});

test("renewing a stale artifact uploads a version with the next review date and moves its mappings", async () => {
  const writes = libraryServer();
  const onChanged = vi.fn();
  render(<EvidenceLibraryView projectId="project-1" onOpenRecord={vi.fn()} onChanged={onChanged} />);
  const table = await screen.findByRole("table");
  const staleRow = within(table).getAllByRole("row")[3];
  const user = userEvent.setup();
  await user.click(within(staleRow).getByRole("button", { name: /Renew/ }));
  const form = screen.getByRole("form", { name: "Replace access-policy.pdf" });
  expect(within(form).getByText(/stays stale/)).toBeVisible();
  const move = within(form).getByRole("checkbox", { name: /Move the 2 linked objectives/ });
  expect(move).toBeChecked();
  await user.upload(within(form).getByLabelText("New version of access-policy.pdf"), new File(["2026"], "access-policy.pdf"));
  fireEvent.change(within(form).getByLabelText("Next review date"), { target: { value: "2027-10-08" } });
  expect(within(form).queryByText(/stays stale/)).not.toBeInTheDocument();
  await user.click(within(form).getByRole("button", { name: "Upload version 3" }));
  await waitFor(() => expect(writes.some((write) => write.url.endsWith("/evidence/art-stale/versions"))).toBe(true));
  const body = writes.find((write) => write.url.endsWith("/evidence/art-stale/versions"))!.body as FormData;
  expect(body.get("review_date")).toBe("2027-10-08");
  expect(body.get("move_mappings")).toBe("true");
  expect((body.get("file") as File).name).toBe("access-policy.pdf");
  await waitFor(() => expect(onChanged).toHaveBeenCalled());
});

test("the review date and the project lead time are saved from the Evidence view", async () => {
  const writes = libraryServer();
  render(<EvidenceLibraryView projectId="project-1" onOpenRecord={vi.fn()} onChanged={vi.fn()} />);
  const input = await screen.findByLabelText("Review date for network-diagram.png");
  fireEvent.change(input, { target: { value: "2026-11-01" } });
  fireEvent.blur(input);
  await waitFor(() => expect(writes).toContainEqual({ method: "PUT", url: "/api/projects/project-1/evidence/art-current/review-date", body: JSON.stringify({ review_date: "2026-11-01" }) }));
  const lead = screen.getByLabelText("Warning lead time in days");
  expect(lead).toHaveValue(30);
  const user = userEvent.setup();
  await user.clear(lead);
  await user.type(lead, "45");
  await user.click(within(lead.closest("form")!).getByRole("button", { name: "Save" }));
  await waitFor(() => expect(writes).toContainEqual({ method: "PUT", url: "/api/projects/project-1/evidence-settings", body: JSON.stringify({ lead_days: 45 }) }));
});

test("artifact labels use the file name and a short hash", () => {
  expect(artifactLabel({ name: "policy.pdf", version_number: 3, sha256: FULL_HASH })).toBe("policy.pdf · v3 · 9f86d081884c");
});

// ---------- requirement view: one artifact to several objectives ----------

const workList = [
  { record_id: "AC.L2-3.1.1", citation: "AC.L2-3.1.1", title: "Authorized Access Control", work_area: "Access Control", record_type: "requirement", parent_id: null, designation: null, sort_order: 0, editable_determination: false },
  ...["a", "b", "c"].map((letter, index) => ({
    record_id: `AC.L2-3.1.1${letter}`, citation: `AC.L2-3.1.1[${letter}]`, title: `Objective [${letter}]`, work_area: "Access Control",
    record_type: "objective", parent_id: "AC.L2-3.1.1", designation: null, sort_order: index + 1, editable_determination: true,
  })),
];

function requirementServer(options: { staleObjective?: string } = {}) {
  const statuses: Record<string, string> = { "AC.L2-3.1.1a": "Met", "AC.L2-3.1.1b": "Met", "AC.L2-3.1.1c": "Met" };
  const mapped: Record<string, { mapping_id: string; rationale: string }[]> = {};
  const writes: { method: string; url: string; body: string }[] = [];
  const stale = options.staleObjective;
  const verification = (recordId: string) => (mapped[recordId]?.length && recordId !== stale ? "verified" : "evidence_pending");
  const determination = (recordId: string, derived = false) => ({
    status: derived ? "Met" : statuses[recordId], derived, na_rationale: "", addressable_disposition: null, disposition_reason: "", interview_observation: "",
    verification: derived ? (workList.slice(1).every((o) => verification(o.record_id) === "verified") ? "verified" : "evidence_pending") : verification(recordId),
  });
  vi.mocked(fetch).mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    if (method !== "GET") writes.push({ method, url, body: String(init?.body ?? "") });
    if (url.endsWith("/profile-readiness")) {
      return Response.json({
        project_id: "project-1", state: "Intake complete", assessment_exists: true, supported_states: [], allowed_next_states: [],
        follow_up_work_required_states: [], follow_up_work_required_when_unresolved_required_fields: true, assessment_entry_allowed: true,
        assessment_entry_blocking_reasons: [], profile_completion_blocking_reasons: [],
        current_details: { unresolved_required_fields: [], follow_up_work: "", reviewed_by: "", approval_evidence: "" },
      });
    }
    if (url === "/api/projects/project-1/assessment") {
      return Response.json({
        id: "assessment-1",
        project: { id: "project-1", name: "CMMC 2026", client_id: "client-1", client_name: "Synthetic Defense" },
        framework: {
          id: "cmmc-l2", name: "CMMC Level 2", record_count: 4, walkthrough_record_count: 4, prompt_count: 0, determination_record_count: 3,
          declarations: {
            record_shape: { hierarchy: ["requirement", "objective"], determination_rule: "records_without_children" },
            rollup_rule: { precedence: ["Not Met", "Pending"], blank_children_prevent_met: true, satisfied_child_statuses: ["Met"], satisfied_rollup_status: "Met", blank_status: "" },
            status_set: ["", "Met", "Not Met", "Pending"], presentation_mode: "requirement_with_objectives",
          },
        },
        progress: { resolved_determination_count: 3, determination_record_count: 3 },
        work_list: workList, record_index: workList,
        record_states: Object.fromEntries(workList.map((record) => [record.record_id, {
          status: "Met", evidence_count: mapped[record.record_id]?.length ?? 0, open_poam_count: 0,
          verification: record.parent_id ? verification(record.record_id) : determination(record.record_id, true).verification,
          evidence_review: record.record_id === stale || (!record.parent_id && stale) ? "stale" : null,
        }])),
      });
    }
    if (url.endsWith("/evidence-mappings/bulk") && method === "POST") {
      const body = JSON.parse(String(init?.body));
      for (const recordId of body.record_ids as string[]) {
        mapped[recordId] = [...(mapped[recordId] ?? []), { mapping_id: `m-${recordId}`, rationale: body.rationale }];
      }
      return Response.json({ artifact_id: body.artifact_id, mappings: [] }, { status: 201 });
    }
    const rationaleMatch = url.match(/evidence-mappings\/m-([^/]+)\/rationale$/);
    if (rationaleMatch && method === "PUT") {
      const recordId = rationaleMatch[1];
      mapped[recordId] = mapped[recordId].map((m) => ({ ...m, rationale: JSON.parse(String(init?.body)).rationale }));
      return Response.json({});
    }
    const recordMatch = url.match(/\/records\/([^/]+)$/);
    if (recordMatch) {
      const recordId = decodeURIComponent(recordMatch[1]);
      const record = workList.find((item) => item.record_id === recordId)!;
      const isRequirement = !record.parent_id;
      return Response.json({
        record: { ...record, regulation_text: `Text for ${recordId}.` },
        determination: determination(recordId, isRequirement),
        parent: null, parent_prompts: [], context_prompts: [], prompts: [], no_prompt_explanation: null,
        children: isRequirement ? workList.slice(1).map((o) => ({ ...o, regulation_text: `Text for ${o.record_id}.`, determination: determination(o.record_id) })) : [],
        note: "",
        evidence: (mapped[recordId] ?? []).map((m) => ({
          mapping_id: m.mapping_id, artifact_id: "art-1", name: "access-policy.pdf", relative_path: "p", rationale: m.rationale,
          review_state: "Not reviewed", shared_record_count: 2, version_id: "v1", version_project_id: "project-1", version_number: 1,
          sha256: FULL_HASH, review_date: recordId === stale ? "2026-09-30" : null, review_status: recordId === stale ? "stale" : "current",
        })),
        position: { current: 1, total: 4, previous_record_id: null, next_record_id: null },
        practitioner_guidance: null,
      });
    }
    if (url.endsWith("/evidence")) {
      return Response.json([{ id: "art-1", name: "access-policy.pdf", relative_path: "p", shared_record_count: 0, version_id: "v1", version_number: 1, sha256: FULL_HASH, version_relative_path: "p", version_created_at: "2026-09-01", review_status: "current" }]);
    }
    if (url.endsWith("/cmmc-score")) return Response.json(cmmcScoreFixture([]));
    if (url.endsWith("/ssp")) return Response.json(null);
    if (url.endsWith("/finding")) return Response.json(null);
    if (url === "/api/backups") return Response.json({ warning: null, backups: [] });
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  return { writes, mapped };
}

function renderWorkspace() {
  return render(<Workspace clients={clientProjectsFixture()} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} />);
}

test("Link evidence maps one artifact to several ticked objectives in one act, each with its own rationale (AC-007)", async () => {
  const { writes, mapped } = requirementServer();
  renderWorkspace();
  await screen.findByRole("heading", { level: 1, name: "Authorized Access Control" });
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Link evidence" }));
  const picker = screen.getByRole("form", { name: "Link evidence to objectives" });
  const select = within(picker).getByRole("combobox", { name: "Evidence file" });
  // Labels carry the file name and a short hash, never the full SHA-256.
  const option = within(select).getByRole("option", { name: /access-policy\.pdf/ });
  expect(option).toHaveTextContent(`access-policy.pdf · v1 · ${shortHash(FULL_HASH)}`);
  expect(option.textContent).not.toContain(FULL_HASH);
  await user.selectOptions(select, "art-1");
  // The focused objective starts ticked; tick a second one.
  expect(within(picker).getByRole("checkbox", { name: /AC.L2-3.1.1\[a\]/ })).toBeChecked();
  await user.click(within(picker).getByRole("checkbox", { name: /AC.L2-3.1.1\[c\]/ }));
  await user.type(within(picker).getByRole("textbox", { name: "Support rationale" }), "Policy section 2.");
  await user.click(within(picker).getByRole("button", { name: "Link to 2 objectives" }));

  await waitFor(() => expect(writes.filter((write) => write.url.endsWith("/evidence-mappings/bulk"))).toHaveLength(1));
  const bulk = JSON.parse(writes.find((write) => write.url.endsWith("/evidence-mappings/bulk"))!.body);
  expect(bulk).toEqual({ artifact_id: "art-1", record_ids: ["AC.L2-3.1.1a", "AC.L2-3.1.1c"], rationale: "Policy section 2." });
  expect(Object.keys(mapped).sort()).toEqual(["AC.L2-3.1.1a", "AC.L2-3.1.1c"]);
  expect(writes.filter((write) => write.url.includes("/evidence-mappings") && !write.url.endsWith("/bulk"))).toHaveLength(0);

  // The focused objective's mapping shows; its rationale is edited on its own.
  const evidence = screen.getByRole("region", { name: "Linked evidence" });
  expect(await within(evidence).findByText("Policy section 2.")).toBeVisible();
  await user.click(within(evidence).getByRole("button", { name: "Edit rationale for access-policy.pdf" }));
  const editor = within(evidence).getByRole("textbox", { name: "Rationale for access-policy.pdf" });
  await user.clear(editor);
  await user.type(editor, "Section 2 lists the authorized users.");
  await user.click(within(evidence).getByRole("button", { name: "Save rationale" }));
  await waitFor(() => expect(mapped["AC.L2-3.1.1a"][0].rationale).toBe("Section 2 lists the authorized users."));
  expect(mapped["AC.L2-3.1.1c"][0].rationale).toBe("Policy section 2.");

  // Re-opening the picker marks objectives that already carry the artifact.
  await user.click(screen.getByRole("button", { name: "Link evidence" }));
  const again = screen.getByRole("form", { name: "Link evidence to objectives" });
  await user.selectOptions(within(again).getByRole("combobox", { name: "Evidence file" }), "art-1");
  await waitFor(() => expect(within(again).getByRole("checkbox", { name: /AC.L2-3.1.1\[c\]/ })).toBeDisabled());
  expect(within(again).getAllByText("already linked")).toHaveLength(2);
});

test("a Met whose evidence went stale shows evidence pending and the stale marker on its row", async () => {
  requirementServer({ staleObjective: "AC.L2-3.1.1a" });
  // Seed mappings by linking first so the objective has evidence.
  renderWorkspace();
  await screen.findByRole("heading", { level: 1, name: "Authorized Access Control" });
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "Link evidence" }));
  const picker = screen.getByRole("form", { name: "Link evidence to objectives" });
  await user.selectOptions(within(picker).getByRole("combobox", { name: "Evidence file" }), "art-1");
  await user.type(within(picker).getByRole("textbox", { name: "Support rationale" }), "Policy.");
  await user.click(within(picker).getByRole("button", { name: "Link to 1 objective" }));

  const row = screen.getByRole("listitem", { name: "Objective AC.L2-3.1.1[a]" });
  expect(await within(row).findByText("Evidence stale")).toBeVisible();
  expect(within(row).getByText("Evidence pending")).toBeVisible();
  expect(within(row).getByRole("button", { name: "Met" })).toHaveAttribute("aria-pressed", "true");
  const evidence = screen.getByRole("region", { name: "Linked evidence" });
  expect(await within(evidence).findByText("Stale: no longer verifies a Met")).toBeVisible();
  expect(within(evidence).getByText(`SHA-256: ${shortHash(FULL_HASH)}`)).toBeVisible();
});
