import { CircleAlert, FileUp, Link2 } from "lucide-react";
import { FormEvent, useState } from "react";
import "../evidence/evidence.css";

import { request } from "../../api";
import { artifactLabel } from "../../lib/evidence";
import type { Artifact, RecordSummary } from "../../types";

/**
 * "Link evidence" on the requirement view (#142, AC-007): choose one library
 * artifact, tick several of the requirement's objectives, and write one
 * rationale that each mapping keeps as its own copy (editable per mapping
 * afterwards). Mapping is all-or-nothing on the server.
 */
export function LinkEvidencePicker({
  projectId,
  assessmentId,
  objectives,
  artifacts,
  linked,
  focusedObjectiveId,
  onLinked,
  onArtifactsChanged,
  onSaveState,
}: {
  projectId: string;
  assessmentId: string;
  objectives: RecordSummary[];
  artifacts: Artifact[];
  /** Artifact IDs already mapped to each objective. */
  linked: Record<string, string[]>;
  focusedObjectiveId: string;
  onLinked: (recordIds: string[]) => void;
  onArtifactsChanged: () => void;
  onSaveState: (state: "saving" | "saved" | "error", message?: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const [artifactId, setArtifactId] = useState("");
  const [ticked, setTicked] = useState<Set<string>>(new Set());
  const [rationale, setRationale] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const alreadyLinked = (recordId: string) => Boolean(artifactId) && (linked[recordId] ?? []).includes(artifactId);
  const chosen = objectives.filter((objective) => ticked.has(objective.record_id) && !alreadyLinked(objective.record_id));
  const artifact = artifacts.find((item) => item.id === artifactId);

  function start() {
    setOpen(true);
    setError("");
    setTicked(new Set(focusedObjectiveId ? [focusedObjectiveId] : []));
  }

  function toggle(recordId: string) {
    setTicked((current) => {
      const next = new Set(current);
      if (next.has(recordId)) next.delete(recordId);
      else next.add(recordId);
      return next;
    });
  }

  async function upload(file: File) {
    setBusy(true);
    setError("");
    const data = new FormData();
    data.append("file", file);
    try {
      const created = await request<{ id: string }>(`/api/projects/${projectId}/evidence`, { method: "POST", body: data });
      setArtifactId(created.id);
      onArtifactsChanged();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not store the file.");
    } finally {
      setBusy(false);
    }
  }

  async function link(event: FormEvent) {
    event.preventDefault();
    if (!artifactId || chosen.length === 0 || !rationale.trim()) return;
    setBusy(true);
    setError("");
    onSaveState("saving");
    const recordIds = chosen.map((objective) => objective.record_id);
    try {
      await request(`/api/projects/${projectId}/assessments/${assessmentId}/evidence-mappings/bulk`, {
        method: "POST",
        body: JSON.stringify({ artifact_id: artifactId, record_ids: recordIds, rationale: rationale.trim() }),
      });
      onSaveState("saved");
      setOpen(false);
      setArtifactId("");
      setRationale("");
      onLinked(recordIds);
      onArtifactsChanged();
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Could not link the evidence.";
      setError(message);
      onSaveState("error", message);
    } finally {
      setBusy(false);
    }
  }

  if (!open) {
    return (
      <button type="button" className="small-button link-evidence-open" onClick={start}>
        <Link2 size={14} /> Link evidence
      </button>
    );
  }

  return (
    <form className="link-evidence" aria-label="Link evidence to objectives" onSubmit={link}>
      <label>
        Evidence file
        <select aria-label="Evidence file" value={artifactId} onChange={(event) => setArtifactId(event.target.value)}>
          <option value="">Choose from the library…</option>
          {artifacts.map((item) => (
            <option key={item.id} value={item.id} title={`SHA-256 ${item.sha256}`}>
              {artifactLabel(item)}{item.review_status === "stale" ? " · stale" : item.review_status === "due_soon" ? " · due soon" : ""}
            </option>
          ))}
        </select>
      </label>
      <label className="upload-button">
        <FileUp size={15} /> {busy && !artifactId ? "Storing file…" : "Or upload a new file"}
        <input type="file" aria-label="Upload a new evidence file" onChange={(event) => event.target.files?.[0] && void upload(event.target.files[0])} />
      </label>
      {artifact?.review_status === "stale" && (
        <p className="link-evidence-warning"><CircleAlert size={13} /> This file is past its review date. Linked objectives stay evidence pending until it is renewed.</p>
      )}
      <fieldset>
        <legend>Objectives it supports</legend>
        {objectives.map((objective) => {
          const already = alreadyLinked(objective.record_id);
          return (
            <label key={objective.record_id} className={already ? "already-linked" : ""}>
              <input
                type="checkbox"
                checked={already || ticked.has(objective.record_id)}
                disabled={already}
                onChange={() => toggle(objective.record_id)}
              />
              <span><strong>{objective.citation}</strong> {objective.regulation_text}</span>
              {already && <small>already linked</small>}
            </label>
          );
        })}
      </fieldset>
      <label>
        Support rationale <small>applies to each ticked objective; edit any one afterwards</small>
        <textarea
          aria-label="Support rationale"
          rows={2}
          value={rationale}
          onChange={(event) => setRationale(event.target.value)}
          placeholder="What does this file show for these objectives?"
        />
      </label>
      {error && <p className="form-error"><CircleAlert size={14} /> {error}</p>}
      <div className="link-evidence-actions">
        <button type="submit" className="small-button" disabled={busy || !artifactId || chosen.length === 0 || !rationale.trim()}>
          Link to {chosen.length} objective{chosen.length === 1 ? "" : "s"}
        </button>
        <button type="button" className="text-button" onClick={() => setOpen(false)}>Cancel</button>
      </div>
    </form>
  );
}
