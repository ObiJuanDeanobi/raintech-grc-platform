import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import { ProfilePanel } from "./ProfilePanel";

function deferredResponse() {
  let resolve!: (response: Response) => void;
  const promise = new Promise<Response>((next) => {
    resolve = next;
  });
  return { promise, resolve };
}

const provenance = {
  source: "Synthetic discovery interview",
  reviewer: "Johnathan",
  last_reviewed_at: "2026-08-26T20:00:00+00:00",
};

function profileValue(section: string, fieldKey: string, label: string, value: string) {
  return { section, field_key: fieldKey, label, value, ...provenance };
}

const version = {
  id: "profile-v1",
  project_id: "project-1",
  version_number: 1,
  status: "Draft",
  created_by: "johnathan",
  created_at: "2026-08-26T19:00:00+00:00",
  content_revision: "revision-1",
  values: [
    profileValue("project_metadata", "delivery_context", "Delivery context", "Synthetic program"),
  ],
  items: [
    {
      id: "environment-1",
      client_key: "environment-cloud",
      item_type: "environment",
      environment_item_id: null,
      values: [
        profileValue("environments", "name", "Name", "Synthetic cloud"),
        profileValue("environments", "environment_type", "Environment type", "cloud"),
      ],
    },
    {
      id: "scope-1",
      client_key: "scope-item",
      item_type: "scope_item",
      environment_item_id: "environment-1",
      values: [profileValue("scope_items", "name", "Name", "Synthetic workstation")],
    },
    ...[
      ["business_process", "business_processes", "Client intake"],
      ["location", "locations", "Synthetic headquarters"],
      ["external_service", "external_services", "Synthetic MSP"],
      ["person_role", "people_roles", "Security Officer"],
      ["exclusion_constraint", "exclusions_constraints", "Training lab excluded"],
      ["reference", "references", "Synthetic boundary memo"],
      ["unknown_follow_up", "unknowns_follow_up", "Final endpoint count"],
    ].map(([itemType, section, itemValue], index) => ({
      id: `${itemType}-${index}`,
      client_key: `${itemType}-${index}`,
      item_type: itemType,
      environment_item_id: null,
      values: [profileValue(section, "name", "Name", itemValue)],
    })),
  ],
  lifecycle: [
    {
      id: "event-draft",
      status: "Draft",
      actor: { id: "johnathan", display_name: "Johnathan" },
      reviewer: "",
      timestamp: "2026-08-26T19:00:00+00:00",
    },
  ],
  evidence: [],
};

const profile = {
  project_id: "project-1",
  active_version_id: null,
  versions: [version],
  template: {
    available: false,
    name: null,
    message: "No framework template is released. Use the complete neutral Profile form.",
  },
};

const artifact = {
  id: "artifact-1",
  name: "existing.txt",
  relative_path: "project-1/existing.txt",
  shared_record_count: 1,
  version_id: "evidence-version-1",
  version_number: 1,
  sha256: "abc123",
  version_relative_path: "project-1/existing.txt",
  version_created_at: "2026-08-26T19:30:00+00:00",
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === "/api/projects/project-1/profile") return Response.json(profile);
      if (url === "/api/projects/project-1/evidence" && init?.method !== "POST") {
        return Response.json([artifact]);
      }
      if (url.endsWith("/evidence-mappings") && init?.method === "POST") {
        return Response.json(
          {
            mapping_id: "mapping-1",
            artifact_id: artifact.id,
            name: artifact.name,
            evidence_version_id: artifact.version_id,
            version_number: 1,
            sha256: artifact.sha256,
            relative_path: artifact.relative_path,
            target_type: "profile",
            target_key: "project_metadata.delivery_context",
            rationale: "Supports the delivery context.",
            review_state: "Not reviewed",
            created_at: "2026-08-26T20:30:00+00:00",
            content_revision: "revision-2",
          },
          { status: 201 },
        );
      }
      if (url.endsWith("/evidence") && init?.method === "POST") {
        return Response.json(
          {
            artifact: {
              ...artifact,
              id: "artifact-uploaded",
              version: {
                id: "evidence-version-uploaded",
                version_number: 1,
                sha256: "storedbyteshash",
              },
            },
            mapping: {
              mapping_id: "mapping-uploaded",
              artifact_id: "artifact-uploaded",
              name: "profile-support.txt",
              evidence_version_id: "evidence-version-uploaded",
              version_number: 1,
              sha256: "storedbyteshash",
              relative_path: "project-1/profile-support.txt",
              target_type: "profile",
              target_key: "references.boundary",
              rationale: "Supports the boundary reference.",
              review_state: "Not reviewed",
              created_at: "2026-08-26T20:30:00+00:00",
            },
            content_revision: "revision-3",
          },
          { status: 201 },
        );
      }
      if (url.endsWith("/lifecycle") && init?.method === "POST") {
        const body = JSON.parse(String(init.body)) as { status: "Reviewed" | "Approved" };
        const lifecycle = [
          ...version.lifecycle,
          {
            id: `event-${body.status}`,
            status: body.status,
            actor: { id: "johnathan", display_name: "Johnathan" },
            reviewer: "Johnathan",
            timestamp: "2026-08-26T21:00:00+00:00",
          },
        ];
        return Response.json(
          {
            active_version_id: body.status === "Approved" ? version.id : null,
            version: { ...version, status: body.status, lifecycle },
          },
          { status: 201 },
        );
      }
      if (url.endsWith("/profile/versions") && init?.method === "POST") {
        return Response.json(
          { ...version, id: "profile-v2", version_number: 2, status: "Draft" },
          { status: 201 },
        );
      }
      if (url.includes("/profile/versions/") && init?.method === "PUT") {
        return Response.json(version);
      }
      return Response.json({ detail: "not found" }, { status: 404 });
    }),
  );
});

