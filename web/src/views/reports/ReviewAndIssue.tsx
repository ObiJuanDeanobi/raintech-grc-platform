import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError, request } from "../../api";
import type { BlockerGroup, IssueChecklist, IssueResult, IssueWarning } from "../../types";
import { PackageChoice } from "./PackageChoice";
import { type PackageType, packageQuery } from "./package-options";

/**
 * Finalize deliverables (#145, ADR 0021, ADR 0022): the one act, and the only
 * place blockers appear. It shows what must be fixed first, what is only worth a
 * look and what will be locked, records who reviewed, and finalizes from the data
 * as it is now. No role, no ticking, no separate backup step. (Stored state and
 * audit still say "issued"; only the words on screen changed.)
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
  packageType = null,
  onPackageChange,
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
  /** CMMC only (#146): which package this act issues. `null` for frameworks with no choice. */
  packageType?: PackageType | null;
  onPackageChange?: (next: PackageType) => void;
}) {
  const followedHeld = useRef(false);
  const [checklist, setChecklist] = useState<IssueChecklist | null>(null);
  const [profileVersion, setProfileVersion] = useState<number | null>(null);
  const [loadError, setLoadError] = useState("");
  const [note, setNote] = useState("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const sequence = useRef(0);

  const load = useCallback(async () => {
    const current = ++sequence.current;
    try {
      const next = await request<IssueChecklist>(`/api/projects/${projectId}/assessments/${assessmentId}/issue-checklist${packageQuery(packageType)}`);
      if (current === sequence.current) { setChecklist(next); setLoadError(""); }
    } catch (caught) {
      if (current === sequence.current) setLoadError(caught instanceof Error ? caught.message : "Could not check your data.");
    }
  }, [projectId, assessmentId, packageType]);
  useEffect(() => { setChecklist(null); void load(); return () => { sequence.current += 1; }; }, [load]);
  useEffect(() => {
    const controller = new AbortController();
    request<{ active_version_id: string | null; versions: { id: string; version_number: number }[] }>(`/api/projects/${projectId}/profile`, { signal: controller.signal })
      .then((profile) => setProfileVersion(
        (profile.versions?.find((version) => version.id === profile.active_version_id) ?? profile.versions?.[0])?.version_number ?? null,
      ))
      .catch(() => undefined);
    return () => controller.abort();
  }, [projectId]);

  async function issue() {
    setWorking(true); setError("");
    try {
      const result = await request<IssueResult>(`/api/projects/${projectId}/assessments/${assessmentId}/issue`, {
        method: "POST",
        body: JSON.stringify({ actor_id: actorId, note: note.trim(), ...(packageType ? { package: packageType } : {}) }),
      });
      onIssued(result);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Nothing was finalized.");
      // A refused issue usually means something changed; show what is left.
      if (caught instanceof ApiError && caught.status === 409) await load();
    } finally { setWorking(false); }
  }

  // A plain reissue follows the kind of the current issue of this assessment; another
  // kind needs the assessment reopened, so the dialog says so instead of failing later.
  const held = checklist?.current_issue;
  const heldType = held && held.assessment_id === assessmentId ? held.package_type ?? null : null;
  useEffect(() => {
    if (packageType && heldType && heldType !== packageType && !followedHeld.current) {
      followedHeld.current = true;
      onPackageChange?.(heldType);
    }
  }, [heldType, packageType, onPackageChange]);
  const mismatch = Boolean(packageType && heldType && heldType !== packageType);
  const blocked = (checklist?.groups.length ?? 0) > 0 || mismatch;
  const today = new Date().toLocaleDateString(undefined, { year: "numeric", month: "long", day: "numeric" });
  const warnings: IssueWarning[] = checklist?.warnings ?? [];
  return (
    <div className="modal-backdrop" role="presentation">
      <div className="workspace-modal review-issue-dialog" role="dialog" aria-modal="true" aria-labelledby="review-issue-title" aria-busy={working}>
        <div>
          <p className="eyebrow">DELIVERABLES</p>
          <h2 id="review-issue-title">Finalize deliverables</h2>
          <p className="muted-small">Locks your data as it is now.</p>
        </div>

        {packageType && onPackageChange && <PackageChoice value={packageType} onChange={onPackageChange} disabled={working} />}

        {loadError && <p className="form-error" role="alert">{loadError}</p>}
        {!checklist && !loadError && <p className="muted-small">Checking your data…</p>}

        {checklist?.current_issue && (
          <p className="muted-small" role="note">Finalizing again replaces the current final version (it will be marked Replaced).</p>
        )}

        {mismatch && (
          <p className="form-error" role="alert">
            The current issued version is {heldType === "gap_assessment" ? "a gap assessment" : "a final self-assessment"}.
            To issue the other kind, reopen the assessment first.
          </p>
        )}

        {checklist && (checklist.groups.length ?? 0) > 0 && (
          <section className="issue-must-fix" aria-labelledby="issue-must-fix-title">
            <h3 id="issue-must-fix-title">Fix before finalizing</h3>
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
            <h3 id="issue-worth-title">Worth a look</h3>
            <p className="muted-small">These do not stop you. Nothing here needs ticking.</p>
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

        {checklist && (
          <section className="issue-locked" aria-labelledby="issue-locked-title">
            <h3 id="issue-locked-title">What will be locked</h3>
            <ul>
              <li>{profileVersion ? `Profile version ${profileVersion}` : "The Profile"}</li>
              <li>The assessment, as it is now</li>
              <li>The documents made from them</li>
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
            {working ? "Finalizing…" : "Finalize"}
          </button>
          <button type="button" className="text-button" disabled={working} onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}
