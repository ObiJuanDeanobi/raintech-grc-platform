import { FormEvent, useEffect, useState } from "react";

import { request } from "../api";
import type {
  ProfileReadiness,
} from "../types";

export function ReadinessPanel({
  readiness,
  hasAssessment,
  onChanged,
  onStarted,
}: {
  readiness: ProfileReadiness;
  hasAssessment: boolean;
  onChanged: () => Promise<void>;
  onStarted?: () => void;
}) {
  const [nextState, setNextState] = useState(
    readiness.allowed_next_states[0] ?? "",
  );
  const [decisionNote, setDecisionNote] = useState("");
  const [unresolved, setUnresolved] = useState(
    readiness.current_details.unresolved_required_fields.join(", "),
  );
  const [followUp, setFollowUp] = useState(readiness.current_details.follow_up_work);
  const [reviewedBy, setReviewedBy] = useState(readiness.current_details.reviewed_by);
  const [approvalEvidence, setApprovalEvidence] = useState(
    readiness.current_details.approval_evidence,
  );
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const unresolvedValues = unresolved
    .split(",")
    .map((value) => value.trim())
    .filter(Boolean);
  const followUpRequired = readiness.follow_up_work_required_states.includes(nextState)
    || (
      readiness.follow_up_work_required_when_unresolved_required_fields
      && unresolvedValues.length > 0
    );

  useEffect(() => {
    setNextState(readiness.allowed_next_states[0] ?? "");
    setUnresolved(readiness.current_details.unresolved_required_fields.join(", "));
    setFollowUp(readiness.current_details.follow_up_work);
    setReviewedBy(readiness.current_details.reviewed_by);
    setApprovalEvidence(readiness.current_details.approval_evidence);
  }, [readiness]);

  async function saveTransition(event: FormEvent) {
    event.preventDefault();
    setWorking(true);
    setError("");
    try {
      await request(`/api/projects/${readiness.project_id}/profile-readiness/transitions`, {
        method: "POST",
        body: JSON.stringify({
          next_state: nextState,
          decision_note: decisionNote,
          unresolved_required_fields: unresolvedValues,
          follow_up_work: followUp,
          reviewed_by: reviewedBy,
          approval_evidence: approvalEvidence,
        }),
      });
      setDecisionNote("");
      await onChanged();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Readiness update failed.");
    } finally {
      setWorking(false);
    }
  }

  async function startAssessment() {
    setWorking(true);
    setError("");
    try {
      await request(`/api/projects/${readiness.project_id}/assessments`, { method: "POST" });
      await onChanged();
      onStarted?.();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Assessment creation failed.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <section className="readiness-panel" aria-labelledby="readiness-title">
      <div className="readiness-heading">
        <div>
          <p className="eyebrow">PROJECT PROFILE</p>
          <h1 id="readiness-title">Assessment readiness</h1>
        </div>
        <span className={`readiness-state ${readiness.assessment_entry_allowed ? "ready" : "blocked"}`}>
          {readiness.state}
        </span>
      </div>
      <div className="readiness-grid">
        <article>
          <h2>Assessment entry</h2>
          {readiness.assessment_entry_allowed ? (
            <p className="readiness-ok">This readiness state permits assessment entry.</p>
          ) : (
            <ul className="blocking-reasons">
              {readiness.assessment_entry_blocking_reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          )}
          <button
            className="small-button"
            disabled={working || hasAssessment || !readiness.assessment_entry_allowed}
            onClick={() => void startAssessment()}
          >
            {hasAssessment ? "Assessment already started" : "Start assessment"}
          </button>
        </article>
      </div>
      <form className="readiness-form" onSubmit={(event) => void saveTransition(event)}>
        <div className="section-title">
          <h2>Record readiness decision</h2>
          <span>Append-only history</span>
        </div>
        <div className="readiness-fields">
          <label>
            Next state
            <select value={nextState} onChange={(event) => setNextState(event.target.value)}>
              {readiness.allowed_next_states.map((state) => (
                <option key={state}>{state}</option>
              ))}
            </select>
          </label>
          <label>
            Decision note
            <textarea required rows={2} value={decisionNote} onChange={(event) => setDecisionNote(event.target.value)} />
          </label>
          <label>
            Unresolved required fields <small>comma-separated</small>
            <input value={unresolved} onChange={(event) => setUnresolved(event.target.value)} />
          </label>
          <label>
            Explicit follow-up work
            <textarea
              required={followUpRequired}
              rows={2}
              value={followUp}
              onChange={(event) => setFollowUp(event.target.value)}
            />
          </label>
          {nextState === "Profile complete" && (
            <>
              <label>
                Named reviewer
                <input value={reviewedBy} onChange={(event) => setReviewedBy(event.target.value)} />
              </label>
              <label>
                Review / approval evidence
                <textarea rows={2} value={approvalEvidence} onChange={(event) => setApprovalEvidence(event.target.value)} />
              </label>
            </>
          )}
        </div>
        {readiness.profile_completion_blocking_reasons.length > 0 && (
          <div className="profile-blockers">
            <strong>Profile completion still needs:</strong>
            <ul>
              {readiness.profile_completion_blocking_reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          </div>
        )}
        {error && <p className="form-error" role="alert">{error}</p>}
        <button className="small-button" disabled={working} type="submit">
          Record transition
        </button>
      </form>
    </section>
  );
}