test("renders the complete neutral form and provenance without a framework template", async () => {
  render(<ProfilePanel projectId="project-1" />);

  expect(await screen.findByRole("heading", { name: "Versioned project profile" })).toBeVisible();
  expect(screen.getByText("No framework template is released. Use the complete neutral Profile form."))
    .toBeVisible();
  for (const heading of [
    "Project metadata",
    "Environments & inventory",
    "Business processes",
    "Locations",
    "External services & vendors",
    "People & roles",
    "Exclusions & constraints",
    "References",
    "Unknowns & follow-up",
  ]) {
    expect(screen.getByRole("heading", { name: heading })).toBeVisible();
  }
  expect(screen.getByDisplayValue("Synthetic workstation")).toBeVisible();
  expect(screen.getByRole("heading", { name: "Inventory in this environment" })).toBeVisible();
  expect(screen.getAllByDisplayValue("Synthetic discovery interview").length).toBeGreaterThan(0);
  expect(screen.getAllByDisplayValue("Johnathan").length).toBeGreaterThan(0);
});

test("records lifecycle, preserves prior versions, and creates a later draft", async () => {
  const user = userEvent.setup();
  render(<ProfilePanel projectId="project-1" />);
  expect(await screen.findAllByText("Version 1 · Draft")).not.toHaveLength(0);

  await user.type(screen.getByLabelText("Lifecycle reviewer"), "Johnathan");
  await user.click(screen.getByRole("button", { name: "Record review" }));
  expect(await screen.findByText("Reviewed by Johnathan")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Approve version" }));
  expect(await screen.findByText("Active approved snapshot")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Create new version" }));
  expect(await screen.findAllByText("Version 2 · Draft")).not.toHaveLength(0);
  expect(screen.getByRole("option", { name: /Version 1 · Approved/ })).toBeInTheDocument();
});

test("reuses same-project evidence and shows a new stored-byte upload hash", async () => {
  const user = userEvent.setup();
  render(<ProfilePanel projectId="project-1" />);
  await screen.findByRole("option", { name: "existing.txt" });

  await user.selectOptions(screen.getByLabelText("Immutable evidence version"), artifact.id);
  await user.selectOptions(
    screen.getByLabelText("Reuse target"),
    "field:project_metadata:delivery_context",
  );
  await user.type(screen.getByLabelText("Reuse rationale"), "Supports the delivery context.");
  await user.click(screen.getByRole("button", { name: "Map existing version" }));
  expect(await screen.findByText("abc123")).toBeVisible();
  expect(screen.getByText("Not reviewed")).toBeVisible();
  const reuseCall = vi.mocked(fetch).mock.calls.find(
    ([input, init]) =>
      String(input).endsWith("/evidence-mappings") && init?.method === "POST",
  );
  expect(JSON.parse(String(reuseCall?.[1]?.body)).expected_revision).toBe("revision-1");

  await user.upload(
    screen.getByLabelText("New sanitized Profile file"),
    new File(["synthetic sanitized"], "profile-support.txt", { type: "text/plain" }),
  );
  await user.selectOptions(
    screen.getByLabelText("Upload target"),
    "item:reference-5:name",
  );
  await user.type(screen.getByLabelText("Upload rationale"), "Supports the boundary reference.");
  await user.click(screen.getByRole("button", { name: "Upload and map" }));
  await waitFor(() =>
    expect(
      vi.mocked(fetch).mock.calls.some(
        ([input, init]) =>
          String(input).endsWith("/profile/versions/profile-v1/evidence")
          && init?.method === "POST",
      ),
    ).toBe(true),
  );
  const uploadCall = vi.mocked(fetch).mock.calls.find(
    ([input, init]) =>
      String(input).endsWith("/profile/versions/profile-v1/evidence")
      && init?.method === "POST",
  );
  expect((uploadCall?.[1]?.body as FormData).get("expected_revision")).toBe("revision-2");
  expect(await screen.findByText("storedbyteshash")).toBeVisible();
  expect(screen.getAllByText("Version 1 · SHA-256")).toHaveLength(2);
});

test("uses the same component for HIPAA and CMMC and ignores a late project response", async () => {
  let resolveProjectA: (response: Response) => void = () => undefined;
  const projectA = new Promise<Response>((resolve) => {
    resolveProjectA = resolve;
  });
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === "/api/projects/project-1/profile") return projectA;
    if (url === "/api/projects/project-2/profile") {
      return Response.json({
        ...profile,
        project_id: "project-2",
        versions: [
          {
            ...version,
            id: "project-b-version",
            project_id: "project-2",
            values: [
              profileValue(
                "project_metadata",
                "delivery_context",
                "Delivery context",
                "Synthetic CMMC project",
              ),
            ],
          },
        ],
      });
    }
    if (url.endsWith("/evidence")) return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const { rerender } = render(<ProfilePanel projectId="project-1" />);
  rerender(<ProfilePanel projectId="project-2" />);
  expect(await screen.findByDisplayValue("Synthetic CMMC project")).toBeVisible();
  resolveProjectA(Response.json(profile));
  await waitFor(() =>
    expect(screen.getByDisplayValue("Synthetic CMMC project")).toBeVisible()
  );
  expect(screen.queryByDisplayValue("Synthetic program")).not.toBeInTheDocument();
});

test("blocks review of dirty displayed content until the draft is saved", async () => {
  const user = userEvent.setup();
  render(<ProfilePanel projectId="project-1" />);
  const field = await screen.findByDisplayValue("Synthetic program");
  await user.clear(field);
  await user.type(field, "Unsaved changed program");
  expect(screen.getByText(/Unsaved Profile changes must be saved/i)).toBeVisible();
  expect(screen.getByRole("button", { name: "Record review" })).toBeDisabled();
  expect(
    vi.mocked(fetch).mock.calls.some(
      ([input]) => String(input).endsWith("/lifecycle"),
    ),
  ).toBe(false);
});

test("an edit made during a delayed save remains visible and dirty", async () => {
  const delayedSave = deferredResponse();
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/profile")) return Response.json(profile);
    if (url.endsWith("/evidence")) return Response.json([]);
    if (url.includes("/profile/versions/") && init?.method === "PUT") {
      return delayedSave.promise;
    }
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const onDirtyChange = vi.fn();
  const user = userEvent.setup();
  render(<ProfilePanel projectId="project-1" onDirtyChange={onDirtyChange} />);
  const field = await screen.findByDisplayValue("Synthetic program");
  await user.clear(field);
  await user.type(field, "Submitted edit");
  await user.click(screen.getByRole("button", { name: "Save draft" }));
  await user.clear(field);
  await user.type(field, "Newer local edit");
  delayedSave.resolve(Response.json({
    ...version,
    content_revision: "revision-2",
    values: [
      profileValue("project_metadata", "delivery_context", "Delivery context", "Submitted edit"),
    ],
  }));
  expect(await screen.findByDisplayValue("Newer local edit")).toBeVisible();
  expect(await screen.findByText(/newer Profile edits remain unsaved/i)).toBeVisible();
  await waitFor(() => expect(onDirtyChange).toHaveBeenLastCalledWith(true));
});

test("a delayed lifecycle request locks editing and applies the real server state", async () => {
  const delayedLifecycle = deferredResponse();
  let serverReviewed = false;
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/profile")) {
      return Response.json(
        serverReviewed
          ? { ...profile, versions: [{ ...version, status: "Reviewed" }] }
          : profile,
      );
    }
    if (url.endsWith("/evidence")) return Response.json([]);
    if (url.endsWith("/lifecycle") && init?.method === "POST") {
      return delayedLifecycle.promise;
    }
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const onDirtyChange = vi.fn();
  const user = userEvent.setup();
  const mounted = render(<ProfilePanel projectId="project-1" onDirtyChange={onDirtyChange} />);
  const field = await screen.findByDisplayValue("Synthetic program");
  await user.type(screen.getByLabelText("Lifecycle reviewer"), "Johnathan");
  await user.click(screen.getByRole("button", { name: "Record review" }));
  expect(field).toBeDisabled();
  expect(screen.getByLabelText("Profile version")).toBeDisabled();
  expect(field).toHaveValue("Synthetic program");
  serverReviewed = true;
  delayedLifecycle.resolve(Response.json({
    active_version_id: null,
    version: {
      ...version,
      status: "Reviewed",
      lifecycle: [
        ...version.lifecycle,
        {
          id: "event-reviewed",
          status: "Reviewed",
          actor: { id: "johnathan", display_name: "Johnathan" },
          reviewer: "Johnathan",
          content_revision: "revision-1",
          timestamp: "2026-08-26T21:00:00+00:00",
        },
      ],
    },
  }));

  expect(await screen.findByText("Reviewed by Johnathan")).toBeVisible();
  expect(screen.getByDisplayValue("Synthetic program")).toBeDisabled();
  expect(screen.getAllByText("Version 1 · Reviewed")).not.toHaveLength(0);
  expect(screen.queryByRole("button", { name: "Save draft" })).not.toBeInTheDocument();
  await waitFor(() => expect(onDirtyChange).toHaveBeenLastCalledWith(false));
  mounted.unmount();
  render(<ProfilePanel projectId="project-1" />);
  expect(await screen.findByDisplayValue("Synthetic program")).toBeDisabled();
  expect(screen.getAllByText("Version 1 · Reviewed")).not.toHaveLength(0);
});

