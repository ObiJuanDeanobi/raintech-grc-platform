import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import { Workspace } from "./App";
import { clientProjectsFixture, cmmcScoreFixture } from "./activeAssessmentFixtures";

/**
 * Issue #143: a NOT MET requirement gets its POA&M draft in one click from the
 * requirement view, prefilled by the server from the finding, never created by
 * a determination change. The assessment header counts NOT MET requirements
 * not on any open POA&M item and filters the list to them.
 */

const requirements = [
  { id: "AC.L2-3.1.1", title: "Authorized Access Control", family: "Access Control", points: 5 },
  { id: "AC.L2-3.1.3", title: "Control CUI Flow", family: "Access Control", points: 1 },
  { id: "AU.L2-3.3.1", title: "System Auditing", family: "Audit and Accountability", points: 5 },
];

const workList = requirements.flatMap((requirement, index) => [
  {
    record_id: requirement.id, citation: requirement.id, title: requirement.title, work_area: requirement.family,
    record_type: "requirement", parent_id: null, designation: null, sort_order: index * 10, editable_determination: false,
  },
  ...["a", "b"].map((letter, offset) => ({
    record_id: `${requirement.id}${letter}`, citation: `${requirement.id}[${letter}]`, title: `Objective [${letter}]`,
    work_area: requirement.family, record_type: "objective", parent_id: requirement.id, designation: null,
    sort_order: index * 10 + offset + 1, editable_determination: true,
  })),
]);

const readiness = {
  project_id: "project-1", state: "Intake complete", assessment_exists: true,
  supported_states: ["Intake started", "Intake complete"], allowed_next_states: [],
  follow_up_work_required_states: [], follow_up_work_required_when_unresolved_required_fields: true,
  assessment_entry_allowed: true, assessment_entry_blocking_reasons: [], profile_completion_blocking_reasons: [],
  current_details: { unresolved_required_fields: [], follow_up_work: "", reviewed_by: "", approval_evidence: "" },
};

type PoamItem = { id: string; title: string; description: string; status: string; validation_state: string };

function derived(statuses: string[]): string {
  if (statuses.includes("Not Met")) return "Not Met";
  if (statuses.includes("Pending")) return "Pending";
  if (statuses.length > 0 && statuses.every((status) => status === "Met")) return "Met";
  return "";
}

