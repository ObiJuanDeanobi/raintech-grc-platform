import { useCallback, useEffect, useRef, useState } from "react";

import { downloadFile, request } from "../../api";
import { ACCOUNT } from "../../lib/account";
import type { BlockerGroup, GeneratedPackage, IssueResult, RecordIndex } from "../../types";
import { ReopenAssessmentForm } from "../close/ClosePanels";
import { ReviewAndIssueDialog } from "./ReviewAndIssue";

/**
 * Reports (#145): a draft any time, and one review-and-issue act. Issued
 * versions are listed below; a draft is never listed because it is never stored.
 */
export function ReportsView({
  projectId,
  assessmentId,
  records,
  hasClose,
  refreshKey,
  onReopened,
  onOpenGroup,
  onOpenTarget,
}: {
  projectId: string;
  assessmentId: string;
  records: RecordIndex[];
  hasClose: boolean;
  refreshKey: unknown;
  onReopened: () => Promise<void>;
  onOpenGroup: (group: BlockerGroup) => void;
  onOpenTarget: (target: string) => void;
}) {
  const [packages, setPackages] = useState<GeneratedPackage[]>([]);
  const [loadError, setLoadError] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [issued, setIssued] = useState<IssueResult | null>(null);
  const [draftError, setDraftError] = useState("");
  const [draftWorking, setDraftWorking] = useState(false);
  const sequence = useRef(0);

  async function downloadDraft() {
    setDraftWorking(true); setDraftError("");
    try { await downloadFile(`/api/projects/${projectId}/assessments/${assessmentId}/draft`); }
    catch (caught) { setDraftError(caught instanceof Error ? caught.message : "The draft could not be made."); }
    finally { setDraftWorking(false); }
  }

  const load = useCallback(async () => {
    const current = ++sequence.current;
    try {
      const listed = await request<GeneratedPackage[]>(`/api/projects/${projectId}/packages`);
      if (current !== sequence.current) return;
      setPackages((Array.isArray(listed) ? listed : []).filter((pkg) => pkg.lifecycle === "Issued" || pkg.lifecycle === "Superseded"));
      setLoadError("");
    } catch (caught) {
      if (current === sequence.current) setLoadError(caught instanceof Error ? caught.message : "Could not load issued versions.");
    }
  }, [projectId]);
  useEffect(() => { void load(); return () => { sequence.current += 1; }; }, [load, assessmentId, refreshKey]);

  return (
    <main className="overview-panel reports-panel">
      <div className="overview-heading">
        <div>
          <p className="eyebrow">REPORTS</p>
          <h1>Reports and packages</h1>
        </div>
      </div>
      {!hasClose ? (
        <p className="muted-small">This framework has no package workflow yet.</p>
      ) : (
        <>
          <section className="reports-actions" aria-label="Report actions">
            <p>
              A draft shows your work so far and is marked DRAFT — NOT ISSUED on every page. It is not saved and can be made as often as you like.
              Issuing freezes the version you review.
            </p>
            <div className="package-review-actions">
              <button type="button" className="secondary-button" disabled={draftWorking} onClick={() => void downloadDraft()}>{draftWorking ? "Making draft…" : "Download draft"}</button>
              <button type="button" className="small-button" onClick={() => { setIssued(null); setDialogOpen(true); }}>Review and issue…</button>
            </div>
            {draftError && <p className="error-copy" role="alert">{draftError}</p>}
            {issued && (
              <p className="readiness-ok" role="status">
                Issued. Reviewed by {issued.reviewer} on {new Date(issued.issued_at).toLocaleDateString()}.
                {issued.superseded_package_id ? " It replaces the earlier issued version." : ""}
              </p>
            )}
          </section>

          <section className="issued-versions" aria-labelledby="issued-versions-title">
            <h2 id="issued-versions-title">Issued versions</h2>
            {loadError && <p className="error-copy" role="alert">{loadError}</p>}
            {packages.length === 0 && !loadError && <p className="muted-small">Nothing has been issued yet.</p>}
            {packages.map((pkg) => (
              <IssuedVersion key={pkg.id} projectId={projectId} pkg={pkg} current={pkg.assessment_id === assessmentId} records={records} onReopened={onReopened} onIssued={(result) => { setIssued(result); void load(); }} />
            ))}
          </section>
        </>
      )}
      {dialogOpen && (
        <ReviewAndIssueDialog
          projectId={projectId}
          assessmentId={assessmentId}
          reviewerName={ACCOUNT.name}
          actorId={ACCOUNT.id}
          onClose={() => setDialogOpen(false)}
          onIssued={(result) => { setDialogOpen(false); setIssued(result); void load(); }}
          onOpenGroup={(group) => { setDialogOpen(false); onOpenGroup(group); }}
          onOpenTarget={(target) => { setDialogOpen(false); onOpenTarget(target); }}
        />
      )}
    </main>
  );
}

