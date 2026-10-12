import {
  CircleAlert,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { request } from "../../api";
import type { AssessmentReopening, RecordIndex, RevalidationItem } from "../../types";

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

export function ReopenAssessmentForm({ projectId, packageId, records, onReopened }: { projectId: string; packageId: string; records: RecordIndex[]; onReopened: () => Promise<void> }) {
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
  if (!open) return <div className="presentation-correction"><button className="secondary-button" onClick={() => setOpen(true)}>Change findings (new version)…</button></div>;
  return <div className="presentation-correction" aria-labelledby="reopen-title">
    <strong id="reopen-title">Change findings (new version)</strong>
    <p>Creates a new assessment revision. Only the records you select must be revalidated; everything else carries over unchanged. The current final version stays in place until you finalize the new one.</p>
    {error && <p className="package-review-error" role="alert">{error}</p>}
    <label><input type="checkbox" checked={substantive} onChange={(event) => setSubstantive(event.target.checked)} /> This correction changes assessment content</label>
    <label>Find affected records<input value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Citation or title…" /></label>
    <div className="reopen-record-list" role="group" aria-label="Affected records">{choices.map((record) => <label key={record.record_id}><input type="checkbox" checked={Boolean(selected[record.record_id])} onChange={(event) => setSelected((all) => ({ ...all, [record.record_id]: event.target.checked }))} /> {record.citation} · {record.title}</label>)}</div>
    <small>{affected.length} record{affected.length === 1 ? "" : "s"} selected</small>
    <label>Reason for the change<textarea rows={2} value={rationale} onChange={(event) => setRationale(event.target.value)} /></label>
    <div className="package-review-actions"><button className="secondary-button" disabled={working} onClick={() => setOpen(false)}>Cancel</button><button className="primary-button" disabled={!ready || working} onClick={() => void submit()}>{working ? "Starting…" : "Start new version"}</button></div>
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
