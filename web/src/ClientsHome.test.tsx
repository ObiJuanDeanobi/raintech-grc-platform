import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, expect, test, vi } from "vitest";

import App from "./App";
import type { HomeCard } from "./views/home/ClientsHome";

/**
 * The Clients home: the first screen when there is more than one project, with one card per
 * client project. With exactly one project the app opens straight into it.
 */

const northwind: HomeCard = {
  project_id: "project-1",
  project_name: "HIPAA 2026",
  client_id: "client-1",
  client_name: "Northwind Health",
  framework_id: "hipaa-45cfr164-2026-07-01",
  framework_name: "HIPAA 45 CFR Part 164",
  variant: "hipaa",
  assessment_started: true,
  progress: { decided: 50, total: 200, percent: 25 },
  verified_sprs: null,
  status_counts: { Met: 40, "Not Met": 10, Pending: 5, Blank: 145 },
  final: { version: 2, issued_at: "2026-10-12T09:30:00+00:00" },
  evidence_expiring: 3,
  evidence_expired: 0,
  evidence_lead_days: 30,
  open_actions: 4,
  last_worked_at: "2026-10-12T09:00:00+00:00",
};

const contoso: HomeCard = {
  ...northwind,
  project_id: "project-2",
  project_name: "CMMC L2 2026",
  client_id: "client-2",
  client_name: "Contoso Defense",
  framework_id: "cmmc-l2-ag-v2.13",
  framework_name: "CMMC Level 2",
  variant: "cmmc",
  progress: { decided: 160, total: 320, percent: 50 },
  verified_sprs: { value: -42, maximum: 110, minimum: 88 },
  status_counts: null,
  final: null,
  evidence_expiring: 0,
  evidence_expired: 2,
  open_actions: 7,
  last_worked_at: "2026-10-10T09:00:00+00:00",
};

const clientList = [
  {
    id: "client-1",
    name: "Northwind Health",
    projects: [{ id: "project-1", name: "HIPAA 2026", framework_version_id: northwind.framework_id }],
  },
  {
    id: "client-2",
    name: "Contoso Defense",
    projects: [{ id: "project-2", name: "CMMC L2 2026", framework_version_id: contoso.framework_id }],
  },
];

let clientsResponse: unknown[] = clientList;
let cards: HomeCard[] = [northwind, contoso];
let requested: string[] = [];

const readiness = (projectId: string) => ({
  project_id: projectId,
  state: "Intake started",
  supported_states: ["Intake started", "Intake complete", "Needs follow-up", "Profile complete"],
  allowed_next_states: ["Intake complete"],
  follow_up_work_required_states: ["Needs follow-up"],
  follow_up_work_required_when_unresolved_required_fields: true,
  profile_completion_blocking_reasons: [],
  current_details: { unresolved_required_fields: [], follow_up_work: "", reviewed_by: "", approval_evidence: "" },
  assessment_exists: false,
  assessment_entry_allowed: true,
  assessment_entry_blocking_reasons: [],
});

beforeEach(() => {
  clientsResponse = clientList;
  cards = [northwind, contoso];
  requested = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      requested.push(url);
      if (url === "/api/frameworks") return Response.json([]);
      if (url === "/api/clients") return Response.json(clientsResponse);
      if (url === "/api/home") return Response.json({ generated_on: "2026-10-12", projects: cards });
      const match = /^\/api\/projects\/(project-\d)\/profile-readiness$/.exec(url);
      if (match) return Response.json(readiness(match[1]));
      if (/^\/api\/projects\/project-\d\/assessment$/.test(url)) {
        return Response.json({ detail: "Assessment not found" }, { status: 404 });
      }
      return Response.json({ detail: "not found" }, { status: 404 });
    }),
  );
});

