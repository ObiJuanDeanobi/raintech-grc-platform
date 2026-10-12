import { FormEvent, useEffect, useMemo, useState } from "react";

import { request, startAssessment } from "../api";
import type {
  ProfileReadiness,
} from "../types";
import { takeStartError } from "../lib/startError";

export function StartAssessmentCard({
  readiness,
  onChanged,
  onStarted,
  onOpenProfile,
}: {
  readiness: ProfileReadiness;
  onChanged: () => Promise<void>;
  onStarted?: () => void;
  onOpenProfile?: () => void;
}) {
  const [working, setWorking] = useState(false);
  const [error, setError] = useState(() => takeStartError());
  // A fresh client has not recorded intake yet; starting records it. Only an open
  // follow-up holds the start back.
  const canStart = readiness.assessment_entry_allowed || readiness.state === readiness.supported_states[0];

  async function start() {
    setWorking(true);
    setError("");
    try {
      await startAssessment(readiness.project_id);
      await onChanged();
      onStarted?.();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not start the assessment.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <section className="start-card" aria-labelledby="start-card-title">
      <h1 id="start-card-title">Ready to begin</h1>
      <p>
        Starting records that intake is done; you can fill in the Profile as you go. It is
        approved once, before anything is issued.
      </p>
      {!canStart && (
        <ul className="blocking-reasons">
          {readiness.assessment_entry_blocking_reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="primary-button" disabled={working || !canStart} onClick={() => void start()}>
        Start assessment
      </button>
      {!canStart && onOpenProfile && (
        <button className="secondary-button" onClick={onOpenProfile}>
          Open the Profile to resolve the follow-up
        </button>
      )}
    </section>
  );
}

export function ReadinessPanel({
  readiness,
  onChanged,
}: {
  readiness: ProfileReadiness;
  onChanged: () => Promise<void>;
}) {
  // Profile complete is recorded by approving a Profile version, never typed in here.
  const choices = useMemo(
    () => readiness.allowed_next_states.filter((state) => state !== "Profile complete"),
    [readiness.allowed_next_states],
  );
  const [nextState, setNextState] = useState(choices[0] ?? "");
  const [decisionNote, setDecisionNote] = useState("");
  const [unresolved, setUnresolved] = useState(
    readiness.current_details.unresolved_required_fields.join(", "),
  );
  const [followUp, setFollowUp] = useState(readiness.current_details.follow_up_work);
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
    setNextState(choices[0] ?? "");
    setUnresolved(readiness.current_details.unresolved_required_fields.join(", "));
    setFollowUp(readiness.current_details.follow_up_work);
  }, [readiness, choices]);

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

  return (
    <details className="readiness-history" open={!readiness.assessment_entry_allowed && readiness.state !== readiness.supported_states[0] ? true : undefined}>
      <summary>Readiness history (advanced)</summary>
      <p className="readiness-current">
        Current state: <strong>{readiness.state}</strong>. Every change is kept in an
        append-only history.
      </p>
      <form className="readiness-form" onSubmit={(event) => void saveTransition(event)}>
        <div className="section-title">
          <h2>Record readiness decision</h2>
          <span>Append-only history</span>
        </div>
        <div className="readiness-fields">
          <label>
            Next state
            <select value={nextState} onChange={(event) => setNextState(event.target.value)}>
              {choices.map((state) => (
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
        <button className="small-button" disabled={working || !nextState} type="submit">
          Record transition
        </button>
      </form>
    </details>
  );
}