test("delayed evidence reuse merges once without overwriting newer local edits", async () => {
  const delayedReuse = deferredResponse();
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/profile")) return Response.json(profile);
    if (url.endsWith("/evidence") && init?.method !== "POST") return Response.json([artifact]);
    if (url.endsWith("/evidence-mappings") && init?.method === "POST") {
      return delayedReuse.promise;
    }
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const onDirtyChange = vi.fn();
  const user = userEvent.setup();
  render(<ProfilePanel projectId="project-1" onDirtyChange={onDirtyChange} />);
  const field = await screen.findByDisplayValue("Synthetic program");
  await user.selectOptions(screen.getByLabelText("Immutable evidence version"), artifact.id);
  await user.selectOptions(
    screen.getByLabelText("Reuse target"),
    "field:project_metadata:delivery_context",
  );
  await user.type(screen.getByLabelText("Reuse rationale"), "Delayed evidence.");
  await user.click(screen.getByRole("button", { name: "Map existing version" }));
  await user.clear(field);
  await user.type(field, "Newer edit during reuse");
  delayedReuse.resolve(Response.json({
    mapping_id: "delayed-mapping",
    artifact_id: artifact.id,
    uploaded_file_id: "upload-id",
    name: artifact.name,
    evidence_version_id: artifact.version_id,
    version_number: 1,
    sha256: artifact.sha256,
    relative_path: artifact.relative_path,
    target_type: "profile",
    target_key: "field:project_metadata:delivery_context",
    rationale: "Delayed evidence.",
    review_state: "Not reviewed",
    created_at: "2026-08-26T21:00:00+00:00",
    content_revision: "revision-2",
  }));

  expect(await screen.findByDisplayValue("Newer edit during reuse")).toBeVisible();
  expect(screen.getAllByText(/Delayed evidence/)).toHaveLength(1);
  await waitFor(() => expect(onDirtyChange).toHaveBeenLastCalledWith(true));
});

