import { useCallback, useEffect, useRef, useState } from "react";

import { downloadFile, request } from "../../api";
import { ACCOUNT } from "../../lib/account";
import type { BlockerGroup, GeneratedPackage, IssueResult, RecordIndex } from "../../types";
import { ReopenAssessmentForm } from "../close/ClosePanels";
import { PackageChoice } from "./PackageChoice";
import { DEFAULT_PACKAGE, type PackageType, packageQuery } from "./package-options";
import { ReviewAndIssueDialog } from "./ReviewAndIssue";

/**
 * Deliverables (#145, ADR 0022): a draft any time, and one finalize act. Final
 * versions are listed below; a draft is never listed because it is never stored.
 * The words are the consultant's; the stored states stay Draft, Issued, Superseded.
 */
export function ReportsView({
  projectId,
  assessmentId,
  records,
  hasClose,
  hasPackageChoice = false,
  refreshKey,
  onReopened,
  onOpenGroup,
  onOpenTarget,
}: {
  projectId: string;
  assessmentId: string;
  records: RecordIndex[];
  hasClose: boolean;
  /** CMMC: the gap assessment or the final self-assessment (#146). */
  hasPackageChoice?: boolean;
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
  const [packageType, setPackageType] = useState<PackageType>(DEFAULT_PACKAGE);
  const chosen = hasPackageChoice ? packageType : null;
  const sequence = useRef(0);
  // Final v1, v2, ... in the order they were finalized.
  const versionNumbers = new Map(
    [...packages].sort((a, b) => String(a.issued_at ?? "").localeCompare(String(b.issued_at ?? ""))).map((pkg, index) => [pkg.id, index + 1] as const),
  );

  async function downloadDraft() {
    setDraftWorking(true); setDraftError("");
    try { await downloadFile(`/api/projects/${projectId}/assessments/${assessmentId}/draft${packageQuery(chosen)}`); }
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
      if (current === sequence.current) setLoadError(caught instanceof Error ? caught.message : "Could not load final versions.");
    }
  }, [projectId]);
  useEffect(() => { void load(); return () => { sequence.current += 1; }; }, [load, assessmentId, refreshKey]);

  return (
    <main className="overview-panel reports-panel">
      <div className="overview-heading">
        <div>
          <p className="eyebrow">DELIVERABLES</p>
          <h1>Deliverables</h1>
        </div>
      </div>
      {!hasClose ? (
        <p className="muted-small">This framework has no package workflow yet.</p>
      ) : (
        <>
          <section className="reports-actions" aria-label="Deliverable actions">
            <p>
              A draft shows your work so far and is marked DRAFT — NOT ISSUED on every page. It is not saved and can be made as often as you like.
              Finalizing locks the version you review.
            </p>
            {hasPackageChoice && <PackageChoice value={packageType} onChange={setPackageType} />}
            <div className="package-review-actions">
              <button type="button" className="secondary-button" disabled={draftWorking} onClick={() => void downloadDraft()}>{draftWorking ? "Making draft…" : "Download draft"}</button>
              <button type="button" className="small-button" onClick={() => { setIssued(null); setDialogOpen(true); }}>Finalize…</button>
            </div>
            {draftError && <p className="error-copy" role="alert">{draftError}</p>}
            {issued && (
              <p className="readiness-ok" role="status">
                Finalized. Reviewed by {issued.reviewer} on {new Date(issued.issued_at).toLocaleDateString()}.
                {issued.superseded_package_id ? " It replaces the earlier final version." : ""}
              </p>
            )}
          </section>

          <section className="issued-versions" aria-labelledby="issued-versions-title">
            <h2 id="issued-versions-title">Final versions</h2>
            {loadError && <p className="error-copy" role="alert">{loadError}</p>}
            {packages.length === 0 && !loadError && <p className="muted-small">Nothing has been finalized yet.</p>}
            {packages.map((pkg) => (
              <FinalVersion key={pkg.id} projectId={projectId} pkg={pkg} number={versionNumbers.get(pkg.id) ?? 1} current={pkg.assessment_id === assessmentId} records={records} onReopened={onReopened} onIssued={(result) => { setIssued(result); void load(); }} />
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
          packageType={chosen}
          onPackageChange={setPackageType}
        />
      )}
    </main>
  );
}

function FinalVersion({ projectId, pkg, number, current, records, onReopened, onIssued }: {
  projectId: string;
  pkg: GeneratedPackage;
  number: number;
  current: boolean;
  records: RecordIndex[];
  onReopened: () => Promise<void>;
  onIssued: (result: IssueResult) => void;
}) {
  const issuedOn = pkg.issued_at ? new Date(pkg.issued_at).toLocaleDateString() : "";
  const isCurrent = pkg.lifecycle === "Issued";
  const [menuOpen, setMenuOpen] = useState(false);
  return (
    <article className="generated-package">
      <div>
        <strong>Final v{number}{pkg.correction ? " (wording corrected)" : ""}{issuedOn ? ` · ${issuedOn}` : ""}</strong>
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
      {pkg.superseded_by_package_id && <small className="package-correction-note">Replaced by a later final version. This one is kept and can still be downloaded.</small>}
      {isCurrent && current && (
        <div className="row-menu">
          <button type="button" className="text-button" aria-expanded={menuOpen} onClick={() => setMenuOpen((value) => !value)}>
            {menuOpen ? "Hide changes" : "Change this version…"}
          </button>
          {menuOpen && (
            <>
              <ReissueForm projectId={projectId} packageId={pkg.id} onIssued={onIssued} />
              <ReopenAssessmentForm projectId={projectId} packageId={pkg.id} records={records} onReopened={onReopened} />
            </>
          )}
        </div>
      )}
      {pkg.reopening && <small className="package-correction-note">Findings changed (new version): {pkg.reopening.rationale}</small>}
    </article>
  );
}

/** A presentation-only correction (stored as a reissue): new wording or layout, same findings. One act. */
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
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Nothing was finalized."); }
    finally { setWorking(false); }
  }
  if (!open) return <div className="presentation-correction"><button type="button" className="secondary-button" onClick={() => setOpen(true)}>Correct wording (same findings)…</button></div>;
  return (
    <div className="presentation-correction" aria-labelledby="reissue-title">
      <strong id="reissue-title">Correct wording (same findings)</strong>
      <p>Makes a new final version from the same findings and replaces this one. If any finding has changed, use Change findings (new version) instead.</p>
      {error && <p className="package-review-error" role="alert">{error}</p>}
      <label>Note <small>optional</small><textarea rows={2} value={note} onChange={(event) => setNote(event.target.value)} /></label>
      <div className="package-review-actions">
        <button type="button" className="secondary-button" disabled={working} onClick={() => setOpen(false)}>Cancel</button>
        <button type="button" className="primary-button" disabled={working} onClick={() => void submit()}>{working ? "Finalizing…" : "Finalize correction"}</button>
      </div>
    </div>
  );
}
