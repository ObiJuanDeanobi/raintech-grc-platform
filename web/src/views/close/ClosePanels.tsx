import {
  CircleAlert,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { request } from "../../api";
import type {
  CloseReadiness,
  GeneratedPackage,
  RevalidationItem,
  AssessmentReopening,
  RecordIndex,
  PackageReview,
  IssueReadiness,
} from "../../types";

export function BackupControl() {
  const [warning, setWarning] = useState<string | null>(null);
  const [last, setLast] = useState<string | null>(null);
  const [state, setState] = useState<"idle" | "working" | "failed">("idle");
  const load = useCallback(() => {
    request<{ warning: string | null; backups: { status: string; completed_at: string }[] }>("/api/backups")
      .then((result) => {
        if (!result || !Array.isArray(result.backups)) return;
        setWarning(result.warning);
        setLast(result.backups.find((backup) => backup.status === "complete")?.completed_at ?? null);
      })
      .catch(() => undefined);
  }, []);
  useEffect(load, [load]);
  async function backUpNow() {
    setState("working");
    try {
      await request("/api/backups", { method: "POST" });
      setState("idle");
      load();
    } catch {
      setState("failed");
    }
  }
  return (
    <span className="backup-control">
      {warning && <span className="backup-warning" role="alert" title={warning}><CircleAlert size={14} /> Backup failed</span>}
      <button type="button" className="text-button" disabled={state === "working"} onClick={() => void backUpNow()} title={last ? `Last backup ${new Date(last).toLocaleString()}` : "No backup yet"}>
        {state === "working" ? "Backing up…" : state === "failed" ? "Backup failed · retry" : "Back up now"}
      </button>
    </span>
  );
}

export function CloseReadinessPanel({ projectId, assessmentId, onNavigate }: { projectId: string; assessmentId: string; onNavigate: (link: Record<string, unknown>) => void }) {
  const [data, setData] = useState<CloseReadiness | null>(null);
  const [error, setError] = useState("");
  const sequenceRef = useRef(0);
  useEffect(() => {
    const controller = new AbortController(); const sequence = ++sequenceRef.current;
    setData(null); setError("");
    void request<CloseReadiness>(`/api/projects/${projectId}/assessments/${assessmentId}/close-readiness?target=fieldwork_ready_for_generation`, { signal: controller.signal })
      .then((next) => { if (!controller.signal.aborted && sequenceRef.current === sequence && next && typeof next.status === "string" && Array.isArray(next.checks) && Array.isArray(next.blockers)) setData(next); })
      .catch((caught) => { if (!controller.signal.aborted && sequenceRef.current === sequence) setError(caught instanceof Error ? caught.message : "Could not load close readiness."); });
    return () => controller.abort();
  }, [projectId, assessmentId]);
  if (error) return <section className="close-readiness-panel"><p className="error-copy">{error}</p></section>;
  if (!data) return null;
  const text = (value: unknown) => typeof value === "string" ? value : JSON.stringify(value);
  return <section className={`close-readiness-panel ${data.status.toLowerCase()}`} aria-labelledby="close-readiness-title">
    <div className="section-title"><div><p className="eyebrow">CLOSE READINESS</p><h2 id="close-readiness-title">Fieldwork ready for generation</h2></div><span className={`readiness-state ${data.status === "Ready" ? "ready" : "blocked"}`}>{data.status}</span></div>
    {data.blockers.length > 0 && <div className="close-readiness-blockers"><strong>Blockers</strong><ul>{data.blockers.map((blocker, index) => <li key={index}>{typeof blocker === "string" ? blocker : text(blocker.detail ?? blocker.message ?? blocker.reason ?? blocker)}</li>)}</ul></div>}
    <div className="close-readiness-checks"><strong>Checks</strong><ul>{data.checks.map((check, index) => <li key={index}><span>{text(check.label ?? check.name ?? check.key ?? `Check ${index + 1}`)}</span><small>{text(check.status ?? check.result ?? check.value)}</small></li>)}</ul></div>
    {data.links && data.links.length > 0 && <div className="close-readiness-links"><strong>Next actions</strong>{data.links.map((link, index) => <button key={index} className="text-button" onClick={() => onNavigate(link)}>{text(link.label ?? link.title ?? link.action ?? "Open related work")}</button>)}</div>}
    {(data.informational || data.metadata) && <details><summary>Later gates and metadata</summary><ul>{Object.entries(data.informational ?? data.metadata ?? {}).map(([key, value]) => <li key={key}>{key.replaceAll("_", " ")} · {text(value)}</li>)}</ul></details>}
  </section>;
}

export function PackageGenerationPanel({ projectId, assessmentId, records, onReopened }: { projectId: string; assessmentId: string; records: RecordIndex[]; onReopened: () => Promise<void> }) {
  const [readiness, setReadiness] = useState<CloseReadiness | null>(null);
  const [packages, setPackages] = useState<GeneratedPackage[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [reviews, setReviews] = useState<Record<string, PackageReview>>({});
  const [reviewForms, setReviewForms] = useState<Record<string, { reviewer_name: string; reviewer_role: string; note: string; confirmations: Record<string, boolean> }>>({});
  const [reviewWorking, setReviewWorking] = useState<string | null>(null);
  const sequenceRef = useRef(0);
  const load = useCallback(async (signal?: AbortSignal) => {
    const sequence = ++sequenceRef.current;
    setLoading(true); setError("");
    try {
      const [nextReadiness, nextPackages] = await Promise.all([
        request<CloseReadiness>(`/api/projects/${projectId}/assessments/${assessmentId}/close-readiness?target=fieldwork_ready_for_generation`, { signal }),
        request<GeneratedPackage[] | { packages?: GeneratedPackage[] }>(`/api/projects/${projectId}/packages`, { signal }),
      ]);
      if (sequence !== sequenceRef.current || signal?.aborted) return;
      setReadiness(nextReadiness);
      const listed = Array.isArray(nextPackages) ? nextPackages : nextPackages.packages ?? [];
      setPackages(listed.filter((pkg) => (pkg.assessment_id === assessmentId || Boolean(pkg.issuance_status)) && pkg.state === "promoted").map((pkg) => ({ ...pkg, source_sha256: pkg.source_sha256 ?? pkg.manifest?.source_snapshot_sha256, template_version: pkg.template_version ?? pkg.manifest?.template_version, components: pkg.components?.length ? pkg.components : pkg.manifest?.components ?? [] })));
      const promoted = listed.filter((pkg) => pkg.assessment_id === assessmentId && pkg.state === "promoted");
      const loadedReviews = await Promise.all(promoted.map(async (pkg) => {
        try { const review = await request<PackageReview>(`/api/projects/${projectId}/packages/${pkg.id}/review`, { signal }); return [pkg.id, review && typeof review.state === "string" ? review : { package_id: pkg.id, state: "Complete candidate" }] as const; }
        catch { return [pkg.id, { package_id: pkg.id, state: "Complete candidate" }] as const; }
      }));
      if (sequence === sequenceRef.current && !signal?.aborted) setReviews(Object.fromEntries(loadedReviews));
    } catch (caught) {
      if (sequence === sequenceRef.current && !signal?.aborted) setError(caught instanceof Error ? caught.message : "Could not load generated packages.");
    } finally { if (sequence === sequenceRef.current && !signal?.aborted) setLoading(false); }
  }, [projectId, assessmentId]);
  useEffect(() => { const controller = new AbortController(); void load(controller.signal); return () => { sequenceRef.current += 1; controller.abort(); }; }, [load]);
  async function generate() {
    const sequence = sequenceRef.current;
    setGenerating(true); setError("");
    try {
      await request(`/api/projects/${projectId}/assessments/${assessmentId}/packages`, { method: "POST" });
      if (sequence === sequenceRef.current) await load();
    } catch (caught) { if (sequence === sequenceRef.current) setError(caught instanceof Error ? caught.message : "Package generation failed."); }
    finally { setGenerating(false); }
  }
  function formFor(pkg: GeneratedPackage) {
    return reviewForms[pkg.id] ?? { reviewer_name: "", reviewer_role: "", note: "", confirmations: Object.fromEntries(pkg.components.map((component) => [component.kind, false])) };
  }
  async function transition(pkg: GeneratedPackage, nextState: "In Review" | "Reviewed" | "Ready to issue") {
    const sequence = sequenceRef.current;
    const form = formFor(pkg);
    const review = reviews[pkg.id];
    const drift = review?.drift ?? [];
    const allConfirmed = pkg.components.every((component) => form.confirmations[component.kind]) && Boolean(form.confirmations.__source);
    if (nextState === "Ready to issue" && (!form.reviewer_name.trim() || !form.reviewer_role.trim() || !form.note.trim() || !allConfirmed || drift.length > 0 || (review?.blockers?.length ?? 0) > 0)) {
      setError("Package sign-off is blocked: complete reviewer fields, component confirmations, and resolve drift or blockers.");
      return;
    }
    setReviewWorking(pkg.id); setError("");
    try {
      const next = await request<PackageReview>(`/api/projects/${projectId}/packages/${pkg.id}/review/transitions`, { method: "POST", body: JSON.stringify({ next_state: nextState, actor_id: "johnathan", reviewer_name: form.reviewer_name, reviewer_role: form.reviewer_role, note: form.note, approval: nextState === "Ready to issue" ? "I approve this exact package for issuance." : "", component_confirmations: form.confirmations }) });
      if (sequenceRef.current === sequence) setReviews((current) => ({ ...current, [pkg.id]: next }));
    } catch (caught) { if (sequenceRef.current === sequence) setError(caught instanceof Error ? caught.message : "Package review update failed."); }
    finally { if (sequenceRef.current === sequence) setReviewWorking(null); }
  }
  if (loading) return <section className="package-generation-panel"><p className="eyebrow">PACKAGE GENERATION</p><p>Loading package status…</p></section>;
  return <section className="package-generation-panel" aria-labelledby="package-generation-title">
    <div className="section-title"><div><p className="eyebrow">PACKAGE GENERATION</p><h2 id="package-generation-title">Assessment package</h2></div>{readiness?.status === "Ready" && <span className="readiness-state ready">Ready to generate</span>}</div>
    {error && <p className="error-copy" role="alert">{error}</p>}
    {readiness?.status !== "Ready" ? <p className="package-generation-blocked">Complete fieldwork close readiness before generating the report and POA&amp;M.</p> : <div className="package-generation-action"><p>Generate the combined assessment report and separate POA&amp;M from one immutable source snapshot.</p><button className="small-button" disabled={generating} onClick={() => void generate()}>{generating ? "Generating both components…" : "Generate package"}</button></div>}
    {packages.length > 0 && <div className="generated-package-list"><strong>Generated packages</strong>{packages.map((pkg) => { const historical = pkg.assessment_id !== assessmentId; const review = reviews[pkg.id] ?? { package_id: pkg.id, state: "Complete candidate" }; const form = formFor(pkg); return <article key={pkg.id} className="generated-package"><div><strong>{pkg.correction ? "Presentation-only correction" : historical ? "Earlier revision package" : "Complete package"}</strong>{pkg.issuance_status && <span className={`readiness-state ${pkg.issuance_status === "Current" ? "ready" : "blocked"}`}>{pkg.issuance_status === "Current" ? "Issued · Current" : "Superseded"}</span>}<small>{new Date(pkg.created_at).toLocaleString()} · Source {pkg.source_snapshot_id ?? "snapshot recorded"}</small></div><div className="generated-components">{pkg.components.map((component) => <a key={component.id} className="text-button" href={component.download_url ?? `/api/projects/${projectId}/packages/${pkg.id}/components/${component.id}/download`}>{component.filename || component.kind}</a>)}</div>{pkg.source_sha256 && <small>Source SHA-256: {pkg.source_sha256}</small>}{pkg.correction && <small className="package-correction-note">Corrects issued package {pkg.correction.prior_package_id} · {pkg.correction.reason}</small>}{pkg.superseded_by_package_id && <small className="package-correction-note">Superseded by {pkg.superseded_by_package_id}; retained and retrievable.</small>}{pkg.issuance_status === "Current" && !historical && <PresentationCorrectionForm projectId={projectId} packageId={pkg.id} onCreated={() => load()} />}{pkg.issuance_status === "Current" && !historical && <ReopenAssessmentForm projectId={projectId} packageId={pkg.id} records={records} onReopened={onReopened} />}{pkg.reopening && <small className="package-correction-note">Reopened for substantive correction: {pkg.reopening.rationale}</small>}{!historical && <div className="package-review" aria-label={`Review ${pkg.id}`} aria-busy={reviewWorking === pkg.id}><div className="section-title"><strong>Package review</strong><span className={`readiness-state ${review.state === "Ready to issue" ? "ready" : "blocked"}`}>{review.state}</span></div>{(review.drift?.length ?? 0) > 0 && <div className="package-review-error" role="alert">Source or template drift detected: {review.drift!.join("; ")}</div>}{(review.blockers?.length ?? 0) > 0 && <div className="package-review-error" role="alert">Review blockers: {review.blockers!.join("; ")}</div>}<div className="package-review-fields"><label>Reviewer name<input value={form.reviewer_name} onChange={(event) => setReviewForms((all) => ({ ...all, [pkg.id]: { ...form, reviewer_name: event.target.value } }))} /></label><label>Reviewer role<input value={form.reviewer_role} onChange={(event) => setReviewForms((all) => ({ ...all, [pkg.id]: { ...form, reviewer_role: event.target.value } }))} /></label><label>Review note<textarea rows={2} value={form.note} onChange={(event) => setReviewForms((all) => ({ ...all, [pkg.id]: { ...form, note: event.target.value } }))} /></label></div><div className="package-review-confirmations">{pkg.components.map((component) => <label key={component.id}><input type="checkbox" checked={Boolean(form.confirmations[component.kind])} onChange={(event) => setReviewForms((all) => ({ ...all, [pkg.id]: { ...form, confirmations: { ...form.confirmations, [component.kind]: event.target.checked } } }))} /> Confirm {component.filename || component.kind}{component.sha256 ? ` (${component.sha256.slice(0, 12)}…)` : ""}</label>)}<label><input type="checkbox" checked={Boolean(form.confirmations.__source)} onChange={(event) => setReviewForms((all) => ({ ...all, [pkg.id]: { ...form, confirmations: { ...form.confirmations, __source: event.target.checked } } }))} /> Confirm source snapshot and template version</label></div><div className="package-review-actions"><button className="secondary-button" disabled={reviewWorking === pkg.id || review.state !== "Complete candidate"} onClick={() => void transition(pkg, "In Review")}>Start review</button><button className="small-button" disabled={reviewWorking === pkg.id || review.state !== "In Review"} onClick={() => void transition(pkg, "Reviewed")}>Mark reviewed</button><button className="primary-button" disabled={reviewWorking === pkg.id || review.state !== "Reviewed"} onClick={() => void transition(pkg, "Ready to issue")}>Sign off: Ready to issue</button></div></div>}</article>; })}</div>}
    {(() => { const target = packages.find((pkg) => pkg.assessment_id === assessmentId); return target ? <IssueFinalDeliverablesPanel key={target.id} projectId={projectId} pkg={target} signed={reviews[target.id]?.state === "Ready to issue"} onChanged={() => load()} /> : null; })()}
  </section>;
}

function IssueFinalDeliverablesPanel({ projectId, pkg, signed, onChanged }: { projectId: string; pkg: GeneratedPackage; signed: boolean; onChanged: () => Promise<void> }) {
  const [readiness, setReadiness] = useState<IssueReadiness | null>(null);
  const [working, setWorking] = useState<"backup" | "issue" | null>(null);
  const [error, setError] = useState("");
  const sequence = useRef(0);
  const load = useCallback(async (signal?: AbortSignal, operationSequence?: number) => {
    const current = operationSequence ?? ++sequence.current;
    try {
      const next = await request<IssueReadiness>(`/api/projects/${projectId}/packages/${pkg.id}/issue-readiness`, { signal });
      if (!signal?.aborted && current === sequence.current) { setReadiness(next); setError(""); }
    } catch (caught) {
      if (!signal?.aborted && current === sequence.current) setError(caught instanceof Error ? caught.message : "Could not load issue readiness.");
    }
  }, [projectId, pkg.id]);
  useEffect(() => { const controller = new AbortController(); void load(controller.signal); return () => { sequence.current += 1; controller.abort(); }; }, [load, signed]);
  async function action(kind: "backup" | "issue") {
    const current = sequence.current; setWorking(kind); setError("");
    try {
      const url = `/api/projects/${projectId}/packages/${pkg.id}/${kind === "backup" ? "backups" : "issue"}`;
      await request<IssueReadiness>(url, { method: "POST", body: JSON.stringify(kind === "backup" ? { actor_id: "johnathan" } : { actor_id: "johnathan", backup_id: readiness?.backup_id }) });
      if (current === sequence.current) await load(undefined, current);
      if (kind === "issue" && current === sequence.current) await onChanged();
    } catch (caught) { if (current === sequence.current) setError(caught instanceof Error ? caught.message : `${kind} failed.`); }
    finally { if (current === sequence.current) setWorking(null); }
  }
  const value = (v: unknown) => typeof v === "string" ? v : JSON.stringify(v);
  if (!readiness && !error) return <section className="issue-deliverables-panel"><p>Loading issue readiness…</p></section>;
  return <section className="issue-deliverables-panel" aria-labelledby="issue-deliverables-title" aria-busy={working !== null}>
    <div className="section-title"><div><p className="eyebrow">ISSUE FINAL DELIVERABLES</p><h2 id="issue-deliverables-title">Complete backup and issue</h2></div>{readiness && <span className={`readiness-state ${readiness.status === "Ready" ? "ready" : "blocked"}`}>{readiness.status}</span>}</div>
    {error && <p className="error-copy" role="alert">{error}</p>}
    {readiness?.blockers?.length ? <ul className="issue-blockers">{readiness.blockers.map((b, i) => <li key={i}>{typeof b === "string" ? b : value(b.detail ?? b.reason ?? b.message ?? b)}</li>)}</ul> : null}
    {readiness?.failure && <p className="package-review-error" role="alert">Backup failed{readiness.failure.stage ? ` at ${readiness.failure.stage}` : ""}: {readiness.failure.reason ?? "unknown reason"}{readiness.failure.attempt_id ? ` (attempt ${readiness.failure.attempt_id})` : ""}</p>}
    {readiness?.backup_id && <p className="issue-identity">Backup <code>{readiness.backup_id}</code>{readiness.backup_manifest_sha256 && <> · Manifest SHA-256 <code>{readiness.backup_manifest_sha256}</code></>}{readiness.backup_completed_at && <> · {new Date(readiness.backup_completed_at).toLocaleString()}</>}</p>}
    {readiness?.issued_snapshot_id && <p className="readiness-ok">Issued snapshot <code>{readiness.issued_snapshot_id}</code>{readiness.issued_at && <> · {new Date(readiness.issued_at).toLocaleString()}</>}</p>}
    {!readiness?.issued_snapshot_id && <div className="package-review-actions"><button className="secondary-button" disabled={working !== null || readiness?.status !== "Ready" || Boolean(readiness?.backup_id)} onClick={() => void action("backup")}>{working === "backup" ? "Creating and validating backup…" : "Create and validate backup"}</button><button className="primary-button" disabled={working !== null || !readiness?.backup_id || readiness.status !== "Ready"} onClick={() => void action("issue")}>{working === "issue" ? "Issuing…" : "Issue final deliverables"}</button></div>}
  </section>;
}

function ReopenAssessmentForm({ projectId, packageId, records, onReopened }: { projectId: string; packageId: string; records: RecordIndex[]; onReopened: () => Promise<void> }) {
  const [open, setOpen] = useState(false);
  const [substantive, setSubstantive] = useState(false);
  const [filter, setFilter] = useState("");
  const [selected, setSelected] = useState<Record<string, boolean>>({});
  const [rationale, setRationale] = useState("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const affected = Object.keys(selected).filter((id) => selected[id]);
  const choices = records.filter((record) => record.editable_determination && `${record.citation} ${record.title}`.toLowerCase().includes(filter.trim().toLowerCase())).slice(0, 40);
  const ready = substantive && affected.length > 0 && rationale.trim().length > 0;
  async function submit() {
    setWorking(true); setError("");
    try {
      await request(`/api/projects/${projectId}/packages/${packageId}/reopen`, { method: "POST", body: JSON.stringify({ actor_id: "johnathan", classification: "substantive", affected_record_ids: affected, rationale: rationale.trim() }) });
      await onReopened();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Reopening failed."); setWorking(false); }
  }
  if (!open) return <div className="presentation-correction"><button className="secondary-button" onClick={() => setOpen(true)}>Reopen for substantive correction…</button></div>;
  return <div className="presentation-correction" aria-labelledby="reopen-title">
    <strong id="reopen-title">Reopen for substantive correction</strong>
    <p>Creates a new assessment revision. Only the records you select must be revalidated; everything else carries over unchanged. The issued package stays current until a new one is reviewed, backed up, and issued.</p>
    {error && <p className="package-review-error" role="alert">{error}</p>}
    <label><input type="checkbox" checked={substantive} onChange={(event) => setSubstantive(event.target.checked)} /> This correction changes assessment content</label>
    <label>Find affected records<input value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Citation or title…" /></label>
    <div className="reopen-record-list" role="group" aria-label="Affected records">{choices.map((record) => <label key={record.record_id}><input type="checkbox" checked={Boolean(selected[record.record_id])} onChange={(event) => setSelected((all) => ({ ...all, [record.record_id]: event.target.checked }))} /> {record.citation} · {record.title}</label>)}</div>
    <small>{affected.length} record{affected.length === 1 ? "" : "s"} selected</small>
    <label>Reason for reopening<textarea rows={2} value={rationale} onChange={(event) => setRationale(event.target.value)} /></label>
    <div className="package-review-actions"><button className="secondary-button" disabled={working} onClick={() => setOpen(false)}>Cancel</button><button className="primary-button" disabled={!ready || working} onClick={() => void submit()}>{working ? "Reopening…" : "Reopen assessment"}</button></div>
  </div>;
}

export function RevalidationPanel({ projectId, assessmentId, reopening, items, currentRecordId, onChanged, onOpenRecord }: { projectId: string; assessmentId: string; reopening: AssessmentReopening; items: RevalidationItem[]; currentRecordId: string; onChanged: () => void; onOpenRecord: (recordId: string) => void }) {
  const [done, setDone] = useState<Record<string, boolean>>(() => Object.fromEntries(items.filter((item) => item.revalidated_by).map((item) => [item.record_id, true])));
  const [note, setNote] = useState("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const pending = items.filter((item) => !done[item.record_id]);
  const current = pending.find((item) => item.record_id === currentRecordId);
  async function revalidate(recordId: string) {
    setWorking(true); setError("");
    try {
      await request(`/api/projects/${projectId}/assessments/${assessmentId}/records/${recordId}/revalidate`, { method: "POST", body: JSON.stringify({ actor_id: "johnathan", note: note.trim() }) });
      setDone((all) => ({ ...all, [recordId]: true })); setNote(""); onChanged();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Revalidation failed."); }
    finally { setWorking(false); }
  }
  return <section className="revalidation-panel" aria-labelledby="revalidation-title">
    <div className="section-title"><div><p className="eyebrow">REOPENED ASSESSMENT</p><h2 id="revalidation-title">Needs Revalidation</h2></div><span className={`readiness-state ${pending.length === 0 ? "ready" : "blocked"}`}>{pending.length === 0 ? "All revalidated" : `${pending.length} of ${items.length} remaining`}</span></div>
    <small>Reopened for: {reopening.rationale}. All other records carried over unchanged.</small>
    {error && <p className="package-review-error" role="alert">{error}</p>}
    <ul>{items.map((item) => <li key={item.id}>{done[item.record_id] ? <span>Revalidated · {item.record_id}</span> : <button className="text-button" onClick={() => onOpenRecord(item.record_id)}>{item.record_id}</button>}</li>)}</ul>
    {current && <div className="presentation-correction"><label>Revalidation note<textarea rows={2} value={note} onChange={(event) => setNote(event.target.value)} /></label><div className="package-review-actions"><button className="primary-button" disabled={!note.trim() || working} onClick={() => void revalidate(current.record_id)}>{working ? "Saving…" : "Mark revalidated"}</button></div></div>}
  </section>;
}

function PresentationCorrectionForm({ projectId, packageId, onCreated }: { projectId: string; packageId: string; onCreated: () => Promise<void> }) {
  const [presentationOnly, setPresentationOnly] = useState(false);
  const [attested, setAttested] = useState(false);
  const [reason, setReason] = useState("");
  const [working, setWorking] = useState(false);
  const [error, setError] = useState("");
  const ready = presentationOnly && attested && reason.trim().length > 0;
  async function submit() {
    setWorking(true); setError("");
    try {
      await request(`/api/projects/${projectId}/packages/${packageId}/corrections`, { method: "POST", body: JSON.stringify({ actor_id: "johnathan", classification: "presentation_only", unchanged_source_attested: true, reason: reason.trim() }) });
      setPresentationOnly(false); setAttested(false); setReason("");
      await onCreated();
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Correction failed."); }
    finally { setWorking(false); }
  }
  return <div className="presentation-correction" aria-labelledby="presentation-correction-title">
    <strong id="presentation-correction-title">Presentation-only correction</strong>
    <p>Creates a new package from the same source snapshot. It must be reviewed, signed, backed up, and issued; this issue stays current until then.</p>
    {error && <p className="package-review-error" role="alert">{error}</p>}
    <label><input type="checkbox" checked={presentationOnly} onChange={(event) => setPresentationOnly(event.target.checked)} /> This correction changes presentation only</label>
    <label><input type="checkbox" checked={attested} onChange={(event) => setAttested(event.target.checked)} /> I confirm the assessment, Profile, evidence, determinations, risks, and remediation are unchanged</label>
    <label>Correction reason<textarea rows={2} value={reason} onChange={(event) => setReason(event.target.value)} /></label>
    <div className="package-review-actions"><button className="secondary-button" disabled={!ready || working} onClick={() => void submit()}>{working ? "Generating corrected package…" : "Create corrected package"}</button></div>
  </div>;
}