test("delayed evidence upload merges once without overwriting newer local edits", async () => {
  const delayedUpload = deferredResponse();
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/profile")) return Response.json(profile);
    if (url.endsWith("/evidence") && init?.method !== "POST") return Response.json([]);
    if (url.endsWith("/evidence") && init?.method === "POST") return delayedUpload.promise;
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const onDirtyChange = vi.fn();
  const user = userEvent.setup();
  render(<ProfilePanel projectId="project-1" onDirtyChange={onDirtyChange} />);
  const field = await screen.findByDisplayValue("Synthetic program");
  await user.upload(
    screen.getByLabelText("New sanitized Profile file"),
    new File(["delayed"], "delayed.txt", { type: "text/plain" }),
  );
  await user.selectOptions(
    screen.getByLabelText("Upload target"),
    "field:project_metadata:delivery_context",
  );
  await user.type(screen.getByLabelText("Upload rationale"), "Delayed upload.");
  await user.click(screen.getByRole("button", { name: "Upload and map" }));
  await user.clear(field);
  await user.type(field, "Newer edit during upload");
  delayedUpload.resolve(Response.json({
    artifact: { ...artifact, id: "uploaded-artifact", name: "delayed.txt" },
    mapping: {
      mapping_id: "delayed-upload-mapping",
      artifact_id: "uploaded-artifact",
      uploaded_file_id: "uploaded-file-id",
      name: "delayed.txt",
      evidence_version_id: "uploaded-version",
      version_number: 1,
      sha256: "uploaded-hash",
      relative_path: "project-1/uploaded.txt",
      target_type: "profile",
      target_key: "field:project_metadata:delivery_context",
      rationale: "Delayed upload.",
      review_state: "Not reviewed",
      created_at: "2026-08-26T21:00:00+00:00",
    },
    content_revision: "revision-2",
  }));

  expect(await screen.findByDisplayValue("Newer edit during upload")).toBeVisible();
  expect(screen.getAllByText(/Delayed upload/)).toHaveLength(1);
  await waitFor(() => expect(onDirtyChange).toHaveBeenLastCalledWith(true));
});