test("opens on the Clients home when there is more than one project", async () => {
  render(<App />);
  expect(await screen.findByRole("heading", { level: 1, name: "Clients" })).toBeVisible();
  expect(await screen.findByRole("button", { name: /Northwind Health.*HIPAA 2026/ })).toBeVisible();
  expect(screen.getByRole("button", { name: /Contoso Defense.*CMMC L2 2026/ })).toBeVisible();
  expect(screen.getByRole("button", { name: "New client / project" })).toBeVisible();
  expect(requested.some((url) => url.includes("/profile-readiness"))).toBe(false);
});

test("opens straight into the project when there is exactly one", async () => {
  clientsResponse = [clientList[0]];
  render(<App />);
  expect(await screen.findByRole("heading", { name: "Ready to begin" })).toBeVisible();
  expect(screen.queryByRole("heading", { level: 1, name: "Clients" })).not.toBeInTheDocument();
  expect(requested).not.toContain("/api/home");
});

test("each card shows its own figures and never a projected score or blockers", async () => {
  render(<App />);
  const hipaa = within(await screen.findByRole("button", { name: /Northwind Health.*HIPAA 2026/ }));
  expect(hipaa.getByText("50 of 200 decided")).toBeVisible();
  expect(hipaa.getByText("25%")).toBeVisible();
  expect(hipaa.getByText("Final v2 · 12 Oct 2026")).toBeVisible();
  const count = (text: string) => (_: string, element: Element | null) =>
    element?.tagName === "SPAN" && element.textContent?.trim() === text;
  expect(hipaa.getByText(count("40 Met"))).toBeVisible();
  expect(hipaa.getByText(count("145 Not started"))).toBeVisible();
  expect(hipaa.getByText("evidence expiring in 30 days", { exact: false })).toBeVisible();
  expect(hipaa.getByText("corrective actions open", { exact: false })).toBeVisible();
  expect(hipaa.queryByText(/SPRS/)).not.toBeInTheDocument();

  const cmmc = within(screen.getByRole("button", { name: /Contoso Defense.*CMMC L2 2026/ }));
  expect(cmmc.getByText("Verified SPRS score")).toBeVisible();
  expect(cmmc.getByText(/−42/)).toBeVisible();
  expect(cmmc.getByText("No final yet")).toBeVisible();
  expect(cmmc.getByText("evidence expired", { exact: false })).toBeVisible();
  expect(cmmc.getByText("POA&M items open", { exact: false })).toBeVisible();
  expect(cmmc.queryByText("Pending", { exact: false })).not.toBeInTheDocument();

  const page = document.body.textContent ?? "";
  expect(page).not.toMatch(/projected|blocker|left before issue/i);
});

test("cards follow the order the server gives, most recently worked first", async () => {
  render(<App />);
  await screen.findByRole("button", { name: /^Northwind/ });
  const names = screen.getAllByRole("button", { name: /^(Northwind|Contoso)/ }).map((button) => button.textContent?.slice(0, 8));
  expect(names).toEqual(["Northwin", "Contoso "]);
});

test("search narrows the cards by client or project and says when nothing matches", async () => {
  const user = userEvent.setup();
  render(<App />);
  const search = await screen.findByRole("searchbox", { name: "Search clients and projects" });

  await user.type(search, "contoso");
  expect(screen.queryByRole("button", { name: /Northwind/ })).not.toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Contoso/ })).toBeVisible();

  await user.clear(search);
  await user.type(search, "hipaa");
  expect(screen.getByRole("button", { name: /Northwind/ })).toBeVisible();
  expect(screen.queryByRole("button", { name: /Contoso/ })).not.toBeInTheDocument();

  await user.clear(search);
  await user.type(search, "zzz");
  expect(screen.getByText("No client or project matches “zzz”.")).toBeVisible();
});