function IssuedVersion({ projectId, pkg, current, records, onReopened, onIssued }: {
  projectId: string;
  pkg: GeneratedPackage;
  current: boolean;
  records: RecordIndex[];
  onReopened: () => Promise<void>;
  onIssued: (result: IssueResult) => void;
}) {
  const issuedOn = pkg.issued_at ? new Date(pkg.issued_at).toLocaleDateString() : "";
  const isCurrent = pkg.lifecycle === "Issued";
  return (
    <article className="generated-package">
      <div>
        <strong>{pkg.correction ? "Reissued version" : "Issued version"}{issuedOn ? ` · ${issuedOn}` : ""}</strong>
        <span className={`readiness-state ${isCurrent ? "ready" : "blocked"}`}>{isCurrent ? "Current" : "Replaced"}</span>
        <small>
          {pkg.reviewer ? `Reviewed by ${pkg.reviewer}` : "Reviewed"}
          {pkg.review_note ? ` · ${pkg.review_note}` : ""}
        </small>
      </div>
      <div className="generated-components">
        {pkg.components.map((component) => (
          <a key={component.id} className="text-button" href={component.download_url ?? `/api/projects/${projectId}/packages/${pkg.id}/components/${component.id}/download`}>
            {component.filename || component.kind}
          </a>
        ))}
      </div>
      {pkg.superseded_by_package_id && <small className="package-correction-note">Replaced by a later issued version. This one is kept and can still be downloaded.</small>}
      {isCurrent && current && <ReissueForm projectId={projectId} packageId={pkg.id} onIssued={onIssued} />}
      {isCurrent && current && <ReopenAssessmentForm projectId={projectId} packageId={pkg.id} records={records} onReopened={onReopened} />}
      {pkg.reopening && <small className="package-correction-note">Reopened to change the assessment: {pkg.reopening.rationale}</small>}
    </article>
  );
}

/** A presentation-only correction: new wording or layout, same findings. One act. */
function ReissueForm({ projectId, packageId, onIssued }: { projectId: string; packageId: string; onIssued: (result: IssueResult) => void }) {
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  async function submit() {
    setWorking(true); setError("");
    try {
      const result = await request<IssueResult>(`/api/projects/${projectId}/packages/${packageId}/issue-now`, {
        method: "POST",
        body: JSON.stringify({ actor_id: ACCOUNT.id, note: note.trim() }),
      });
      setOpen(false); setNote("");
      onIssued(result);
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Nothing was issued."); }
    finally { setWorking(false); }
  }
  if (!open) return <div className="presentation-correction"><button type="button" className="secondary-button" onClick={() => setOpen(true)}>Reissue with new wording or layout…</button></div>;
  return (
    <div className="presentation-correction" aria-labelledby="reissue-title">
      <strong id="reissue-title">Reissue with new wording or layout</strong>
      <p>Issues a new version from the same findings and replaces this one. If anything in the assessment has changed, reopen it instead.</p>
      {error && <p className="package-review-error" role="alert">{error}</p>}
      <label>Note <small>optional</small><textarea rows={2} value={note} onChange={(event) => setNote(event.target.value)} /></label>
      <div className="package-review-actions">
        <button type="button" className="secondary-button" disabled={working} onClick={() => setOpen(false)}>Cancel</button>
        <button type="button" className="primary-button" disabled={working} onClick={() => void submit()}>{working ? "Issuing…" : "Issue"}</button>
      </div>
    </div>
  );
}