test("sends the displayed revision and reloads after a stale lifecycle conflict", async () => {
  let lifecycleBody: { expected_revision?: string } = {};
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/profile")) return Response.json(profile);
    if (url.endsWith("/evidence")) return Response.json([]);
    if (url.endsWith("/lifecycle") && init?.method === "POST") {
      lifecycleBody = JSON.parse(String(init.body)) as { expected_revision?: string };
      return Response.json(
        { detail: "Profile content changed after review began; reload and review again" },
        { status: 409 },
      );
    }
    if (url.endsWith("/profile/versions/profile-v1")) {
      return Response.json({
        ...version,
        content_revision: "revision-2",
        values: [
          profileValue(
            "project_metadata",
            "delivery_context",
            "Delivery context",
            "Changed by another operator",
          ),
        ],
      });
    }
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const user = userEvent.setup();
  render(<ProfilePanel projectId="project-1" />);
  await screen.findByDisplayValue("Synthetic program");
  await user.type(screen.getByLabelText("Lifecycle reviewer"), "Johnathan");
  await user.click(screen.getByRole("button", { name: "Record review" }));

  expect(await screen.findByDisplayValue("Changed by another operator")).toBeVisible();
  expect(lifecycleBody.expected_revision).toBe("revision-1");
  expect(screen.getByRole("alert")).toHaveTextContent(/reloaded; review it again/i);
});

test("a stale evidence mutation reloads the changed snapshot for re-review", async () => {
  let mappingBody: { expected_revision?: string } = {};
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/profile")) return Response.json(profile);
    if (url.endsWith("/evidence") && init?.method !== "POST") return Response.json([artifact]);
    if (url.endsWith("/evidence-mappings") && init?.method === "POST") {
      mappingBody = JSON.parse(String(init.body)) as { expected_revision?: string };
      return Response.json(
        { detail: "Profile snapshot changed after it was loaded; reload and review again" },
        { status: 409 },
      );
    }
    if (url.endsWith("/profile/versions/profile-v1")) {
      return Response.json({
        ...version,
        content_revision: "revision-2",
        evidence: [{
          mapping_id: "other-client-mapping",
          artifact_id: artifact.id,
          uploaded_file_id: "other-client-file",
          name: artifact.name,
          evidence_version_id: artifact.version_id,
          version_number: 1,
          sha256: artifact.sha256,
          relative_path: artifact.relative_path,
          target_type: "profile",
          target_key: "field:project_metadata:delivery_context",
          rationale: "Added by another operator.",
          review_state: "Not reviewed",
          created_at: "2026-08-26T20:30:00+00:00",
        }],
      });
    }
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const user = userEvent.setup();
  render(<ProfilePanel projectId="project-1" />);
  await screen.findByRole("option", { name: "existing.txt" });
  await user.selectOptions(screen.getByLabelText("Immutable evidence version"), artifact.id);
  await user.selectOptions(
    screen.getByLabelText("Reuse target"),
    "field:project_metadata:delivery_context",
  );
  await user.type(screen.getByLabelText("Reuse rationale"), "Stale local rationale.");
  await user.click(screen.getByRole("button", { name: "Map existing version" }));

  expect(await screen.findByText(/Added by another operator/)).toBeVisible();
  expect(mappingBody.expected_revision).toBe("revision-1");
  expect(screen.getByRole("alert")).toHaveTextContent(/reloaded; review it again/i);
});

