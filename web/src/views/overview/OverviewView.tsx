import { ArrowRight } from "lucide-react";
import { useEffect, useState } from "react";

import { request } from "../../api";
import type { BlockerGroup, CloseReadiness, OverviewData, PoamState } from "../../types";
import { CmmcScorePanel } from "../assessment/CmmcScore";

/**
 * Overview (#144): where the engagement stands, as counts. It never lists
 * blockers one by one; each grouped count opens the matching filtered list.
 */

const FAMILY_NAMES: Record<string, string> = {
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
};

const RULE_NAMES: Record<string, string> = {
  security: "Security Rule",
  privacy: "Privacy Rule",
  breach: "Breach Notification Rule",
};

const POAM_LABELS: Record<PoamState, string> = {
  none: "No POA&M",
  draft: "POA&M draft",
  open: "POA&M open",
  closed: "POA&M closed",
};

/** The NOT MET list scrolls and is capped so a large gap list stays one block. */
const NOT_MET_CAP = 100;

export interface OverviewProps {
  projectId: string;
  assessmentId: string;
  projectName: string;
  clientName: string;
  frameworkName: string;
  /** CMMC declares official scoring; HIPAA shows counts, never a score. */
  scored: boolean;
  /** Change to reload after the work underneath changed. */
  refreshKey: unknown;
  onOpenStep: (target: string) => void;
  onOpenGroup: (group: BlockerGroup) => void;
  onOpenRecord: (recordId: string) => void;
  /** The engagement's other client projects, so switching stays one click away. */
  otherProjects?: { id: string; name: string; clientName: string; framework: string }[];
  onOpenProject?: (projectId: string) => void;
}

function EveryItem({ projectId, assessmentId }: { projectId: string; assessmentId: string }) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<string[] | null>(null);
  useEffect(() => {
    if (!open || items) return;
    const controller = new AbortController();
    request<CloseReadiness>(`/api/projects/${projectId}/assessments/${assessmentId}/close-readiness`, { signal: controller.signal })
      .then((next) => setItems((next.blockers ?? []).map((blocker) => (typeof blocker === "string" ? blocker : String(blocker.detail ?? "")))))
      .catch(() => setItems([]));
    return () => controller.abort();
  }, [open, items, projectId, assessmentId]);
  return (
    <div className="every-item">
      <button type="button" className="text-button" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
        {open ? "Hide every item" : "Show every item"}
      </button>
      {open && (items === null ? <p className="muted-small">Loading…</p> : (
        <ul className="every-item-list">{items.map((detail, index) => <li key={index}>{detail}</li>)}</ul>
      ))}
    </div>
  );
}