/** A small in-memory API: the server, not the component, decides what exists. */
function poamServer(initial: Record<string, string>) {
  const statuses: Record<string, string> = { ...initial };
  const poam: Record<string, PoamItem[]> = {};
  const writes: { method: string; url: string; body: string }[] = [];
  const objectivesOf = (id: string) => workList.filter((record) => record.parent_id === id);
  const requirementStatus = (id: string) => derived(objectivesOf(id).map((o) => statuses[o.record_id] ?? ""));
  const open = (id: string) => (poam[id] ?? []).filter((item) => !["Closed", "Withdrawn"].includes(item.status));
  const unplanned = () => {
    const ids = requirements.map((r) => r.id).filter((id) => requirementStatus(id) === "Not Met" && open(id).length === 0);
    return { count: ids.length, requirement_ids: ids };
  };
  const determination = (id: string, isDerived = false) => ({
    status: isDerived ? requirementStatus(id) : statuses[id] ?? "", derived: isDerived, na_rationale: "",
    addressable_disposition: null, disposition_reason: "", interview_observation: "", verification: null,
  });
  const finding = (id: string) => {
    if (requirementStatus(id) !== "Not Met" && !poam[id]) return null;
    return {
      finding: { id: `finding-${id}`, title: `Not Met: ${id}`, status: "Open" },
      requirement_id: id,
      requirement_status: requirementStatus(id),
      failed_objectives: objectivesOf(id).filter((o) => statuses[o.record_id] === "Not Met").map((o) => ({
        record_id: o.record_id, citation: o.citation, regulation_text: `Objective text for ${o.record_id}.`,
        note: "Examine: Synthetic note.", interview_observation: "", evidence: [],
      })),
      poam_items: poam[id] ?? [],
      history: [],
    };
  };

  vi.mocked(fetch).mockImplementation(async (input, init) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    const body = String(init?.body ?? "");
    if (method !== "GET") writes.push({ method, url, body });
    if (url.endsWith("/profile-readiness")) return Response.json(readiness);
    if (url === "/api/projects/project-1/assessment") {
      return Response.json({
        id: "assessment-1",
        project: { id: "project-1", name: "CMMC 2026", client_id: "client-1", client_name: "Synthetic Defense" },
        framework: {
          id: "cmmc-l2", name: "CMMC Level 2", record_count: workList.length, walkthrough_record_count: workList.length,
          prompt_count: 0, determination_record_count: 6,
          declarations: {
            record_shape: { hierarchy: ["requirement", "objective"], determination_rule: "records_without_children" },
            rollup_rule: { precedence: ["Not Met", "Pending"], blank_children_prevent_met: true, satisfied_child_statuses: ["Met"], satisfied_rollup_status: "Met", blank_status: "" },
            status_set: ["", "Met", "Not Met", "Pending"],
            presentation_mode: "requirement_with_objectives",
            findings_rule: "requirement_level",
            scoring: { authority: "32 CFR 170.24", requirements: Object.fromEntries(requirements.map((r) => [r.id, { rule: "fixed", points: r.points, source: "32 CFR 170.24" }])) },
          },
        },
        progress: { resolved_determination_count: Object.values(statuses).filter((s) => s === "Met" || s === "Not Met").length, determination_record_count: 6 },
        work_list: workList, record_index: workList,
        record_states: Object.fromEntries(workList.map((record) => [record.record_id, {
          status: record.parent_id ? statuses[record.record_id] ?? "" : requirementStatus(record.record_id),
          evidence_count: 0, open_poam_count: record.parent_id ? 0 : open(record.record_id).length, verification: null,
        }])),
        not_met_without_poam: unplanned(),
      });
    }
    const determinationMatch = url.match(/\/determinations\/([^/]+)$/);
    if (determinationMatch && method === "PUT") {
      const id = decodeURIComponent(determinationMatch[1]);
      statuses[id] = JSON.parse(body).status;
      return Response.json(determination(id));
    }
    const recordMatch = url.match(/\/records\/([^/]+)$/);
    if (recordMatch) {
      const id = decodeURIComponent(recordMatch[1]);
      const record = workList.find((item) => item.record_id === id)!;
      const isRequirement = !record.parent_id;
      return Response.json({
        record: { ...record, regulation_text: `Text for ${id}.` },
        determination: determination(id, isRequirement),
        parent: null, parent_prompts: [], context_prompts: [], prompts: [], no_prompt_explanation: null,
        children: isRequirement ? objectivesOf(id).map((o) => ({ ...o, regulation_text: `Objective text for ${o.record_id}.`, determination: determination(o.record_id) })) : [],
        note: "", evidence: [], practitioner_guidance: null,
        position: { current: 1, total: workList.length, previous_record_id: null, next_record_id: null },
      });
    }
    const findingMatch = url.match(/\/requirements\/([^/]+)\/finding$/);
    if (findingMatch) return Response.json(finding(decodeURIComponent(findingMatch[1])));
    const createMatch = url.match(/\/requirements\/([^/]+)\/poam$/);
    if (createMatch && method === "POST") {
      const id = decodeURIComponent(createMatch[1]);
      if (requirementStatus(id) !== "Not Met") return Response.json({ detail: "POA&M items attach only to a requirement that is currently Not Met" }, { status: 409 });
      if (open(id).length > 0) return Response.json({ detail: `${id} is already on POA&M item` }, { status: 409 });
      const title = `${id} ${requirements.find((r) => r.id === id)!.title}`;
      poam[id] = [...(poam[id] ?? []), { id: `poam-${id}-${(poam[id] ?? []).length + 1}`, title, description: `Remediate ${title}. Failed assessment objectives:`, status: "Draft", validation_state: "Not Ready" }];
      return Response.json(finding(id), { status: 201 });
    }
    const editMatch = url.match(/\/requirements\/([^/]+)\/poam\/([^/]+)$/);
    if (editMatch && method === "PUT") {
      const id = decodeURIComponent(editMatch[1]);
      const next = JSON.parse(body);
      poam[id] = poam[id].map((item) => (item.id === editMatch[2] ? { ...item, ...next } : item));
      return Response.json(finding(id));
    }
    if (url.endsWith("/cmmc-score")) {
      const lines = requirements.flatMap((r) => {
        const status = requirementStatus(r.id);
        if (status === "Met") return [];
        const state = status === "Not Met" ? "not_met" as const : status === "Pending" ? "pending" as const : "not_assessed" as const;
        return [{ record_id: r.id, title: r.title, points: r.points, state }];
      });
      return Response.json({ ...cmmcScoreFixture(lines), not_met_without_poam: unplanned() });
    }
    if (url.endsWith("/ssp")) return Response.json(null);
    if (url.includes("/evidence")) return Response.json([]);
    if (url === "/api/backups") return Response.json({ warning: null, backups: [] });
    return Response.json({ detail: "not found" }, { status: 404 });
  });

  return {
    poam,
    writes,
    poamWrites: () => writes.filter((write) => write.url.includes("/poam")),
  };
}