test("nests each inventory item only beneath its assigned environment", async () => {
  const twoEnvironmentVersion = {
    ...version,
    items: [
      {
        id: "environment-a",
        client_key: "environment-a",
        item_type: "environment",
        environment_item_id: null,
        values: [
          profileValue("environments", "name", "Name", "Cloud A"),
          profileValue("environments", "environment_type", "Environment type", "cloud"),
        ],
      },
      {
        id: "environment-b",
        client_key: "environment-b",
        item_type: "environment",
        environment_item_id: null,
        values: [
          profileValue("environments", "name", "Name", "Site B"),
          profileValue("environments", "environment_type", "Environment type", "site"),
        ],
      },
      {
        id: "inventory-a",
        client_key: "inventory-a",
        item_type: "scope_item",
        environment_item_id: "environment-a",
        values: [profileValue("scope_items", "name", "Name", "Workstation A only")],
      },
      {
        id: "inventory-b",
        client_key: "inventory-b",
        item_type: "scope_item",
        environment_item_id: "environment-b",
        values: [profileValue("scope_items", "name", "Name", "Firewall B only")],
      },
    ],
  };
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/profile")) {
      return Response.json({ ...profile, versions: [twoEnvironmentVersion] });
    }
    if (url.endsWith("/evidence")) return Response.json([]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  render(<ProfilePanel projectId="project-1" />);
  const cloudCard = (await screen.findAllByDisplayValue("Cloud A"))[0].closest(
    ".profile-item-card",
  );
  const siteCard = screen.getAllByDisplayValue("Site B")[0].closest(".profile-item-card");
  expect(cloudCard?.querySelector('input[value="Workstation A only"]')).not.toBeNull();
  expect(cloudCard?.querySelector('input[value="Firewall B only"]')).toBeNull();
  expect(siteCard?.querySelector('input[value="Firewall B only"]')).not.toBeNull();
  expect(siteCard?.querySelector('input[value="Workstation A only"]')).toBeNull();
  expect(screen.queryByRole("option", { name: "Unassigned" })).not.toBeInTheDocument();
});

test("late save and lifecycle responses from Project A never overwrite Project B", async () => {
  const save = deferredResponse();
  const lifecycle = deferredResponse();
  const projectB = {
    ...profile,
    project_id: "project-2",
    versions: [
      {
        ...version,
        id: "project-2-v1",
        project_id: "project-2",
        values: [
          profileValue("project_metadata", "name", "Name", "Project B remains visible"),
        ],
      },
    ],
  };
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/projects/project-1/profile") return Response.json(profile);
    if (url === "/api/projects/project-1/evidence") return Response.json([]);
    if (url === "/api/projects/project-2/profile") return Response.json(projectB);
    if (url === "/api/projects/project-2/evidence") return Response.json([]);
    if (url.includes("/projects/project-1/profile/versions/") && init?.method === "PUT") {
      return save.promise;
    }
    if (url.endsWith("/lifecycle") && init?.method === "POST") return lifecycle.promise;
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const user = userEvent.setup();
  const { rerender } = render(<ProfilePanel projectId="project-1" />);
  await screen.findByDisplayValue("Synthetic program");
  await user.click(screen.getByRole("button", { name: "Save draft" }));
  rerender(<ProfilePanel projectId="project-2" />);
  expect(await screen.findByDisplayValue("Project B remains visible")).toBeVisible();
  save.resolve(Response.json({ ...version, values: [
    profileValue("project_metadata", "name", "Name", "LEAKED SAVE"),
  ] }));
  await waitFor(() =>
    expect(screen.getByDisplayValue("Project B remains visible")).toBeVisible()
  );
  expect(screen.queryByDisplayValue("LEAKED SAVE")).not.toBeInTheDocument();

  rerender(<ProfilePanel projectId="project-1" />);
  await screen.findByDisplayValue("Synthetic program");
  await user.type(screen.getByLabelText("Lifecycle reviewer"), "Johnathan");
  await user.click(screen.getByRole("button", { name: "Record review" }));
  rerender(<ProfilePanel projectId="project-2" />);
  await screen.findByDisplayValue("Project B remains visible");
  lifecycle.resolve(Response.json({
    active_version_id: null,
    version: { ...version, status: "Reviewed", values: [
      profileValue("project_metadata", "name", "Name", "LEAKED LIFECYCLE"),
    ] },
  }));
  await waitFor(() =>
    expect(screen.getByDisplayValue("Project B remains visible")).toBeVisible()
  );
  expect(screen.queryByDisplayValue("LEAKED LIFECYCLE")).not.toBeInTheDocument();
});