export function OverviewView(props: OverviewProps) {
  const { projectId, assessmentId, refreshKey } = props;
  const [data, setData] = useState<OverviewData | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    setError("");
    request<OverviewData>(`/api/projects/${projectId}/assessments/${assessmentId}/overview`, { signal: controller.signal })
      .then((next) => { if (!controller.signal.aborted) setData(next); })
      .catch((caught) => {
        if (!controller.signal.aborted) setError(caught instanceof Error ? caught.message : "Could not load the overview.");
      });
    return () => controller.abort();
  }, [projectId, assessmentId, refreshKey]);

  const steps = data?.steps ?? [];
  const groups = data?.left_before_issue?.groups ?? [];
  const notMet = data?.not_met ?? [];
  const hipaa = data?.variant === "hipaa";

  return (
    <main className="overview-panel overview-dashboard">
      <div className="overview-heading">
        <div>
          <p className="eyebrow">PROJECT OVERVIEW</p>
          <h1>{props.clientName} · {props.projectName}</h1>
          <p>{props.frameworkName}</p>
        </div>
      </div>
      {error && <p className="error-copy" role="alert">{error}</p>}

      {steps.length > 0 && (
        <nav className="step-rail" aria-label="Engagement steps">
          {steps.map((step, index) => (
            <button key={step.label} type="button" onClick={() => props.onOpenStep(step.target)}>
              <span className="step-number" aria-hidden="true">{index + 1}</span>
              <span className="step-text"><strong>{step.label}</strong><small>{step.figure}</small></span>
            </button>
          ))}
        </nav>
      )}

      {props.scored && <CmmcScorePanel projectId={projectId} assessmentId={assessmentId} refreshKey={`${refreshKey}`} />}

      {data && !hipaa && data.families.length > 0 && (
        <section className="overview-section family-table" aria-label="Progress by family">
          <div className="section-title"><h2>Progress by family</h2><span>{data.families.length} families</span></div>
          <table>
            <thead><tr><th>Family</th><th>Objectives decided</th><th aria-label="Progress" /><th>NOT MET requirements</th></tr></thead>
            <tbody>
              {data.families.map((family) => (
                <tr key={family.name}>
                  <th scope="row">{FAMILY_NAMES[family.name] ?? family.name} <small>{family.name}</small></th>
                  <td>{family.decided} of {family.total}</td>
                  <td><span className="family-bar" aria-hidden="true"><i style={{ width: `${family.total ? Math.round((family.decided / family.total) * 100) : 0}%` }} /></span></td>
                  <td className={family.not_met > 0 ? "has-not-met" : ""}>{family.not_met}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {data && hipaa && (data.status_counts ?? []).length > 0 && (
        <section className="overview-section family-table" aria-label="Status by rule">
          <div className="section-title"><h2>Status by rule</h2></div>
          <table>
            <thead>
              <tr><th>Rule</th>{Object.keys(data.status_counts![0].counts).map((status) => <th key={status}>{status}</th>)}</tr>
            </thead>
            <tbody>
              {data.status_counts!.map((entry) => (
                <tr key={entry.rule}>
                  <th scope="row">{RULE_NAMES[entry.rule] ?? entry.rule}</th>
                  {Object.entries(entry.counts).map(([status, count]) => <td key={status}>{count}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}

      {data && !hipaa && (
        <section className="overview-section not-met-section" aria-label="NOT MET requirements">
          <div className="section-title"><h2>NOT MET requirements</h2><span>{notMet.length}</span></div>
          {notMet.length === 0 ? (
            <p className="muted-small">No requirement is NOT MET.</p>
          ) : (
            <>
              <ul className="not-met-list">
                {notMet.slice(0, NOT_MET_CAP).map((item) => (
                  <li key={item.record_id}>
                    <button type="button" onClick={() => props.onOpenRecord(item.record_id)}>
                      <small>{item.record_id}</small>
                      <strong>{item.title}</strong>
                      <span className={`poam-state ${item.poam_state}`}>{POAM_LABELS[item.poam_state]}</span>
                    </button>
                  </li>
                ))}
              </ul>
              {notMet.length > NOT_MET_CAP && <p className="muted-small">Showing the first {NOT_MET_CAP} of {notMet.length}. Open Assessments for the rest.</p>}
            </>
          )}
        </section>
      )}

      {data && (
        <section className="overview-section left-before-issue" aria-label="Left before issue">
          <div className="section-title"><h2>Left before issue</h2><span>{data.left_before_issue.ready ? "Ready" : `${data.left_before_issue.count} ${data.left_before_issue.count === 1 ? "item" : "items"}`}</span></div>
          {groups.length === 0 ? (
            <p className="muted-small">Nothing is left. The assessment is ready to issue.</p>
          ) : (
            <ul className="group-counts">
              {groups.map((group) => (
                <li key={group.key}>
                  <button type="button" onClick={() => props.onOpenGroup(group)} aria-label={`${group.label}: ${group.count}`}>
                    <strong>{group.count}</strong>
                    <span>{group.label}</span>
                    <ArrowRight size={14} aria-hidden="true" />
                  </button>
                </li>
              ))}
            </ul>
          )}
          <EveryItem projectId={projectId} assessmentId={assessmentId} />
        </section>
      )}

      {data && (
        <section className="overview-section resume-card" aria-label="Continue where you left off">
          <div>
            <p className="eyebrow">CONTINUE WHERE YOU LEFT OFF</p>
            {data.resume ? (
              <>
                <h2>{data.resume.title}</h2>
                <p className="muted-small">{data.resume.record_id}</p>
              </>
            ) : (
              <>
                <h2>Nothing decided yet</h2>
                <p className="muted-small">Start with the first requirement.</p>
              </>
            )}
          </div>
          <button type="button" className="small-button" onClick={() => (data.resume ? props.onOpenRecord(data.resume.record_id) : props.onOpenStep("assessments"))}>
            {data.resume ? "Continue" : "Start assessing"} <ArrowRight size={15} />
          </button>
        </section>
      )}
      {(props.otherProjects ?? []).length > 0 && (
        <section className="overview-section other-projects" aria-label="Other client projects">
          <div className="section-title"><h2>Other client projects</h2><span>{props.otherProjects!.length}</span></div>
          <ul>
            {props.otherProjects!.map((project) => (
              <li key={project.id}>
                <button type="button" onClick={() => props.onOpenProject?.(project.id)}>
                  <strong>{project.clientName}</strong>
                  <span>{project.name}</span>
                  <small>{project.framework}</small>
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}