function renderWorkspace() {
  return render(
    <Workspace clients={clientProjectsFixture()} projectId="project-1" onProjectChange={vi.fn()} onWorkspaceCreated={vi.fn()} />,
  );
}

async function openRequirement(title: string) {
  const user = userEvent.setup();
  const list = await screen.findByRole("navigation", { name: "Requirements by family" });
  const family = within(list).getAllByRole("button", { expanded: false });
  for (const header of family) await user.click(header);
  await user.click(within(list).getByRole("button", { name: new RegExp(title) }));
  await screen.findByRole("heading", { level: 1, name: title });
  return user;
}

const ALL_NOT_MET = {
  "AC.L2-3.1.1a": "Not Met", "AC.L2-3.1.1b": "Met",
  "AC.L2-3.1.3a": "Not Met", "AC.L2-3.1.3b": "Not Met",
  "AU.L2-3.3.1a": "Pending",
};

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn());
});

test("a NOT MET requirement creates one prefilled POA&M draft in one click, opened for editing", async () => {
  const server = poamServer(ALL_NOT_MET);
  renderWorkspace();
  const user = await openRequirement("Authorized Access Control");
  const panel = await screen.findByRole("region", { name: "Requirement finding" });
  const create = await within(panel).findByRole("button", { name: "Create POA&M draft" });
  expect(create).toBeEnabled();
  expect(server.poamWrites()).toHaveLength(0);

  await user.click(create);
  await waitFor(() => expect(server.poamWrites()).toHaveLength(1));
  expect(server.poamWrites()[0]).toMatchObject({ method: "POST", url: "/api/projects/project-1/assessments/assessment-1/requirements/AC.L2-3.1.1/poam" });
  expect(JSON.parse(server.poamWrites()[0].body)).toEqual({ draft: true });

  // The draft opens inline, prefilled by the server, with its title focused.
  const draft = await within(panel).findByRole("form", { name: /POA&M draft AC.L2-3.1.1 Authorized Access Control/ });
  const title = within(draft).getByLabelText("Title");
  expect(title).toHaveValue("AC.L2-3.1.1 Authorized Access Control");
  expect(title).toHaveFocus();
  expect(within(draft).getByLabelText("Description")).toHaveValue("Remediate AC.L2-3.1.1 Authorized Access Control. Failed assessment objectives:");
  expect(draft).toHaveTextContent("Draft");

  // A second draft is refused before it is asked for: the button is disabled with its reason.
  const again = within(panel).getByRole("button", { name: "Create POA&M draft" });
  expect(again).toBeDisabled();
  expect(panel).toHaveTextContent("Already on POA&M item “AC.L2-3.1.1 Authorized Access Control” (Draft).");
  await user.click(again);
  expect(server.poamWrites()).toHaveLength(1);

  // Editing saves title and description through the POA&M item route.
  await user.clear(title);
  await user.type(title, "Rebuild the authorized user list");
  await user.click(within(draft).getByRole("button", { name: "Save draft" }));
  await waitFor(() => expect(server.poamWrites()).toHaveLength(2));
  expect(server.poamWrites()[1]).toMatchObject({ method: "PUT", url: "/api/projects/project-1/assessments/assessment-1/requirements/AC.L2-3.1.1/poam/poam-AC.L2-3.1.1-1" });
  expect(JSON.parse(server.poamWrites()[1].body).title).toBe("Rebuild the authorized user list");
});

