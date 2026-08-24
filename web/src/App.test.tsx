import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
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

test("keeps direct file selection and shows the initial evidence version, hash, and review state", async () => {
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL) => {
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
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
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
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
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
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
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
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
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
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
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
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
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
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
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
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
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
