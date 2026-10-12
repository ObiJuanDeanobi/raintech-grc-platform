import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, request } from "../../api";
import type { BlockerGroup, IssueChecklist, IssueResult, IssueWarning } from "../../types";

/**
 * Review and issue (#145, ADR 0021): the one act. It shows what must be fixed
 * first and what is only worth a look, records who reviewed, and issues from the
 * data as it is now. No role, no ticking, no separate backup step.
 */
export function ReviewAndIssueDialog({
  projectId,
  assessmentId,
  reviewerName,
  actorId,
  onClose,
  onIssued,
  onOpenGroup,
  onOpenTarget,
}: {
  projectId: string;
  assessmentId: string;
  /** The selected account's name; the reviewer is always the account. */
  reviewerName: string;
  actorId: string;
  onClose: () => void;
  onIssued: (result: IssueResult) => void;
  onOpenGroup: (group: BlockerGroup) => void;
  onOpenTarget: (target: string) => void;
}) {
  const [checklist, setChecklist] = useState<IssueChecklist | null>(null);
  const [loadError, setLoadError] = useState("");
  const [note, setNote] = useState("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const sequence = useRef(0);

  const load = useCallback(async () => {
    const current = ++sequence.current;
    try {
      const next = await request<IssueChecklist>(`/api/projects/${projectId}/assessments/${assessmentId}/issue-checklist`);
      if (current === sequence.current) { setChecklist(next); setLoadError(""); }
    } catch (caught) {
      if (current === sequence.current) setLoadError(caught instanceof Error ? caught.message : "Could not check your data.");
    }
  }, [projectId, assessmentId]);
  useEffect(() => { void load(); return () => { sequence.current += 1; }; }, [load]);

  async function issue() {
    setWorking(true); setError("");
    try {
      const result = await request<IssueResult>(`/api/projects/${projectId}/assessments/${assessmentId}/issue`, {
        method: "POST",
        body: JSON.stringify({ actor_id: actorId, note: note.trim() }),
      });
      onIssued(result);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Nothing was issued.");
      // A refused issue usually means something changed; show what is left.
      if (caught instanceof ApiError && caught.status === 409) await load();
    } finally { setWorking(false); }
  }

  const blocked = (checklist?.groups.length ?? 0) > 0;
  const today = new Date().toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
  const warnings: IssueWarning[] = checklist?.warnings ?? [];
  return (
    <div className="modal-backdrop" role="presentation">
      <div className="workspace-modal review-issue-dialog" role="dialog" aria-modal="true" aria-labelledby="review-issue-title" aria-busy={working}>
        <div>
          <p className="eyebrow">REPORTS</p>
          <h2 id="review-issue-title">Review and issue</h2>
          <p className="muted-small">Issues from your data as it is now.</p>
        </div>

        {loadError && <p className="form-error" role="alert">{loadError}</p>}
        {!checklist && !loadError && <p className="muted-small">Checking your data…</p>}

        {checklist?.current_issue && (
          <p className="muted-small" role="note">Issuing again replaces the current issued version (it will be marked Superseded).</p>
        )}

        {checklist && blocked && (
          <section className="issue-must-fix" aria-labelledby="issue-must-fix-title">
            <h3 id="issue-must-fix-title">Must be fixed before issue</h3>
            <ul>
              {checklist.groups.map((group) => (
                <li key={group.key}>
                  <button type="button" className="text-button" onClick={() => onOpenGroup(group)}>
                    {group.count} · {group.label}
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}

        {checklist && warnings.length > 0 && (
          <section className="issue-worth-checking" aria-labelledby="issue-worth-title">
            <h3 id="issue-worth-title">Worth checking</h3>
            <p className="muted-small">These do not stop the issue. Nothing here needs ticking.</p>
            <ul>
              {warnings.map((warning) => (
                <li key={warning.key}>
                  <strong>{warning.count} · {warning.label}</strong>
                  <span>{warning.detail}</span>
                  <button type="button" className="text-button" onClick={() => onOpenTarget(warning.target)}>Open</button>
                </li>
              ))}
            </ul>
          </section>
        )}

        <dl className="issue-who">
          <div><dt>Reviewer</dt><dd>{reviewerName}</dd></div>
          <div><dt>Date</dt><dd>{today}</dd></div>
        </dl>
        <label>
          Note <small>optional</small>
          <textarea rows={2} value={note} onChange={(event) => setNote(event.target.value)} />
        </label>

        {error && <p className="form-error" role="alert">{error}</p>}
        <div className="modal-actions">
          <button type="button" className="primary-button" disabled={working || !checklist || blocked} onClick={() => void issue()}>
            {working ? "Issuing…" : "Issue"}
          </button>
          <button type="button" className="text-button" disabled={working} onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}