test("a card opens that project, and the logo and the Clients link return to the home", async () => {
  const user = userEvent.setup();
  render(<App />);
  await user.click(await screen.findByRole("button", { name: /Contoso Defense.*CMMC L2 2026/ }));
  expect(await screen.findByRole("heading", { name: "Ready to begin" })).toBeVisible();
  expect(requested).toContain("/api/projects/project-2/profile-readiness");
  expect(requested).not.toContain("/api/projects/project-1/profile-readiness");

  await user.click(screen.getByRole("button", { name: /RainTech GRC, back to all clients/ }));
  expect(await screen.findByRole("heading", { level: 1, name: "Clients" })).toBeVisible();

  await user.click(screen.getByRole("button", { name: /Northwind Health.*HIPAA 2026/ }));
  expect(await screen.findByRole("heading", { name: "Ready to begin" })).toBeVisible();
  await user.click(screen.getByRole("button", { name: "Clients" }));
  expect(await screen.findByRole("heading", { level: 1, name: "Clients" })).toBeVisible();
});

test("with one project the logo still returns to the home, which then lists that one card", async () => {
  clientsResponse = [clientList[0]];
  cards = [northwind];
  const user = userEvent.setup();
  render(<App />);
  await user.click(await screen.findByRole("button", { name: /back to all clients/ }));
  expect(await screen.findByRole("button", { name: /Northwind Health.*HIPAA 2026/ })).toBeVisible();
});

test("New client / project opens the creator", async () => {
  const user = userEvent.setup();
  render(<App />);
  await user.click(await screen.findByRole("button", { name: "New client / project" }));
  expect(await screen.findByRole("button", { name: /Create and start assessment/ })).toBeVisible();
});

test("a failed load says so and offers to try again", async () => {
  const user = userEvent.setup();
  let failures = 1;
  const base = vi.mocked(fetch).getMockImplementation()!;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input) === "/api/home" && failures-- > 0) {
        return Response.json({ detail: "The home could not be read." }, { status: 500 });
      }
      return base(input, init);
    }),
  );
  render(<App />);
  expect(await screen.findByRole("alert")).toHaveTextContent("The home could not be read.");
  await user.click(screen.getByRole("button", { name: "Try again" }));
  expect(await screen.findByRole("button", { name: /Northwind Health.*HIPAA 2026/ })).toBeVisible();
});

test("a card's accessible name carries its figures, so a screen reader hears them", async () => {
  render(<App />);
  expect(
    await screen.findByRole("button", {
      name: /Contoso Defense.*CMMC L2 2026.*160 of 320 decided.*50%.*Verified SPRS score.*\u221242.*of 110.*provisional.*No final yet.*2 evidence expired.*7 POA&M items open/,
    }),
  ).toBeVisible();
  expect(
    screen.getByRole("button", {
      name: /Northwind Health.*50 of 200 decided.*25%.*40 Met.*Final v2 \u00b7 12 Oct 2026.*3 evidence expiring in 30 days.*4 corrective actions open/,
    }),
  ).toBeVisible();
  // The bar is decoration: a progressbar role inside a button is not valid.
  expect(document.querySelectorAll("button [role='progressbar']")).toHaveLength(0);
});

test("a CMMC project with nothing decided says Not started instead of a score", async () => {
  cards = [{ ...contoso, progress: { decided: 0, total: 320, percent: 0 }, verified_sprs: null }];
  clientsResponse = [clientList[1], clientList[0]];
  render(<App />);
  const card = within(await screen.findByRole("button", { name: /Contoso Defense/ }));
  expect(card.getByText("Not started")).toBeVisible();
  expect(card.queryByText(/of 110/)).not.toBeInTheDocument();
});

test("a project whose framework is unavailable still has a card that says so", async () => {
  cards = [
    northwind,
    {
      ...contoso,
      framework_name: "Framework unavailable",
      variant: "unknown",
      progress: null,
      verified_sprs: null,
      status_counts: null,
    },
  ];
  render(<App />);
  const card = within(await screen.findByRole("button", { name: /Contoso Defense/ }));
  expect(card.getByText("Framework unavailable")).toBeVisible();
  expect(card.queryByText(/SPRS/)).not.toBeInTheDocument();
});

test("the home top bar has no static Saved indicator", async () => {
  render(<App />);
  await screen.findByRole("button", { name: /Contoso Defense/ });
  expect(screen.queryByText("Saved")).not.toBeInTheDocument();
});