test("late reuse, upload, and successor responses cannot enter another project", async () => {
  const reuse = deferredResponse();
  const upload = deferredResponse();
  const successor = deferredResponse();
  const projectB = {
    ...profile,
    project_id: "project-2",
    versions: [{
      ...version,
      id: "project-2-v1",
      project_id: "project-2",
      values: [profileValue("project_metadata", "name", "Name", "Safe Project B")],
    }],
  };
  let projectAApproved = false;
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url === "/api/projects/project-1/profile") {
      return Response.json(
        projectAApproved
          ? {
              ...profile,
              active_version_id: version.id,
              versions: [{ ...version, status: "Approved" }],
            }
          : profile,
      );
    }
    if (url === "/api/projects/project-1/evidence") return Response.json([artifact]);
    if (url === "/api/projects/project-2/profile") return Response.json(projectB);
    if (url === "/api/projects/project-2/evidence") return Response.json([]);
    if (url.endsWith("/evidence-mappings") && init?.method === "POST") return reuse.promise;
    if (url.endsWith("/evidence") && init?.method === "POST") return upload.promise;
    if (url.endsWith("/profile/versions") && init?.method === "POST") return successor.promise;
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const user = userEvent.setup();
  const { rerender } = render(<ProfilePanel projectId="project-1" />);
  await screen.findByRole("option", { name: "existing.txt" });
  await user.selectOptions(screen.getByLabelText("Immutable evidence version"), artifact.id);
  await user.selectOptions(
    screen.getByLabelText("Reuse target"),
    "field:project_metadata:delivery_context",
  );
  await user.type(screen.getByLabelText("Reuse rationale"), "Delayed reuse.");
  await user.click(screen.getByRole("button", { name: "Map existing version" }));
  rerender(<ProfilePanel projectId="project-2" />);
  await screen.findByDisplayValue("Safe Project B");
  reuse.resolve(Response.json({
    mapping_id: "leaked-reuse",
    artifact_id: artifact.id,
    uploaded_file_id: "upload-1",
    name: "LEAKED REUSE",
    evidence_version_id: artifact.version_id,
    version_number: 1,
    sha256: "leak",
    relative_path: "leak",
    target_type: "profile",
    target_key: "field:project_metadata:name",
    rationale: "leak",
    review_state: "Not reviewed",
    created_at: "2026-08-26T00:00:00Z",
  }));
  await waitFor(() => expect(screen.getByDisplayValue("Safe Project B")).toBeVisible());
  expect(screen.queryByText("LEAKED REUSE")).not.toBeInTheDocument();

  rerender(<ProfilePanel projectId="project-1" />);
  await screen.findByLabelText("New sanitized Profile file");
  await user.upload(
    screen.getByLabelText("New sanitized Profile file"),
    new File(["safe"], "safe.txt", { type: "text/plain" }),
  );
  await user.selectOptions(
    screen.getByLabelText("Upload target"),
    "field:project_metadata:delivery_context",
  );
  await user.type(screen.getByLabelText("Upload rationale"), "Delayed upload.");
  await user.click(screen.getByRole("button", { name: "Upload and map" }));
  rerender(<ProfilePanel projectId="project-2" />);
  await screen.findByDisplayValue("Safe Project B");
  upload.resolve(Response.json({
    artifact: { ...artifact, id: "leaked-artifact", name: "LEAKED UPLOAD" },
    mapping: {
      mapping_id: "leaked-upload",
      artifact_id: "leaked-artifact",
      uploaded_file_id: "leaked-file",
      name: "LEAKED UPLOAD",
      evidence_version_id: "leaked-version",
      version_number: 1,
      sha256: "leak",
      relative_path: "leak",
      target_type: "profile",
      target_key: "field:project_metadata:name",
      rationale: "leak",
      review_state: "Not reviewed",
      created_at: "2026-08-26T00:00:00Z",
    },
  }));
  await waitFor(() => expect(screen.getByDisplayValue("Safe Project B")).toBeVisible());
  expect(screen.queryByText("LEAKED UPLOAD")).not.toBeInTheDocument();

  projectAApproved = true;
  rerender(<ProfilePanel projectId="project-1" />);
  await screen.findByRole("button", { name: "Create new version" });
  await user.click(screen.getByRole("button", { name: "Create new version" }));
  rerender(<ProfilePanel projectId="project-2" />);
  await screen.findByDisplayValue("Safe Project B");
  successor.resolve(Response.json({
    ...version,
    id: "leaked-successor",
    version_number: 2,
    values: [profileValue("project_metadata", "name", "Name", "LEAKED SUCCESSOR")],
  }));
  await waitFor(() => expect(screen.getByDisplayValue("Safe Project B")).toBeVisible());
  expect(screen.queryByDisplayValue("LEAKED SUCCESSOR")).not.toBeInTheDocument();
});

