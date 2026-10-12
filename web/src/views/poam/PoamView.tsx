import { CircleAlert, LoaderCircle } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { request } from "../../api";
import "./poam.css";

/**
 * POA&M (CMMC) or corrective actions (HIPAA): one list of every item in the
 * project. Read-only. Counts are progress, never blockers. A row opens its
 * requirement in the Assessments view, where the item is edited.
 */

export type PoamEligibility = { state: "eligible" | "not_eligible" | "not_applicable"; reason: string };

export type PoamItem = {
  id: string;
  /** Null when the action is no longer linked to a record (a HIPAA reconciliation was changed). */
  record_id: string | null;
  linked: boolean;
  citation: string;
  requirement_title: string;
  work_area: string;
  requirement_status: string;
  title: string;
  description: string;
  status: string;
  status_label: string;
  group: "open" | "draft" | "closed" | "withdrawn";
  status_rank: number;
  weight: number | null;
  eligibility: PoamEligibility;
  closure_rationale: string | null;
  closed_at: string | null;
  updated_at: string;
};

export type PoamList = {
  variant: "cmmc" | "hipaa";
  item_label: string;
  scored: boolean;
  items: PoamItem[];
  counts: { open: number; draft: number; closed: number; withdrawn: number; ready_for_validation: number; total: number };
  work_areas: string[];
  not_met_count: number;
  not_met_without_plan: { count: number; requirement_ids: string[]; not_needed_count: number };
  missing_fields: string[];
};

const AREA_NAMES: Record<string, string> = {
  AC: "Access Control",
  AT: "Awareness and Training",
  AU: "Audit and Accountability",
  CM: "Configuration Management",
  IA: "Identification and Authentication",
  IR: "Incident Response",
  MA: "Maintenance",
  MP: "Media Protection",
  PS: "Personnel Security",
  PE: "Physical Protection",
  RA: "Risk Assessment",
  CA: "Security Assessment",
  SC: "System and Communications Protection",
  SI: "System and Information Integrity",
  security: "Security Rule",
  privacy: "Privacy Rule",
  breach: "Breach Notification Rule",
};

const STATUS_OPTIONS: [string, string][] = [
  ["Open", "Open"],
  ["In Progress", "In progress"],
  ["Waiting", "Waiting"],
  ["Ready for Validation", "Ready for validation"],
  ["Draft", "Draft"],
  ["Closed", "Closed"],
  ["Withdrawn", "Withdrawn"],
];

type Sort = "default" | "requirement" | "points" | "status" | "title";

const areaName = (area: string) => AREA_NAMES[area] ?? area;
const pillClass = (item: PoamItem) => (item.status === "Ready for Validation" ? "ready" : item.group);