test("a requirement 32 CFR 170.21 does not allow on a POA&M warns on the draft but does not block it", async () => {
  const server = poamServer(ALL_NOT_MET);
  renderWorkspace();
  const user = await openRequirement("Authorized Access Control");
  const panel = await screen.findByRole("region", { name: "Requirement finding" });
  const warning = await within(panel).findByRole("note");
  expect(warning).toHaveTextContent("32 CFR 170.21: cannot stay on a POA&M for Conditional status.");
  expect(warning).toHaveTextContent("5-point requirement; only 1-point requirements may be on a POA&M (32 CFR 170.21(a)(2)(ii)).");
  await user.click(within(panel).getByRole("button", { name: "Create POA&M draft" }));
  await within(panel).findByRole("form", { name: /POA&M draft/ });
  expect(within(panel).getByRole("note")).toHaveTextContent("cannot stay on a POA&M");
  expect(server.poamWrites()).toHaveLength(1);

  // A 1-point requirement is POA&M-eligible: no warning.
  await user.click(within(screen.getByRole("navigation", { name: "Requirements by family" })).getByRole("button", { name: /Control CUI Flow/ }));
  await screen.findByRole("heading", { level: 1, name: "Control CUI Flow" });
  const eligible = await screen.findByRole("region", { name: "Requirement finding" });
  await within(eligible).findByRole("button", { name: "Create POA&M draft" });
  await waitFor(() => expect(within(eligible).queryByRole("note")).not.toBeInTheDocument());
});

test("the header counts NOT MET requirements not on a POA&M and filters the list to them", async () => {
  poamServer(ALL_NOT_MET);
  renderWorkspace();
  const count = await screen.findByRole("button", { name: /NOT MET not on a POA&M/ });
  expect(count).toHaveTextContent("2 NOT MET not on a POA&M");
  expect(count).toHaveAttribute("aria-pressed", "false");
  const user = userEvent.setup();
  await user.click(count);
  expect(count).toHaveAttribute("aria-pressed", "true");
  // The list re-renders as the workspace reloads; always read the current one.
  const list = () => screen.getByRole("navigation", { name: "Requirements by family" });
  expect(within(list()).getByRole("button", { name: /Authorized Access Control/ })).toBeVisible();
  expect(within(list()).getByRole("button", { name: /Control CUI Flow/ })).toBeVisible();
  expect(within(list()).queryByRole("button", { name: /System Auditing/ })).not.toBeInTheDocument();

  // Drafting a POA&M takes the requirement out of the count and the filtered list.
  await user.click(within(list()).getByRole("button", { name: /Authorized Access Control/ }));
  await screen.findByRole("heading", { level: 1, name: "Authorized Access Control" });
  const panel = await screen.findByRole("region", { name: "Requirement finding" });
  await user.click(await within(panel).findByRole("button", { name: "Create POA&M draft" }));
  await waitFor(() => expect(screen.getByRole("button", { name: /NOT MET not on a POA&M/ })).toHaveTextContent("1 NOT MET not on a POA&M"));
  await waitFor(() => expect(within(list()).queryByRole("button", { name: /Authorized Access Control/ })).not.toBeInTheDocument());
  expect(within(list()).getByRole("button", { name: /Control CUI Flow/ })).toBeVisible();

  await user.click(screen.getByRole("button", { name: /NOT MET not on a POA&M/ }));
  // Unfiltered, every family is back (collapsed unless it holds the active requirement).
  expect(within(list()).getByRole("button", { name: /^Audit and Accountability/ })).toBeVisible();
});

test("Pending has no POA&M draft and a determination change never creates one", async () => {
  const server = poamServer(ALL_NOT_MET);
  renderWorkspace();
  const user = await openRequirement("System Auditing");
  const panel = await screen.findByRole("region", { name: "Requirement finding" });
  expect(panel).toHaveTextContent("Pending objectives create follow-up work, never a finding.");
  expect(within(panel).queryByRole("button", { name: "Create POA&M draft" })).not.toBeInTheDocument();

  // Not Met on an objective derives the requirement Not Met: the button appears, nothing is created.
  const row = screen.getByRole("listitem", { name: "Objective AU.L2-3.3.1[b]" });
  await user.click(within(row).getByRole("button", { name: "Not Met" }));
  await waitFor(() => expect(screen.getByRole("button", { name: /NOT MET not on a POA&M/ })).toHaveTextContent("3 NOT MET"));
  expect(await within(await screen.findByRole("region", { name: "Requirement finding" })).findByRole("button", { name: "Create POA&M draft" })).toBeEnabled();
  expect(server.poamWrites()).toHaveLength(0);
  expect(server.poam).toEqual({});
});
