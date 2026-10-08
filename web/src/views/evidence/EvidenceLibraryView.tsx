import { ArrowRight, ChevronDown, ChevronRight, CircleAlert, FileCheck2, FileUp, LoaderCircle, RefreshCw } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";

import { request } from "../../api";
import { REVIEW_LABELS, reviewDetail, shortHash } from "../../lib/evidence";
import type { Artifact, EvidenceLibrary, EvidenceReview, LibraryArtifact } from "../../types";
import "./evidence.css";

type Filter = "all" | EvidenceReview;

/**
 * The project's evidence library (#142): every artifact once, with its review
 * status and the objectives that use it. Upload, renewal, review dates, the
 * warning lead time and the recycle bin live here; linking to objectives is
 * done from the requirement view.
 */
export function EvidenceLibraryView({
  projectId,
  onOpenRecord,
  onChanged,
}: {
  projectId: string;
  /** Opens a mapped objective in the requirement view. */
  onOpenRecord: (recordId: string) => void;
  /** Something that can change verification or mappings was saved. */
  onChanged: () => void;
}) {
  const [library, setLibrary] = useState<EvidenceLibrary | null>(null);
  const [binned, setBinned] = useState<Artifact[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState<Filter>("all");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [renewing, setRenewing] = useState<string | null>(null);
  const [leadDraft, setLeadDraft] = useState("");

  const load = useCallback(async () => {
    const [next, bin] = await Promise.all([
      request<EvidenceLibrary>(`/api/projects/${projectId}/evidence-library`),
      request<Artifact[]>(`/api/projects/${projectId}/evidence?binned=true`),
    ]);
    setLibrary(next);
    setLeadDraft(String(next.lead_days));
    setBinned(Array.isArray(bin) ? bin : []);
  }, [projectId]);

  useEffect(() => {
    load().catch((caught) => setError(caught instanceof Error ? caught.message : "Could not load the evidence library."));
  }, [load]);

  async function act(path: string, init: RequestInit, changesVerification = true) {
    setBusy(true);
    setError("");
    try {
      await request(path, init);
      await load();
      if (changesVerification) onChanged();
      return true;
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The change was not saved.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  const base = `/api/projects/${projectId}/evidence`;

  function upload(file: File) {
    const data = new FormData();
    data.append("file", file);
    void act(base, { method: "POST", body: data }, false);
  }

  function setReviewDate(artifact: LibraryArtifact, value: string) {
    void act(`${base}/${artifact.id}/review-date`, { method: "PUT", body: JSON.stringify({ review_date: value || null }) });
  }

  async function saveLead(event: FormEvent) {
    event.preventDefault();
    await act(`/api/projects/${projectId}/evidence-settings`, { method: "PUT", body: JSON.stringify({ lead_days: Number(leadDraft) }) });
  }

  if (!library) {
    return (
      <main className="overview-panel evidence-view">
        {error ? <p className="form-error"><CircleAlert size={16} /> {error}</p> : <p className="muted"><LoaderCircle className="spin" size={14} /> Loading evidence…</p>}
      </main>
    );
  }

  const counts = { current: 0, due_soon: 0, stale: 0 } as Record<EvidenceReview, number>;
  for (const artifact of library.artifacts) counts[artifact.review_status] += 1;
  const shown = library.artifacts.filter((artifact) => filter === "all" || artifact.review_status === filter);

  return (
    <main className="overview-panel evidence-view" aria-label="Evidence library">
      <div className="overview-heading">
        <div>
          <p className="eyebrow">EVIDENCE LIBRARY</p>
          <h1>Evidence</h1>
          <p>Upload each file once and link it to objectives from the requirement view. Evidence past its review date no longer verifies a Met; the determination itself is not changed.</p>
        </div>
        <label className="upload-button evidence-upload">
          <FileUp size={16} /> Upload evidence
          <input type="file" aria-label="Upload evidence" disabled={busy} onChange={(event) => { const file = event.target.files?.[0]; event.target.value = ""; if (file) upload(file); }} />
        </label>
      </div>

      <div className="evidence-toolbar">
        <div className="evidence-filters" role="group" aria-label="Filter by review status">
          {(["all", "current", "due_soon", "stale"] as Filter[]).map((value) => (
            <button
              key={value}
              type="button"
              aria-pressed={filter === value}
              className={`${filter === value ? "selected" : ""} review-${value}`}
              onClick={() => setFilter(value)}
            >
              {value === "all" ? `All ${library.artifacts.length}` : `${REVIEW_LABELS[value]} ${counts[value]}`}
            </button>
          ))}
        </div>
        <form className="lead-time" onSubmit={saveLead}>
          <label>
            Warn
            <input aria-label="Warning lead time in days" type="number" min={0} max={365} value={leadDraft} onChange={(event) => setLeadDraft(event.target.value)} />
            days before a review date
          </label>
          <button type="submit" className="text-button" disabled={busy || leadDraft === String(library.lead_days) || leadDraft === ""}>Save</button>
        </form>
      </div>

      {error && <p className="form-error"><CircleAlert size={16} /> {error}</p>}

      {library.artifacts.length === 0 ? (
        <div className="empty-panel"><FileCheck2 size={22} /><p>No evidence yet. Upload a file to start the library.</p></div>
      ) : (
        <table className="evidence-table">
          <thead>
            <tr>
              <th scope="col">File</th>
              <th scope="col">Version</th>
              <th scope="col">Review date</th>
              <th scope="col">Status</th>
              <th scope="col">Used by</th>
              <th scope="col"><span className="sr-only">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            {shown.map((artifact) => {
              const open = expanded.has(artifact.id);
              return (
                <ArtifactRows
                  key={artifact.id}
                  artifact={artifact}
                  today={library.today}
                  open={open}
                  renewing={renewing === artifact.id}
                  busy={busy}
                  onToggle={() => setExpanded((current) => {
                    const next = new Set(current);
                    if (next.has(artifact.id)) next.delete(artifact.id);
                    else next.add(artifact.id);
                    return next;
                  })}
                  onOpenRecord={onOpenRecord}
                  onReviewDate={(value) => setReviewDate(artifact, value)}
                  onRenew={() => setRenewing(renewing === artifact.id ? null : artifact.id)}
                  onRenewed={async (data) => {
                    if (await act(`${base}/${artifact.id}/versions`, { method: "POST", body: data })) setRenewing(null);
                  }}
                  onBin={() => void act(`${base}/${artifact.id}/recycle`, { method: "POST" }, false)}
                />
              );
            })}
          </tbody>
        </table>
      )}

      <section className="evidence-bin" aria-label="Recycle bin">
        <h2>Recycle bin <span>{binned.length}</span></h2>
        <p className="muted">Evidence must be unlinked from every objective before it can be binned. Deleting permanently removes the stored file; its hash history is kept.</p>
        {binned.length === 0 ? <p className="muted">Empty.</p> : (
          <ul>
            {binned.map((artifact) => (
              <li key={artifact.id}>
                <span>{artifact.name}{artifact.purged_at ? " · file purged" : ""}</span>
                {!artifact.purged_at && (
                  <>
                    <button type="button" className="text-button" disabled={busy} onClick={() => void act(`${base}/${artifact.id}/restore`, { method: "POST" }, false)}>Restore</button>
                    <button type="button" className="text-button danger" disabled={busy} onClick={() => {
                      if (window.confirm(`Permanently delete the stored file for “${artifact.name}”? Its hash history is kept.`)) {
                        void act(`${base}/${artifact.id}`, { method: "DELETE" }, false);
                      }
                    }}>Delete permanently</button>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}

function ArtifactRows({
  artifact,
  today,
  open,
  renewing,
  busy,
  onToggle,
  onOpenRecord,
  onReviewDate,
  onRenew,
  onRenewed,
  onBin,
}: {
  artifact: LibraryArtifact;
  today: string;
  open: boolean;
  renewing: boolean;
  busy: boolean;
  onToggle: () => void;
  onOpenRecord: (recordId: string) => void;
  onReviewDate: (value: string) => void;
  onRenew: () => void;
  onRenewed: (data: FormData) => Promise<void>;
  onBin: () => void;
}) {
  const used = artifact.used_by.length;
  const inUse = used + artifact.other_use_count > 0;
  return (
    <>
      <tr className={`evidence-row review-${artifact.review_status}`}>
        <td>
          <strong>{artifact.name}</strong>
          <small title={`SHA-256 ${artifact.sha256}`}>SHA-256 {shortHash(artifact.sha256)}</small>
        </td>
        <td>v{artifact.version_number}</td>
        <td>
          <input
            type="date"
            aria-label={`Review date for ${artifact.name}`}
            defaultValue={artifact.review_date ?? ""}
            key={artifact.review_date ?? "none"}
            disabled={busy}
            onBlur={(event) => {
              if (event.target.value !== (artifact.review_date ?? "")) onReviewDate(event.target.value);
            }}
          />
          <small>{reviewDetail(artifact.review_date, artifact.review_status, artifact.days_until_review)}</small>
        </td>
        <td>
          <span className={`review-pill ${artifact.review_status}`}>{REVIEW_LABELS[artifact.review_status]}</span>
        </td>
        <td>
          {used === 0 ? (
            <span className="muted-small">Not linked{artifact.other_use_count ? ` · ${artifact.other_use_count} other use${artifact.other_use_count === 1 ? "" : "s"}` : ""}</span>
          ) : (
            <button type="button" className="used-by-toggle" aria-expanded={open} onClick={onToggle}>
              {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />} Used by {used}
            </button>
          )}
        </td>
        <td className="evidence-actions">
          <button type="button" className="text-button" onClick={onRenew} aria-expanded={renewing}>
            <RefreshCw size={12} /> {artifact.review_status === "stale" ? "Renew" : "Replace"}
          </button>
          <button
            type="button"
            className="text-button"
            disabled={busy || inUse}
            title={inUse ? "Unlink it from every objective first" : "Move to the recycle bin"}
            onClick={onBin}
          >
            Move to bin
          </button>
        </td>
      </tr>
      {open && used > 0 && (
        <tr className="used-by-row">
          <td colSpan={6}>
            <ul aria-label={`Objectives using ${artifact.name}`}>
              {artifact.used_by.map((use) => (
                <li key={use.mapping_id}>
                  <button type="button" className="used-by-link" onClick={() => onOpenRecord(use.record_id)}>
                    <strong>{use.citation}</strong>
                    <span>{use.rationale}</span>
                    {use.version_number !== artifact.version_number && <small>pinned to v{use.version_number}</small>}
                    <ArrowRight size={13} />
                  </button>
                </li>
              ))}
            </ul>
          </td>
        </tr>
      )}
      {renewing && (
        <tr className="renew-row">
          <td colSpan={6}>
            <RenewForm artifact={artifact} today={today} busy={busy} onSubmit={onRenewed} onCancel={onRenew} />
          </td>
        </tr>
      )}
    </>
  );
}

function RenewForm({
  artifact,
  today,
  busy,
  onSubmit,
  onCancel,
}: {
  artifact: LibraryArtifact;
  today: string;
  busy: boolean;
  onSubmit: (data: FormData) => Promise<void>;
  onCancel: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [reviewDate, setReviewDate] = useState("");
  const [move, setMove] = useState(artifact.used_by.length > 0);
  const stillStale = Boolean(artifact.review_date && artifact.review_date < today && (!reviewDate || reviewDate < today));

  return (
    <form
      className="renew-form"
      aria-label={`Replace ${artifact.name}`}
      onSubmit={(event) => {
        event.preventDefault();
        if (!file) return;
        const data = new FormData();
        data.append("file", file);
        if (reviewDate) data.append("review_date", reviewDate);
        if (move) data.append("move_mappings", "true");
        void onSubmit(data);
      }}
    >
      <label>
        New version
        <input type="file" aria-label={`New version of ${artifact.name}`} onChange={(event) => setFile(event.target.files?.[0] ?? null)} />
      </label>
      <label>
        Next review date
        <input type="date" aria-label="Next review date" value={reviewDate} onChange={(event) => setReviewDate(event.target.value)} />
      </label>
      {artifact.used_by.length > 0 && (
        <label className="renew-move">
          <input type="checkbox" checked={move} onChange={(event) => setMove(event.target.checked)} />
          Move the {artifact.used_by.length} linked objective{artifact.used_by.length === 1 ? "" : "s"} to the new version
        </label>
      )}
      {stillStale && <p className="link-evidence-warning"><CircleAlert size={13} /> Without a review date after today this file stays stale.</p>}
      <div className="link-evidence-actions">
        <button type="submit" className="small-button" disabled={busy || !file}>Upload version {artifact.version_number + 1}</button>
        <button type="button" className="text-button" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}