export function PoamView({
  projectId,
  assessmentId,
  refreshKey = "",
  onOpenRecord,
  onOpenGap,
}: {
  projectId: string;
  assessmentId: string;
  refreshKey?: string;
  /** Opens the item's requirement (or HIPAA record) in the Assessments view. */
  onOpenRecord: (recordId: string) => void;
  /** Opens Assessments narrowed to the records with no open plan. */
  onOpenGap?: (label: string, recordIds: string[]) => void;
}) {
  const [data, setData] = useState<PoamList | null>(null);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("all");
  const [eligibility, setEligibility] = useState("all");
  const [area, setArea] = useState("all");
  const [sort, setSort] = useState<Sort>("default");

  useEffect(() => {
    let current = true;
    request<PoamList>(`/api/projects/${projectId}/assessments/${assessmentId}/poam-items`)
      .then((next) => current && setData(next))
      .catch((caught) => current && setError(caught instanceof Error ? caught.message : "Could not load the POA&M list."));
    return () => {
      current = false;
    };
  }, [projectId, assessmentId, refreshKey]);

  const shown = useMemo(() => {
    if (!data) return [];
    const needle = search.trim().toLowerCase();
    const rows = data.items.filter(
      (item) =>
        (status === "all" || item.status === status) &&
        (eligibility === "all" || item.eligibility.state === eligibility) &&
        (area === "all" || item.work_area === area) &&
        // Only what the row shows: the id and citation, the requirement and item titles, the status,
        // the eligibility reason and the closure rationale.
        (!needle || [item.record_id ?? "", item.citation, item.requirement_title, item.title, item.status_label, item.eligibility.reason, item.closure_rationale ?? ""].some((text) => text.toLowerCase().includes(needle))),
    );
    const order = (a: PoamItem, b: PoamItem) => {
      if (sort === "requirement") return (a.record_id ?? "~").localeCompare(b.record_id ?? "~", undefined, { numeric: true });
      if (sort === "points") return (b.weight ?? -1) - (a.weight ?? -1);
      // Workflow order: Draft, Open, In progress, Waiting, Ready for validation, Closed, Withdrawn.
      if (sort === "status") return a.status_rank - b.status_rank;
      if (sort === "title") return a.title.localeCompare(b.title);
      return 0;
    };
    // Array.prototype.sort is stable, so "default" keeps the server's order.
    return [...rows].sort(order);
  }, [data, search, status, eligibility, area, sort]);

  if (!data) {
    return (
      <main className="overview-panel poam-view">
        {error ? <p className="form-error"><CircleAlert size={16} /> {error}</p> : <p className="muted"><LoaderCircle className="spin" size={14} /> Loading…</p>}
      </main>
    );
  }

  const cmmc = data.variant === "cmmc";
  const heading = cmmc ? "POA&M" : "Corrective actions";
  const { count: gap, not_needed_count: notNeeded, requirement_ids: gapIds } = data.not_met_without_plan;
  const progress = [`${data.counts.open} open${data.counts.draft ? ` (${data.counts.draft} draft)` : ""}`, `${data.counts.closed} closed`];
  if (data.counts.withdrawn) progress.push(`${data.counts.withdrawn} withdrawn`);
  // The pill says nothing when nothing is Not Met, and never claims "every" when some were marked Not needed.
  const gapNoun = cmmc ? "a POA&M" : "an open corrective action";
  const gapLabel = gap > 0
    ? `${gap} Not Met without ${gapNoun}${!cmmc && notNeeded ? ` (${notNeeded} marked Not needed)` : ""}`
    : data.not_met_count === 0
      ? ""
      : cmmc
        ? "Every Not Met requirement has a POA&M"
        : notNeeded
          ? `No Not Met without an open corrective action (${notNeeded} marked Not needed)`
          : "Every Not Met record has an open corrective action";
  const present = new Set(data.items.map((item) => item.status));

  return (
    <main className="overview-panel poam-view" aria-label={heading}>
      <div className="overview-heading">
        <div>
          <p className="eyebrow">{cmmc ? "PLAN OF ACTION AND MILESTONES" : "REMEDIATION"}</p>
          <h1>{heading}</h1>
          <p>
            {cmmc
              ? "Every POA&M item across this project's requirements. Click a row to open its requirement and work on the item there."
              : "Every corrective action across this project's standards. Click a row to open its record and work on the action there."}
          </p>
          <div className="poam-progress" aria-label="Progress">
            <strong>{progress.join(" · ")}</strong>
            {gapLabel && gap > 0 && onOpenGap ? (
              <button
                type="button"
                className="poam-gap"
                title="Show these in Assessments"
                onClick={() => onOpenGap(`Not Met without ${gapNoun}`, gapIds)}
              >
                {gapLabel}
              </button>
            ) : gapLabel ? (
              <span className={`poam-gap ${gap ? "" : "none"}`}>{gapLabel}</span>
            ) : null}
          </div>
        </div>
      </div>

      {error && <p className="form-error"><CircleAlert size={16} /> {error}</p>}

      <div className="poam-toolbar">
        <label>
          Search
          <input type="search" aria-label="Search items" placeholder="Citation, title or text" value={search} onChange={(event) => setSearch(event.target.value)} />
        </label>
        <label>
          Status
          <select aria-label="Filter by status" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="all">All statuses</option>
            {STATUS_OPTIONS.filter(([value]) => present.has(value)).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
          </select>
        </label>
        {data.scored && (
          <label>
            32 CFR 170.21
            <select aria-label="Filter by eligibility" value={eligibility} onChange={(event) => setEligibility(event.target.value)}>
              <option value="all">Any eligibility</option>
              <option value="eligible">Eligible</option>
              <option value="not_eligible">Not eligible</option>
              <option value="not_applicable">Not applicable</option>
            </select>
          </label>
        )}
        <label>
          {cmmc ? "Family" : "Rule"}
          <select aria-label="Filter by work area" value={area} onChange={(event) => setArea(event.target.value)}>
            <option value="all">{cmmc ? "All families" : "All rules"}</option>
            {data.work_areas.map((value) => <option key={value} value={value}>{areaName(value)}</option>)}
          </select>
        </label>
        <label>
          Sort by
          <select aria-label="Sort by" value={sort} onChange={(event) => setSort(event.target.value as Sort)}>
            <option value="default">Needs attention first</option>
            <option value="requirement">{cmmc ? "Requirement" : "Citation"}</option>
            {data.scored && <option value="points">Points (highest first)</option>}
            <option value="status">Status</option>
            <option value="title">Title</option>
          </select>
        </label>
        <span className="poam-shown">Showing {shown.length} of {data.counts.total}</span>
      </div>

      {data.items.length === 0 ? (
        <p className="poam-empty">
          {cmmc
            ? "No POA&M items yet. Open a NOT MET requirement in Assessments and draft one from its finding."
            : "No corrective actions yet. Saving a Not Met record in Assessments offers to create one."}
        </p>
      ) : shown.length === 0 ? (
        <p className="poam-empty">Nothing matches these filters.</p>
      ) : (
        <table className="poam-table">
          <thead>
            <tr>
              <th>{cmmc ? "Requirement" : "Standard"}</th>
              <th>{cmmc ? "POA&M item" : "Corrective action"}</th>
              <th>Status</th>
              {data.scored && <th>Points</th>}
              {data.scored && <th>32 CFR 170.21</th>}
            </tr>
          </thead>
          <tbody>
            {shown.map((item) => (
              <tr key={item.id} className={`poam-row ${item.group} ${item.record_id ? "" : "unlinked"}`} onClick={() => item.record_id && onOpenRecord(item.record_id)}>
                <td>
                  {item.record_id ? (
                    <>
                      <button type="button" className="poam-open" aria-label={`Open ${item.record_id}`} onClick={(event) => { event.stopPropagation(); onOpenRecord(item.record_id as string); }}>
                        {item.record_id}
                      </button>
                      <small>{item.requirement_title}</small>
                    </>
                  ) : (
                    <small title="Its record was marked Not needed or points to another action. It is still counted as open work.">{item.citation}</small>
                  )}
                </td>
                <td>
                  <strong>{item.title}</strong>
                  {item.group === "closed" && item.closure_rationale && <small className="poam-closure">Closed: {item.closure_rationale}</small>}
                </td>
                <td><span className={`poam-pill ${pillClass(item)}`}>{item.status_label}</span></td>
                {data.scored && <td>{item.weight ?? "—"}</td>}
                {data.scored && (
                  <td>
                    <span className={`poam-elig ${item.eligibility.state}`}>
                      {{ eligible: "Eligible", not_eligible: "Not eligible", not_applicable: "Not applicable" }[item.eligibility.state]}
                    </span>
                    {item.eligibility.reason && <small>{item.eligibility.reason}</small>}
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {data.missing_fields.length > 0 && (
        <p className="poam-note">Owner and due date are not recorded on these items yet, so there is no overdue or due-soon view.</p>
      )}
    </main>
  );
}
