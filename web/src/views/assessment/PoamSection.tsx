import { CircleAlert, ListPlus, TriangleAlert } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { request } from "../../api";
import type { NotMetWithoutPoam, RequirementFinding } from "../../types";

type PoamItem = RequirementFinding["poam_items"][number];

/** Closed and Withdrawn items no longer plan the requirement (#143). */
const TERMINAL = new Set(["Closed", "Withdrawn"]);

/** 32 CFR 170.21 eligibility, read from the requirement's score deduction line (#141). */
export interface PoamEligibility {
  allowed: boolean;
  reason: string;
}

/**
 * POA&M items for one CMMC requirement finding (#143).
 *
 * A NOT MET requirement gets its POA&M draft in one click, prefilled by the
 * server from the requirement-level finding. Nothing is ever created by a
 * determination change. A requirement already on an open item cannot get a
 * second draft. A requirement 32 CFR 170.21 does not allow on a POA&M is
 * warned about, never blocked.
 */
export function PoamSection({
  base,
  finding,
  eligibility,
  onFinding,
  onChanged,
}: {
  /** `/api/projects/{p}/assessments/{a}/requirements/{record}` */
  base: string;
  finding: RequirementFinding;
  eligibility: PoamEligibility | null;
  onFinding: (finding: RequirementFinding) => void;
  onChanged: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [createdId, setCreatedId] = useState("");
  const notMet = finding.requirement_status === "Not Met";
  const open = finding.poam_items.filter((item) => !TERMINAL.has(item.status));

  async function createDraft() {
    if (busy) return;
    setBusy(true);
    setError("");
    const before = new Set(finding.poam_items.map((item) => item.id));
    try {
      const next = await request<RequirementFinding>(`${base}/poam`, { method: "POST", body: JSON.stringify({ draft: true }) });
      onFinding(next);
      setCreatedId(next.poam_items.find((item) => !before.has(item.id))?.id ?? "");
      onChanged();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not create the POA&M draft.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="poam-section" aria-label="POA&M items" role="group">
      <strong>POA&amp;M items</strong>
      {notMet && eligibility && !eligibility.allowed && (
        <p className="poam-eligibility-warning" role="note">
          <TriangleAlert size={14} />
          <span>
            <strong>32 CFR 170.21: cannot stay on a POA&amp;M for Conditional status.</strong>{" "}
            {eligibility.reason} A POA&amp;M item can still track the remediation; the requirement must be verified Met for Conditional Level 2.
          </span>
        </p>
      )}
      {finding.poam_items.length === 0 ? <p className="muted">None yet.</p> : (
        <ul className="poam-items">
          {finding.poam_items.map((item) => (
            <PoamItemRow
              key={item.id}
              base={base}
              item={item}
              autoFocus={item.id === createdId}
              requirementMet={finding.requirement_status === "Met"}
              onFinding={onFinding}
              onChanged={onChanged}
            />
          ))}
        </ul>
      )}
      {notMet && (
        <div className="poam-create">
          <button
            type="button"
            className="small-button"
            disabled={busy || open.length > 0}
            onClick={() => void createDraft()}
          >
            <ListPlus size={14} /> {busy ? "Creating…" : "Create POA&M draft"}
          </button>
          <span className="muted-small">
            {open.length > 0
              ? `Already on POA&M item “${open[0].title}” (${open[0].status}).`
              : "Prefilled from this finding: failed objectives, notes and evidence. Starts as Draft."}
          </span>
        </div>
      )}
      {error && <p className="form-error"><CircleAlert size={16} /> {error}</p>}
    </div>
  );
}

function PoamItemRow({
  base,
  item,
  autoFocus,
  requirementMet,
  onFinding,
  onChanged,
}: {
  base: string;
  item: PoamItem;
  autoFocus: boolean;
  requirementMet: boolean;
  onFinding: (finding: RequirementFinding) => void;
  onChanged: () => void;
}) {
  const [title, setTitle] = useState(item.title);
  const [description, setDescription] = useState(item.description);
  const [closing, setClosing] = useState(false);
  const [rationale, setRationale] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const titleRef = useRef<HTMLInputElement>(null);
  useEffect(() => {
    if (autoFocus) titleRef.current?.focus();
  }, [autoFocus]);

  async function send(path: string, init: RequestInit, failure: string) {
    setBusy(true);
    setError("");
    try {
      onFinding(await request<RequirementFinding>(path, init));
      onChanged();
      return true;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : failure);
      return false;
    } finally {
      setBusy(false);
    }
  }

  const dirty = title !== item.title || description !== item.description;
  const closable = !TERMINAL.has(item.status) && requirementMet;
  return (
    <li className={`poam-item status-${item.status.toLowerCase().replaceAll(" ", "-")}`}>
      {item.status === "Draft" ? (
        <form
          className="poam-draft"
          aria-label={`POA&M draft ${item.title}`}
          onSubmit={(event) => {
            event.preventDefault();
            void send(`${base}/poam/${item.id}`, { method: "PUT", body: JSON.stringify({ title, description }) }, "Could not save the POA&M draft.");
          }}
        >
          <span className="poam-status">Draft</span>
          <label>Title<input ref={titleRef} value={title} onChange={(event) => setTitle(event.target.value)} required /></label>
          <label>Description<textarea rows={6} value={description} onChange={(event) => setDescription(event.target.value)} /></label>
          <div className="statement-actions">
            <button className="small-button" type="submit" disabled={busy || !dirty || !title.trim()}>{busy ? "Saving…" : "Save draft"}</button>
            <span className="muted-small">{dirty ? "Unsaved changes." : "Saved."}</span>
          </div>
        </form>
      ) : (
        <span>{item.title} · {item.status}</span>
      )}
      {closable && !closing && (
        <button type="button" className="text-button" onClick={() => setClosing(true)}>Close item</button>
      )}
      {closable && closing && (
        <form
          className="reconciliation-form"
          onSubmit={(event) => {
            event.preventDefault();
            void send(`${base}/poam/${item.id}/close`, { method: "POST", body: JSON.stringify({ rationale }) }, "Could not close the POA&M item.")
              .then((closed) => { if (closed) setClosing(false); });
          }}
        >
          <label>How was the remediation verified? <span className="required">required</span>
            <textarea rows={2} value={rationale} onChange={(event) => setRationale(event.target.value)} required />
          </label>
          <div className="statement-actions">
            <button className="small-button" type="submit" disabled={busy || !rationale.trim()}>Close POA&amp;M item</button>
            <button className="text-button" type="button" onClick={() => setClosing(false)}>Cancel</button>
          </div>
        </form>
      )}
      {error && <p className="form-error"><CircleAlert size={16} /> {error}</p>}
    </li>
  );
}

/**
 * The assessment header's count of NOT MET requirements not on any open
 * POA&M item; pressing it filters the requirement list to them (#143).
 */
export function UnplannedNotMet({
  summary,
  active,
  onToggle,
}: {
  summary: NotMetWithoutPoam;
  active: boolean;
  onToggle: () => void;
}) {
  if (summary.count === 0 && !active) {
    return <span className="unplanned-not-met none" title="Every NOT MET requirement is on an open POA&M item.">0 NOT MET without POA&amp;M</span>;
  }
  return (
    <button
      type="button"
      className={`unplanned-not-met ${summary.count > 0 ? "has-unplanned" : ""}`}
      aria-pressed={active}
      title={active ? "Show every requirement" : "Show only NOT MET requirements not on any open POA&M item"}
      onClick={onToggle}
    >
      <strong>{summary.count}</strong> NOT MET not on a POA&amp;M
    </button>
  );
}