test("dirty Draft A cannot be silently abandoned through Profile version switching", async () => {
  const draftTwo = {
    ...version,
    id: "profile-v2",
    version_number: 2,
    content_revision: "revision-2",
    values: [
      profileValue("project_metadata", "delivery_context", "Delivery context", "Draft B"),
    ],
  };
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/profile")) {
      return Response.json({ ...profile, versions: [version, draftTwo] });
    }
    if (url.endsWith("/evidence")) return Response.json([]);
    if (url.endsWith("/profile/versions/profile-v2") && init?.method === "PUT") {
      const body = JSON.parse(String(init.body)) as { values: typeof draftTwo.values };
      return Response.json({
        ...draftTwo,
        content_revision: "revision-3",
        values: body.values,
      });
    }
    return Response.json({ detail: "not found" }, { status: 404 });
  });
  const confirm = vi.spyOn(window, "confirm").mockReturnValue(false);
  const onDirtyChange = vi.fn();
  const user = userEvent.setup();
  render(<ProfilePanel projectId="project-1" onDirtyChange={onDirtyChange} />);
  const draftA = await screen.findByDisplayValue("Synthetic program");
  await user.clear(draftA);
  await user.type(draftA, "Unsaved Draft A");
  await user.selectOptions(screen.getByLabelText("Profile version"), "profile-v2");
  expect(confirm).toHaveBeenCalled();
  expect(screen.getByDisplayValue("Unsaved Draft A")).toBeVisible();
  expect(screen.queryByDisplayValue("Draft B")).not.toBeInTheDocument();
  confirm.mockReturnValue(true);
  await user.selectOptions(screen.getByLabelText("Profile version"), "profile-v2");
  expect(await screen.findByDisplayValue("Draft B")).toBeVisible();
  const draftB = screen.getByDisplayValue("Draft B");
  await user.clear(draftB);
  await user.type(draftB, "Saved Draft B");
  await user.click(screen.getByRole("button", { name: "Save draft" }));
  expect(await screen.findByText("Draft saved with provenance.")).toBeVisible();
  await waitFor(() => expect(onDirtyChange).toHaveBeenLastCalledWith(false));
});

test("Profile evidence target selectors expose each canonical identity exactly once", async () => {
  const duplicatedTargets = {
    ...version,
    values: [
      ...version.values,
      {
        ...version.values[0],
        id: "duplicate-value",
        label: "Duplicate display row",
      },
    ],
  };
  vi.mocked(fetch).mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/profile")) {
      return Response.json({ ...profile, versions: [duplicatedTargets] });
    }
    if (url.endsWith("/evidence")) return Response.json([artifact]);
    return Response.json({ detail: "not found" }, { status: 404 });
  });

  render(<ProfilePanel projectId="project-1" />);
  await screen.findByRole("option", { name: "existing.txt" });
  const expected = "field:project_metadata:delivery_context";
  const reuseValues = Array.from(
    (screen.getByLabelText("Reuse target") as HTMLSelectElement).options,
    (option) => option.value,
  );
  const uploadValues = Array.from(
    (screen.getByLabelText("Upload target") as HTMLSelectElement).options,
    (option) => option.value,
  );
  expect(reuseValues.filter((value) => value === expected)).toHaveLength(1);
  expect(uploadValues.filter((value) => value === expected)).toHaveLength(1);
});
