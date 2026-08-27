import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  Check,
  ChevronDown,
  CircleAlert,
  Cloud,
  FileCheck2,
  FileUp,
  FolderKanban,
  ListFilter,
  LoaderCircle,
  Search,
  ShieldCheck,
  UserRound,
  X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ApiError, request } from "./api";
import { ProfilePanel } from "./ProfilePanel";
import type {
  Artifact,
  Assessment,
  Client,
  EvidenceMapping,
  Prompt,
  ProfileReadiness,
  RecordDetail,
  Status,
} from "./types";

function ReadinessPanel({
  readiness,
  hasAssessment,
  onChanged,
}: {
  readiness: ProfileReadiness;
  hasAssessment: boolean;
  onChanged: () => Promise<void>;
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

  async function acknowledge() {
    setWorking(true);
    setError("");
    try {
      await request(`/api/projects/${readiness.project_id}/profile-readiness/acknowledgement`, {
        method: "POST",
      });
      await onChanged();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Acknowledgement failed.");
    } finally {
      setWorking(false);
    }
  }

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
        <article>
          <h2>Operating boundary</h2>
          <code>{readiness.boundary_document}</code>
          <p>
            Acknowledging this document records that it was reviewed. It is explicitly not an
            attestation that content is free of CUI, PHI, or ePHI.
          </p>
          {readiness.acknowledgement ? (
            <p className="readiness-ok">
              Acknowledged by {readiness.acknowledgement.actor.display_name}
            </p>
          ) : (
            <button className="secondary-button" disabled={working} onClick={() => void acknowledge()}>
              Acknowledge boundary
            </button>
          )}
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
          <label>
            Named reviewer
            <input value={reviewedBy} onChange={(event) => setReviewedBy(event.target.value)} />
          </label>
          <label>
            Review / approval evidence
            <textarea rows={2} value={approvalEvidence} onChange={(event) => setApprovalEvidence(event.target.value)} />
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
        <button className="small-button" disabled={working || !readiness.acknowledgement} type="submit">
          Record transition
        </button>
      </form>
    </section>
  );
}

function statusClass(status: Status): string {
  return status ? `status-${status.toLowerCase().replaceAll(" ", "-").replace("/", "")}` : "status-blank";
}

function StatusPill({ status, derived = false }: { status: Status; derived?: boolean }) {
  return (
    <span className={`status-pill ${statusClass(status)}`}>
      {derived ? `Derived · ${status || "Blank"}` : status || "Blank"}
    </span>
  );
}

type RoutineSaveState = "saving" | "saved" | "failed";
type RoutineSaveReporter = (
  key: string,
  state: RoutineSaveState | null,
) => void;
type RoutineRecordSaveCoordinator = <T>(
  recordKey: string,
  write: () => Promise<T>,
) => Promise<T>;

function sameDraft<T>(left: T, right: T): boolean {
  return JSON.stringify(left) === JSON.stringify(right);
}

/**
 * Routine edits on one assessment record share a single write chain. The map
 * intentionally holds a separate chain for each record, not a global queue.
 */
function useRoutineRecordSaveCoordinator(): RoutineRecordSaveCoordinator {
  const chainsRef = useRef(new Map<string, Promise<void>>());
  return useCallback<RoutineRecordSaveCoordinator>(async (recordKey, write) => {
    const prior = chainsRef.current.get(recordKey) ?? Promise.resolve();
    const result = prior.then(write, write);
    const chain = result.then(
      () => undefined,
      () => undefined,
    );
    chainsRef.current.set(recordKey, chain);
    try {
      return await result;
    } finally {
      if (chainsRef.current.get(recordKey) === chain) chainsRef.current.delete(recordKey);
    }
  }, []);
}

/**
 * This deliberately covers only the three routine assessment edits in this
 * workspace. Each record shares one write chain, while separate records
 * remain independently saveable.
 */
function useRoutineAutosave<T>(
  key: string,
  recordKey: string,
  initialDraft: T,
  persist: (draft: T) => Promise<unknown>,
  report: RoutineSaveReporter,
  coordinateSave: RoutineRecordSaveCoordinator,
  onFinalSuccess?: () => void,
) {
  const [draft, setDraft] = useState(initialDraft);
  const [state, setState] = useState<RoutineSaveState>("saved");
  const draftRef = useRef(initialDraft);
  const persistedRef = useRef(initialDraft);
  const initialDraftRef = useRef(initialDraft);
  const draftVersionRef = useRef(0);
  const queuedVersionRef = useRef<number | null>(null);
  const runningRef = useRef(false);
  const keyGenerationRef = useRef(0);
  const activeKeyRef = useRef(key);
  const persistRef = useRef(persist);
  const recordKeyRef = useRef(recordKey);
  const coordinateSaveRef = useRef(coordinateSave);
  const onFinalSuccessRef = useRef(onFinalSuccess);
  persistRef.current = persist;
  recordKeyRef.current = recordKey;
  coordinateSaveRef.current = coordinateSave;
  onFinalSuccessRef.current = onFinalSuccess;
  initialDraftRef.current = initialDraft;
  if (activeKeyRef.current !== key) {
    activeKeyRef.current = key;
    keyGenerationRef.current += 1;
  }

  const processQueue = useCallback(async () => {
    if (runningRef.current || queuedVersionRef.current === null) return;
    runningRef.current = true;
    const savingGeneration = keyGenerationRef.current;
    const savingVersion = queuedVersionRef.current;
    const savingDraft = draftRef.current;
    const savingRecordKey = recordKeyRef.current;
    const save = persistRef.current;
    setState("saving");
    try {
      await coordinateSaveRef.current(savingRecordKey, () => save(savingDraft));
      if (keyGenerationRef.current !== savingGeneration) return;
      persistedRef.current = savingDraft;
      if (queuedVersionRef.current !== null && queuedVersionRef.current > savingVersion) {
        runningRef.current = false;
        void processQueue();
        return;
      }
      queuedVersionRef.current = null;
      runningRef.current = false;
      if (draftVersionRef.current === savingVersion) {
        setState("saved");
        onFinalSuccessRef.current?.();
      } else {
        setState("saving");
      }
    } catch {
      if (keyGenerationRef.current !== savingGeneration) return;
      if (queuedVersionRef.current !== null && queuedVersionRef.current > savingVersion) {
        runningRef.current = false;
        void processQueue();
        return;
      }
      runningRef.current = false;
      setState("failed");
    }
  }, []);

  const stage = useCallback((next: T) => {
    draftRef.current = next;
    draftVersionRef.current += 1;
    setDraft(next);
    if (!sameDraft(next, persistedRef.current)) setState("saving");
  }, []);

  const save = useCallback((next: T) => {
    if (
      sameDraft(next, draftRef.current)
      && queuedVersionRef.current === draftVersionRef.current
    ) {
      return;
    }
    stage(next);
    const version = draftVersionRef.current;
    if (
      !runningRef.current
      && queuedVersionRef.current === null
      && sameDraft(next, persistedRef.current)
    ) {
      setState("saved");
      return;
    }
    queuedVersionRef.current = version;
    setState("saving");
    void processQueue();
  }, [processQueue, stage]);

  const retry = useCallback(() => {
    queuedVersionRef.current = draftVersionRef.current;
    setState("saving");
    void processQueue();
  }, [processQueue]);

  useEffect(() => {
    keyGenerationRef.current += 1;
    const resetDraft = initialDraftRef.current;
    draftRef.current = resetDraft;
    persistedRef.current = resetDraft;
    draftVersionRef.current = 0;
    queuedVersionRef.current = null;
    runningRef.current = false;
    setDraft(resetDraft);
    setState("saved");
  }, [key]);

  useEffect(() => () => {
    keyGenerationRef.current += 1;
  }, []);

  useEffect(() => {
    report(key, state);
  }, [key, report, state]);

  useEffect(() => () => report(key, null), [key, report]);

  return { draft, state, stage, save, retry };
}

function RoutineSaveStatus({
  state,
  retry,
  label,
}: {
  state: RoutineSaveState;
  retry: () => void;
  label: string;
}) {
  if (state === "saved") return null;
  return (
    <p className={`routine-save-state ${state}`} aria-live="polite">
      {state === "saving" ? "Saving" : "Save failed"}
      {state === "failed" && (
        <button className="text-button" type="button" onClick={retry} aria-label={`Retry ${label}`}>
          Retry
        </button>
      )}
    </p>
  );
}

function Setup({ onCreated }: { onCreated: (projectId: string) => void }) {
  const [clientName, setClientName] = useState("");
  const [projectName, setProjectName] = useState("HIPAA 2026");
  const [error, setError] = useState("");
  const [working, setWorking] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setWorking(true);
    setError("");
    try {
      const client = await request<{ id: string }>("/api/clients", {
        method: "POST",
        body: JSON.stringify({ name: clientName }),
      });
      const project = await request<{ id: string }>(`/api/clients/${client.id}/projects`, {
        method: "POST",
        body: JSON.stringify({ name: projectName }),
      });
      onCreated(project.id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not create the workspace.");
    } finally {
      setWorking(false);
    }
  }

  return (
    <main className="setup-shell">
      <section className="setup-brand">
        <div className="brand-mark"><ShieldCheck size={26} /></div>
        <p className="eyebrow">RAINTECH GRC</p>
        <h1>Begin with the work,<br />not the setup.</h1>
        <p>
          Create the first client project. Its profile begins with intake, and any later
          assessment is pinned to a versioned framework catalog.
        </p>
        <div className="setup-facts">
          <span><Check size={16} /> Complete cited walkthrough</span>
          <span><Check size={16} /> Source-attributed guidance</span>
          <span><Check size={16} /> Local SQLite workspace</span>
        </div>
      </section>
      <form className="setup-card" onSubmit={submit}>
        <p className="eyebrow">FIRST WORKSPACE</p>
        <h2>Create a client project</h2>
        <label>
          Client name
          <input
            autoFocus
            required
            value={clientName}
            onChange={(event) => setClientName(event.target.value)}
            placeholder="e.g. Northwind Health"
          />
        </label>
        <label>
          Project name
          <input
            required
            value={projectName}
            onChange={(event) => setProjectName(event.target.value)}
          />
        </label>
        <div className="pinned-framework">
          <BookOpen size={18} />
          <div>
            <strong>HIPAA 45 CFR Part 164</strong>
            <span>Version hipaa-45cfr164-2026-07-01</span>
          </div>
        </div>
        {error && <p className="form-error"><CircleAlert size={16} /> {error}</p>}
        <button className="primary-button" disabled={working} type="submit">
          {working ? <LoaderCircle className="spin" size={18} /> : <ArrowRight size={18} />}
          Create workspace
        </button>
      </form>
    </main>
  );
}

function WorkspaceCreator({
  clients,
  onCreated,
  onCancel,
}: {
  clients: Client[];
  onCreated: (projectId: string) => void;
  onCancel: () => void;
}) {
  const [clientId, setClientId] = useState(clients[0]?.id || "__new__");
  const [clientName, setClientName] = useState("");
  const [projectName, setProjectName] = useState("HIPAA 2026");
  const [error, setError] = useState("");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      let destinationClientId = clientId;
      if (clientId === "__new__") {
        const created = await request<{ id: string }>("/api/clients", {
          method: "POST",
          body: JSON.stringify({ name: clientName }),
        });
        destinationClientId = created.id;
      }
      const project = await request<{ id: string }>(
        `/api/clients/${destinationClientId}/projects`,
        { method: "POST", body: JSON.stringify({ name: projectName }) },
      );
      onCreated(project.id);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not create the workspace.");
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <form className="workspace-modal" onSubmit={submit} aria-label="Create client project">
        <div>
          <p className="eyebrow">NEW WORKSPACE</p>
          <h2>Add a HIPAA project</h2>
        </div>
        <label>
          Client
          <select value={clientId} onChange={(event) => setClientId(event.target.value)}>
            {clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}
            <option value="__new__">New client…</option>
          </select>
        </label>
        {clientId === "__new__" && (
          <label>
            New client name
            <input required value={clientName} onChange={(event) => setClientName(event.target.value)} />
          </label>
        )}
        <label>
          Project name
          <input required value={projectName} onChange={(event) => setProjectName(event.target.value)} />
        </label>
        {error && <p className="form-error"><CircleAlert size={16} /> {error}</p>}
        <div className="modal-actions">
          <button className="small-button" type="submit">Create and open</button>
          <button className="text-button" type="button" onClick={onCancel}>Cancel</button>
        </div>
      </form>
    </div>
  );
}

function PromptCard({
  prompt,
  assessment,
  recordId,
  onRoutineSaveState,
  coordinateSave,
}: {
  prompt: Prompt;
  assessment: Assessment;
  recordId: string;
  onRoutineSaveState: RoutineSaveReporter;
  coordinateSave: RoutineRecordSaveCoordinator;
}) {
  const {
    draft: answer,
    state: answerSaveState,
    stage: stageAnswer,
    save: saveAnswer,
    retry: retryAnswer,
  } = useRoutineAutosave(
    `prompt:${assessment.id}:${prompt.id}`,
    `record:${assessment.id}:${recordId}`,
    prompt.answer,
    async (nextAnswer) => {
      await request(`/api/assessments/${assessment.id}/prompts/${prompt.id}/answer`, {
        method: "PUT",
        body: JSON.stringify({ answer: nextAnswer }),
      });
    },
    onRoutineSaveState,
    coordinateSave,
  );

  return (
    <article className={`prompt-card role-${prompt.role}`}>
      <div className="prompt-heading">
        {prompt.render_checkbox ? (
          <input aria-label={prompt.text} type="checkbox" tabIndex={-1} />
        ) : (
          <span className="context-dot" aria-hidden="true" />
        )}
        <div>
          <p>{prompt.text}</p>
          <span>
            {prompt.source_detail || prompt.source}
            {prompt.cfr_paragraph && ` · ${prompt.cfr_paragraph}`}
          </span>
        </div>
      </div>
      <textarea
        aria-label={`Answer: ${prompt.text}`}
        value={answer}
        onChange={(event) => stageAnswer(event.target.value)}
        onBlur={() => saveAnswer(answer)}
        placeholder="Record the answer to this question…"
        rows={2}
      />
      <RoutineSaveStatus state={answerSaveState} retry={retryAnswer} label="answer" />
    </article>
  );
}

function DeterminationPanel({
  assessmentId,
  statuses,
  detail,
  onRoutineSaveState,
  coordinateSave,
  onFinalSuccess,
}: {
  assessmentId: string;
  statuses: Status[];
  detail: RecordDetail;
  onRoutineSaveState: RoutineSaveReporter;
  coordinateSave: RoutineRecordSaveCoordinator;
  onFinalSuccess: () => void;
}) {
  const {
    draft: form,
    state: determinationSaveState,
    stage: stageDetermination,
    save,
    retry: retryDetermination,
  } = useRoutineAutosave(
    `determination:${assessmentId}:${detail.record.record_id}`,
    `record:${assessmentId}:${detail.record.record_id}`,
    detail.determination,
    async (next) => {
      await request(
        `/api/assessments/${assessmentId}/determinations/${detail.record.record_id}`,
        {
          method: "PUT",
          body: JSON.stringify(next),
        },
      );
    },
    onRoutineSaveState,
    coordinateSave,
    onFinalSuccess,
  );

  if (!detail.record.editable_determination) {
    return (
      <section className="working-section rollup-section">
        <div className="section-title">
          <div><p className="eyebrow">ROLLED UP</p><h3>Derived standard status</h3></div>
          <StatusPill status={detail.determination.status} derived />
        </div>
        <p className="muted">
          This standard has no editable determination. Its status follows the child
          specifications; notes and evidence here remain independently recordable.
        </p>
      </section>
    );
  }

  return (
    <section className="working-section">
      <div className="section-title">
        <div><p className="eyebrow">DECISION</p><h3>Determination</h3></div>
        <StatusPill status={form.status} />
      </div>
      <div className="status-grid">
        {statuses.filter(Boolean).map((status) => (
          <button
            key={status}
            type="button"
            className={form.status === status ? "selected" : ""}
            onClick={() => {
              const next = { ...form, status };
              if (status !== "N/A" && detail.record.designation !== "addressable") save(next);
              else stageDetermination(next);
            }}
          >
            {status}
          </button>
        ))}
      </div>
      {form.status === "N/A" && (
        <label>
          N/A rationale <span className="required">required</span>
          <textarea
            rows={3}
            value={form.na_rationale}
            onChange={(event) => stageDetermination({ ...form, na_rationale: event.target.value })}
            onBlur={() => save(form)}
            placeholder="Explain why this requirement does not apply…"
          />
        </label>
      )}
      {detail.record.designation === "addressable" && (
        <div className="addressable-box">
          <p className="eyebrow">ADDRESSABLE SPECIFICATION</p>
          <label>
            Disposition <span className="required">required</span>
            <select
              value={form.addressable_disposition ?? ""}
              onChange={(event) => {
                const next = { ...form, addressable_disposition: event.target.value };
                if (event.target.value === "standard_measure") save(next);
                else stageDetermination(next);
              }}
            >
              <option value="">Select a disposition…</option>
              <option value="standard_measure">Use the standard measure</option>
              <option value="equivalent_alternative">Equivalent alternative</option>
              <option value="non_implementation">Documented non-implementation</option>
            </select>
          </label>
          {form.addressable_disposition && form.addressable_disposition !== "standard_measure" && (
            <label>
              Reasoning <span className="required">required</span>
              <textarea
                rows={3}
                value={form.disposition_reason}
                onChange={(event) => stageDetermination({ ...form, disposition_reason: event.target.value })}
                onBlur={() => save(form)}
              />
            </label>
          )}
        </div>
      )}
      <details className="interview-box">
        <summary>Document an interview or observation</summary>
        <p>Use this when a Met decision relies on direct observation instead of mapped evidence.</p>
        <textarea
          rows={3}
          value={form.interview_observation}
          onChange={(event) => stageDetermination({ ...form, interview_observation: event.target.value })}
          onBlur={() => form.status && save(form)}
          placeholder="Who was interviewed or what was observed?"
        />
      </details>
      <RoutineSaveStatus state={determinationSaveState} retry={retryDetermination} label="determination" />
    </section>
  );
}

function RecordNotes({
  assessmentId,
  recordId,
  initialNote,
  onRoutineSaveState,
  coordinateSave,
}: {
  assessmentId: string;
  recordId: string;
  initialNote: string;
  onRoutineSaveState: RoutineSaveReporter;
  coordinateSave: RoutineRecordSaveCoordinator;
}) {
  const {
    draft: note,
    state: noteSaveState,
    stage: stageNote,
    save: saveNote,
    retry: retryNote,
  } = useRoutineAutosave(
    `note:${assessmentId}:${recordId}`,
    `record:${assessmentId}:${recordId}`,
    initialNote,
    async (nextNote) => {
      await request(`/api/assessments/${assessmentId}/records/${recordId}/note`, {
        method: "PUT",
        body: JSON.stringify({ note: nextNote }),
      });
    },
    onRoutineSaveState,
    coordinateSave,
  );

  return (
    <section className="working-section">
      <div className="section-title"><div><p className="eyebrow">DISCUSSION</p><h3>Record notes</h3></div></div>
      <textarea
        aria-label="Record notes"
        value={note}
        rows={5}
        placeholder="Record implementation details, scope, and assessor observations…"
        onChange={(event) => stageNote(event.target.value)}
        onBlur={() => saveNote(note)}
      />
      <RoutineSaveStatus state={noteSaveState} retry={retryNote} label="note" />
    </section>
  );
}

function EvidencePanel({
  assessment,
  detail,
  artifacts,
  onChanged,
  onArtifactsChanged,
  onSaveState,
}: {
  assessment: Assessment;
  detail: RecordDetail;
  artifacts: Artifact[];
  onChanged: () => void;
  onArtifactsChanged: () => void;
  onSaveState: (state: "saving" | "saved" | "error", message?: string) => void;
}) {
  const [artifactId, setArtifactId] = useState("");
  const [rationale, setRationale] = useState("");
  const [uploading, setUploading] = useState(false);

  async function upload(file: File) {
    setUploading(true);
    onSaveState("saving");
    const data = new FormData();
    data.append("file", file);
    try {
      const artifact = await request<Artifact>(`/api/projects/${assessment.project.id}/evidence`, {
        method: "POST",
        body: data,
      });
      setArtifactId(artifact.id);
      onArtifactsChanged();
      onSaveState("saved");
    } catch (caught) {
      onSaveState("error", caught instanceof Error ? caught.message : undefined);
    } finally {
      setUploading(false);
    }
  }

  async function mapEvidence(event: FormEvent) {
    event.preventDefault();
    onSaveState("saving");
    try {
      await request(
        `/api/projects/${assessment.project.id}/assessments/${assessment.id}/evidence-mappings`,
        {
        method: "POST",
        body: JSON.stringify({
          artifact_id: artifactId,
          record_id: detail.record.record_id,
          rationale,
        }),
        },
      );
      setRationale("");
      onSaveState("saved");
      onChanged();
      onArtifactsChanged();
    } catch (caught) {
      onSaveState("error", caught instanceof Error ? caught.message : undefined);
    }
  }

  async function unmap(mapping: EvidenceMapping) {
    if (!window.confirm(`Remove the mapping to “${mapping.name}”? The evidence file is retained.`)) return;
    onSaveState("saving");
    try {
      await request(
        `/api/projects/${assessment.project.id}/assessments/${assessment.id}/evidence-mappings/${mapping.mapping_id}`,
        { method: "DELETE" },
      );
      onSaveState("saved");
      onChanged();
      onArtifactsChanged();
    } catch (caught) {
      onSaveState("error", caught instanceof Error ? caught.message : undefined);
    }
  }

  return (
    <section className="working-section">
      <div className="section-title">
        <div><p className="eyebrow">SUPPORT</p><h3>Mapped evidence</h3></div>
        <span className="count-badge">{detail.evidence.length}</span>
      </div>
      <div className="evidence-list">
        {detail.evidence.length === 0 && (
          <p className="empty-copy">No evidence mapped to this record yet.</p>
        )}
        {detail.evidence.map((mapping) => (
          <article className="evidence-item" key={mapping.mapping_id}>
            <FileCheck2 size={18} />
            <div>
              <strong>{mapping.name}</strong>
              <p>{mapping.rationale}</p>
              <span>Version {mapping.version_number}</span>
              <span>SHA-256: {mapping.sha256}</span>
              <span>{mapping.review_state}</span>
              <span>Shared across {mapping.shared_record_count} record{mapping.shared_record_count === 1 ? "" : "s"}</span>
            </div>
            <button className="icon-button" aria-label={`Unmap ${mapping.name}`} onClick={() => void unmap(mapping)}>
              <X size={15} />
            </button>
          </article>
        ))}
      </div>
      <form className="map-form" onSubmit={mapEvidence}>
        <label className="upload-button">
          <FileUp size={16} />
          {uploading ? "Storing file…" : "Add evidence file"}
          <input
            type="file"
            onChange={(event) => event.target.files?.[0] && void upload(event.target.files[0])}
          />
        </label>
        <label>
          Existing artifact
          <select required value={artifactId} onChange={(event) => setArtifactId(event.target.value)}>
            <option value="">Choose evidence…</option>
            {artifacts.map((artifact) => (
              <option key={artifact.id} value={artifact.id}>
                {artifact.name} · Version {artifact.version_number} · SHA-256: {artifact.sha256}
                {" "}({artifact.shared_record_count} mappings)
              </option>
            ))}
          </select>
        </label>
        <label>
          Support rationale
          <textarea
            required
            rows={2}
            value={rationale}
            onChange={(event) => setRationale(event.target.value)}
            placeholder="What does this artifact support here?"
          />
        </label>
        <button className="small-button" type="submit">Map to this record</button>
      </form>
    </section>
  );
}

export function Workspace({
  clients,
  projectId,
  onProjectChange,
  onWorkspaceCreated,
}: {
  clients: Client[];
  projectId: string;
  onProjectChange: (id: string) => void;
  onWorkspaceCreated: (id: string) => void;
}) {
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [readiness, setReadiness] = useState<ProfileReadiness | null>(null);
  const [progress, setProgress] = useState<Assessment["progress"] | null>(null);
  const [recordId, setRecordId] = useState("");
  const [returnRecordId, setReturnRecordId] = useState("");
  const [detail, setDetail] = useState<RecordDetail | null>(null);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [search, setSearch] = useState("");
  const [area, setArea] = useState("all");
  const [saveState, setSaveState] = useState<"saved" | "saving" | "error">("saved");
  const [saveMessage, setSaveMessage] = useState("");
  const [routineSaves, setRoutineSaves] = useState<Map<string, RoutineSaveState>>(new Map());
  const [loading, setLoading] = useState(true);
  const [creatingWorkspace, setCreatingWorkspace] = useState(false);
  const [profileDirty, setProfileDirty] = useState(false);
  const [view, setView] = useState<"assessment" | "overview" | "profile">("assessment");
  const detailTargetRef = useRef({ assessmentId: "", recordId: "" });
  const detailRequestSequenceRef = useRef(0);
  const assessmentRequestSequenceRef = useRef(0);
  const artifactRequestSequenceRef = useRef(0);
  const projectTargetRef = useRef(projectId);
  const coordinateRoutineSave = useRoutineRecordSaveCoordinator();
  projectTargetRef.current = projectId;
  detailTargetRef.current = { assessmentId: assessment?.id ?? "", recordId };

  const loadAssessment = useCallback(async (signal?: AbortSignal) => {
    const targetProjectId = projectId;
    const requestSequence = ++assessmentRequestSequenceRef.current;
    let next: Assessment | null;
    try {
      next = await request<Assessment>(
        `/api/projects/${targetProjectId}/assessment`,
        { signal },
      );
    } catch (error) {
      if (signal?.aborted) return;
      if (error instanceof ApiError && error.status === 404) next = null;
      else throw error;
    }
    if (
      signal?.aborted
      || assessmentRequestSequenceRef.current !== requestSequence
      || projectTargetRef.current !== targetProjectId
    ) return;
    setAssessment(next);
    setProgress(next?.progress ?? null);
    setRecordId(next?.work_list[0]?.record_id || "");
  }, [projectId]);

  const loadReadiness = useCallback(async (signal?: AbortSignal) => {
    const targetProjectId = projectId;
    const next = await request<ProfileReadiness>(
      `/api/projects/${targetProjectId}/profile-readiness`,
      { signal },
    );
    if (signal?.aborted || projectTargetRef.current !== targetProjectId) return undefined;
    setReadiness(next);
    return next;
  }, [projectId]);

  const reloadWorkspace = useCallback(async () => {
    const nextReadiness = await loadReadiness();
    if (nextReadiness === undefined) return;
    if (nextReadiness?.assessment_exists) await loadAssessment();
    else {
      setAssessment(null);
      setProgress(null);
      setRecordId("");
    }
  }, [loadAssessment, loadReadiness]);

  const refreshAssessmentProgress = useCallback(async () => {
    if (!assessment) return;
    const targetProjectId = assessment.project.id;
    const targetAssessmentId = assessment.id;
    const requestSequence = ++assessmentRequestSequenceRef.current;
    const next = await request<Assessment>(`/api/projects/${targetProjectId}/assessment`);
    if (
      assessmentRequestSequenceRef.current !== requestSequence
      || projectTargetRef.current !== targetProjectId
    ) return;
    if (detailTargetRef.current.assessmentId === targetAssessmentId) {
      setProgress(next.progress);
    }
  }, [assessment]);

  const loadDetail = useCallback(async () => {
    if (!assessment || !recordId) return;
    const target = { assessmentId: assessment.id, recordId };
    const requestSequence = ++detailRequestSequenceRef.current;
    const next = await request<RecordDetail>(
      `/api/projects/${assessment.project.id}/assessments/${target.assessmentId}/records/${encodeURIComponent(target.recordId)}`,
    );
    if (
      detailRequestSequenceRef.current === requestSequence &&
      detailTargetRef.current.assessmentId === target.assessmentId
      && detailTargetRef.current.recordId === target.recordId
    ) {
      setDetail(next);
    }
  }, [assessment, recordId]);

  const loadArtifacts = useCallback(async (signal?: AbortSignal) => {
    if (!assessment) return;
    const targetProjectId = assessment.project.id;
    const requestSequence = ++artifactRequestSequenceRef.current;
    let next: Artifact[];
    try {
      next = await request<Artifact[]>(
        `/api/projects/${targetProjectId}/evidence`,
        { signal },
      );
    } catch (error) {
      if (signal?.aborted) return;
      throw error;
    }
    if (
      signal?.aborted
      || artifactRequestSequenceRef.current !== requestSequence
      || projectTargetRef.current !== targetProjectId
    ) return;
    setArtifacts(next);
  }, [assessment]);

  useEffect(() => {
    const controller = new AbortController();
    setAssessment(null);
    setReadiness(null);
    setProgress(null);
    setRecordId("");
    setLoading(true);
    setDetail(null);
    setArtifacts([]);
    void (async () => {
      try {
        const nextReadiness = await loadReadiness(controller.signal);
        if (nextReadiness?.assessment_exists) await loadAssessment(controller.signal);
      } catch (error) {
        if (!controller.signal.aborted) throw error;
      } finally {
        if (!controller.signal.aborted && projectTargetRef.current === projectId) setLoading(false);
      }
    })();
    return () => controller.abort();
  }, [loadAssessment, loadReadiness, projectId]);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

  useEffect(() => {
    const controller = new AbortController();
    void loadArtifacts(controller.signal);
    return () => controller.abort();
  }, [loadArtifacts]);

  function updateSaveState(state: "saving" | "saved" | "error", message = "") {
    setSaveState(state);
    setSaveMessage(message);
  }

  const reportRoutineSave = useCallback<RoutineSaveReporter>((key, state) => {
    setRoutineSaves((current) => {
      const next = new Map(current);
      if (state === null) next.delete(key);
      else next.set(key, state);
      return next;
    });
  }, []);

  const routineSaveState = useMemo<RoutineSaveState>(() => {
    const states = [...routineSaves.values()];
    if (states.includes("failed")) return "failed";
    if (states.includes("saving")) return "saving";
    return "saved";
  }, [routineSaves]);

  const hasUnsavedRoutineEdit = routineSaveState !== "saved";
  const visibleSaveState: RoutineSaveState | "error" =
    routineSaveState !== "saved" ? routineSaveState : saveState;
  const visibleSaveMessage =
    visibleSaveState === "failed"
      ? "Save failed"
      : visibleSaveState === "error"
        ? saveMessage || "Save failed"
        : "";

  const confirmRoutineNavigation = useCallback(() => {
    if (!hasUnsavedRoutineEdit && !profileDirty) return true;
    return window.confirm("Changes are still saving or failed to save. Leave this record?");
  }, [hasUnsavedRoutineEdit, profileDirty]);

  const changeRecord = useCallback((nextRecordId: string, nextReturnRecordId = "") => {
    if (nextRecordId === recordId || !confirmRoutineNavigation()) return;
    setReturnRecordId(nextReturnRecordId);
    setRecordId(nextRecordId);
  }, [confirmRoutineNavigation, recordId]);

  const changeProject = useCallback((nextProjectId: string) => {
    if (nextProjectId === projectId || !confirmRoutineNavigation()) return false;
    onProjectChange(nextProjectId);
    return true;
  }, [confirmRoutineNavigation, onProjectChange, projectId]);

  const changeView = useCallback((nextView: "assessment" | "overview" | "profile") => {
    if (nextView === view || !confirmRoutineNavigation()) return;
    setView(nextView);
  }, [confirmRoutineNavigation, view]);

  useEffect(() => {
    if (!hasUnsavedRoutineEdit && !profileDirty) return;
    const warnBeforeUnload = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [hasUnsavedRoutineEdit, profileDirty]);

  const filtered = useMemo(() => {
    if (!assessment) return [];
    const term = search.toLowerCase();
    return assessment.work_list.filter(
      (record) =>
        (area === "all" || record.work_area === area) &&
        (!term ||
          record.title.toLowerCase().includes(term) ||
          record.citation.toLowerCase().includes(term)),
    );
  }, [assessment, search, area]);

  const projects = clients.flatMap((client) =>
    client.projects.map((project) => ({ ...project, clientName: client.name })),
  );

  const selectedProject = projects.find((project) => project.id === projectId);

  if (loading || !readiness) {
    return <div className="loading-screen"><LoaderCircle className="spin" /><span>Opening assessment workspace…</span></div>;
  }

  if (!assessment || !progress || !detail) {
    return (
      <div className="readiness-shell">
        <header className="topbar">
          <div className="topbar-brand">
            <div className="brand-mark small"><ShieldCheck size={20} /></div>
            <span>RainTech GRC</span>
          </div>
          <nav>
            <button className={view === "assessment" ? "active" : ""} onClick={() => changeView("assessment")}>Assessments</button>
            <button className={view === "overview" ? "active" : ""} onClick={() => changeView("overview")}>Overview</button>
            <button className={view === "profile" ? "active" : ""} onClick={() => changeView("profile")}>Profile</button>
            <button disabled>Actions</button>
          </nav>
          <div className="topbar-utility"><span className="account"><UserRound size={16} /> Johnathan</span></div>
        </header>
        <main className="readiness-main">
          <div className="readiness-project-line">
            <label>
              Client project
              <select value={projectId} onChange={(event) => changeProject(event.target.value)}>
                {projects.map((project) => (
                  <option key={project.id} value={project.id}>{project.clientName} · {project.name}</option>
                ))}
              </select>
            </label>
            <span>{selectedProject?.framework_version_id}</span>
          </div>
          {view === "profile" ? (
            <ProfilePanel projectId={projectId} onDirtyChange={setProfileDirty} />
          ) : (
            <ReadinessPanel
              readiness={readiness}
              hasAssessment={Boolean(assessment)}
              onChanged={reloadWorkspace}
            />
          )}
        </main>
        {creatingWorkspace && (
          <WorkspaceCreator
            clients={clients}
            onCancel={() => setCreatingWorkspace(false)}
            onCreated={(id) => {
              setCreatingWorkspace(false);
              onWorkspaceCreated(id);
            }}
          />
        )}
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-brand">
          <div className="brand-mark small"><ShieldCheck size={20} /></div>
          <span>RainTech GRC</span>
        </div>
        <nav>
          <button className={view === "assessment" ? "active" : ""} onClick={() => changeView("assessment")}>Assessments</button>
          <button className={view === "overview" ? "active" : ""} onClick={() => changeView("overview")}>Overview</button>
          <button className={view === "profile" ? "active" : ""} onClick={() => changeView("profile")}>Profile</button>
          <button disabled>Actions</button>
        </nav>
        <div className="topbar-utility">
          <span className={`save-state ${visibleSaveState}`} title={visibleSaveMessage} aria-live="polite">
            {visibleSaveState === "saving" && <LoaderCircle className="spin" size={14} />}
            {visibleSaveState === "saved" && <Cloud size={14} />}
            {(visibleSaveState === "error" || visibleSaveState === "failed") && <CircleAlert size={14} />}
            {visibleSaveState === "saving" ? "Saving" : visibleSaveState === "saved" ? "Saved" : "Save failed"}
          </span>
          <span className="account"><UserRound size={16} /> Johnathan</span>
        </div>
      </header>

      <aside className="rail">
        <div className="project-switcher">
          <p className="eyebrow">CLIENT PROJECT</p>
          <select value={projectId} onChange={(event) => changeProject(event.target.value)}>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>{project.clientName} · {project.name}</option>
            ))}
          </select>
          <span>{assessment.framework.name}</span>
          <button
            className="add-workspace"
            onClick={() => {
              if (confirmRoutineNavigation()) setCreatingWorkspace(true);
            }}
          >
            + Client / project
          </button>
        </div>
        <div className="rail-title">
          <div>
            <p className="eyebrow">GAP ANALYSIS</p>
            <h2>Work list</h2>
          </div>
          <span>{assessment.work_list.length}</span>
        </div>
        <div className="rail-filters">
          <label className="search-field"><Search size={15} /><input aria-label="Search records" placeholder="Find a citation…" value={search} onChange={(event) => setSearch(event.target.value)} /></label>
          <label className="area-filter"><ListFilter size={15} /><select aria-label="Filter work area" value={area} onChange={(event) => setArea(event.target.value)}>
            <option value="all">All work areas</option>
            <option value="security">Security</option>
            <option value="privacy">Privacy</option>
            <option value="breach">Breach notification</option>
          </select></label>
        </div>
        <div className="record-list">
          {filtered.map((record, index) => (
            <button
              key={record.record_id}
              className={record.record_id === recordId ? "active" : ""}
              onClick={() => changeRecord(record.record_id)}
            >
              <span className="record-number">{String(index + 1).padStart(3, "0")}</span>
              <span><strong>{record.title}</strong><small>{record.citation}</small></span>
              {record.designation && <em>{record.designation}</em>}
            </button>
          ))}
        </div>
      </aside>

      <main className={`assessment-main ${view !== "assessment" ? "workspace-hidden" : ""}`}>
        <div className="record-toolbar">
          <div>
            <span className={`readiness-state compact ${readiness.assessment_entry_allowed ? "ready" : "blocked"}`}>
              {readiness.state}
            </span>
            {returnRecordId ? (
              <button className="back-link" onClick={() => changeRecord(returnRecordId)}>
                <ArrowLeft size={15} /> Back to determination
              </button>
            ) : (
              <span className="position">{detail.position.current} of {detail.position.total}</span>
            )}
            <span className="position">
              {progress.resolved_determination_count} of{" "}
              {progress.determination_record_count} resolved
            </span>
          </div>
          <div className="previous-next">
            <button disabled={!detail.position.previous_record_id} onClick={() => detail.position.previous_record_id && changeRecord(detail.position.previous_record_id)}>
              <ArrowLeft size={16} /> Previous
            </button>
            <button disabled={!detail.position.next_record_id} onClick={() => detail.position.next_record_id && changeRecord(detail.position.next_record_id)}>
              Next <ArrowRight size={16} />
            </button>
          </div>
        </div>
        {readiness.assessment_entry_blocking_reasons.length > 0 && (
          <div className="assessment-readiness-warning">
            <strong>New assessment entry is blocked.</strong>
            {readiness.assessment_entry_blocking_reasons.map((reason) => (
              <span key={reason}>{reason}</span>
            ))}
          </div>
        )}

        {detail.parent && (
          <section className="parent-context">
            <div className="parent-icon"><FolderKanban size={18} /></div>
            <div>
              <p className="eyebrow">STANDARD CONTEXT</p>
              <h3>{detail.parent.title}</h3>
              <span>{detail.parent.citation}</span>
              <p>{detail.parent.regulation_text}</p>
              <details>
                <summary><ChevronDown size={14} /> Standard-level questions</summary>
                {detail.parent_prompts.length === 0 ? (
                  <p>No standard-level guidance questions are attached to this record.</p>
                ) : (
                  <ul className="parent-question-list">
                    {detail.parent_prompts.map((prompt) => <li key={prompt.id}>{prompt.text}</li>)}
                  </ul>
                )}
                <p>Open the standard work to record answers, notes, and evidence.</p>
              </details>
            </div>
            <div className="parent-actions">
              <StatusPill status={detail.parent.determination?.status ?? ""} derived />
              <button className="text-button" onClick={() => changeRecord(detail.parent!.record_id, recordId)}>
                Open standard notes & evidence
              </button>
            </div>
          </section>
        )}

        <section className={`record-brief ${detail.record.editable_determination ? "" : "rollup-brief"}`}>
          <div className="record-meta">
            <span>{detail.record.work_area}</span>
            <span>{detail.record.record_type.replaceAll("_", " ")}</span>
            {detail.record.designation && <span>{detail.record.designation}</span>}
          </div>
          <p className="citation">{detail.record.citation}</p>
          <h1>{detail.record.title}</h1>
          <blockquote>{detail.record.regulation_text}</blockquote>
        </section>

        <section className="prompt-section">
          <div className="content-heading">
            <div><p className="eyebrow">ASSESSOR GUIDANCE</p><h2>Questions to work through</h2></div>
            <span>{detail.prompts.length} question{detail.prompts.length === 1 ? "" : "s"}</span>
          </div>
          {detail.prompts.length === 0 ? (
            <div className="empty-panel">
              <BookOpen size={22} />
              <p>{detail.no_prompt_explanation}</p>
            </div>
          ) : (
            <div className="prompt-list">
              {detail.prompts.map((prompt) => (
                <PromptCard
                  key={`${assessment.id}:${prompt.id}`}
                  prompt={prompt}
                  assessment={assessment}
                  recordId={detail.record.record_id}
                  onRoutineSaveState={reportRoutineSave}
                  coordinateSave={coordinateRoutineSave}
                />
              ))}
            </div>
          )}
        </section>
      </main>

      <aside className={`working-record ${view !== "assessment" ? "workspace-hidden" : ""}`}>
        <div className="working-header">
          <div><p className="eyebrow">WORKING RECORD</p><h2>Assessment notes</h2></div>
          <ShieldCheck size={20} />
        </div>
        <DeterminationPanel
          key={`${assessment.id}:${detail.record.record_id}:determination`}
          assessmentId={assessment.id}
          statuses={assessment.framework.declarations.status_set}
          detail={detail}
          onRoutineSaveState={reportRoutineSave}
          coordinateSave={coordinateRoutineSave}
          onFinalSuccess={() => {
            void loadDetail();
            void refreshAssessmentProgress();
          }}
        />
        <RecordNotes
          key={`${assessment.id}:${detail.record.record_id}:notes`}
          assessmentId={assessment.id}
          recordId={detail.record.record_id}
          initialNote={detail.note}
          onRoutineSaveState={reportRoutineSave}
          coordinateSave={coordinateRoutineSave}
        />
        <EvidencePanel
          key={`${assessment.id}:${detail.record.record_id}:evidence`}
          assessment={assessment}
          detail={detail}
          artifacts={artifacts}
          onChanged={() => void loadDetail()}
          onArtifactsChanged={() => void loadArtifacts()}
          onSaveState={updateSaveState}
        />
      </aside>
      {view === "overview" && (
        <main className="overview-panel">
          <div className="overview-heading">
            <div>
              <p className="eyebrow">PROJECT OVERVIEW</p>
              <h1>{assessment.project.client_name} · {assessment.project.name}</h1>
              <p>{assessment.framework.name} is pinned to {assessment.framework.id}.</p>
            </div>
            <button className="small-button" onClick={() => changeView("assessment")}>
              Continue assessment <ArrowRight size={15} />
            </button>
          </div>
          <div className="overview-metrics">
            <article><strong>{assessment.framework.determination_record_count}</strong><span>determinations</span></article>
            <article><strong>{assessment.framework.record_count}</strong><span>cited records</span></article>
            <article><strong>{assessment.framework.prompt_count}</strong><span>assessor prompts</span></article>
          </div>
          <section className="overview-readiness">
            <div>
              <p className="eyebrow">PROFILE READINESS</p>
              <h2>{readiness.state}</h2>
            </div>
            {readiness.assessment_entry_blocking_reasons.length > 0 ? (
              <ul className="blocking-reasons">
                {readiness.assessment_entry_blocking_reasons.map((reason) => <li key={reason}>{reason}</li>)}
              </ul>
            ) : (
              <p className="readiness-ok">This readiness state permits assessment entry.</p>
            )}
            <button className="secondary-button" onClick={() => changeView("profile")}>Review profile gate</button>
          </section>
          <div className="overview-projects">
            <div className="section-title"><h2>Client projects</h2><span>{projects.length}</span></div>
            {projects.map((project) => (
              <button key={project.id} onClick={() => {
                if (changeProject(project.id)) setView("assessment");
              }}>
                <FolderKanban size={18} />
                <span><strong>{project.clientName}</strong><small>{project.name}</small></span>
                <ArrowRight size={16} />
              </button>
            ))}
          </div>
        </main>
      )}
      {view === "profile" && (
        <main className="overview-panel">
          <ProfilePanel projectId={projectId} onDirtyChange={setProfileDirty} />
          <ReadinessPanel
            readiness={readiness}
            hasAssessment
            onChanged={reloadWorkspace}
          />
        </main>
      )}
      {creatingWorkspace && (
        <WorkspaceCreator
          clients={clients}
          onCancel={() => setCreatingWorkspace(false)}
          onCreated={(id) => {
            setCreatingWorkspace(false);
            onWorkspaceCreated(id);
          }}
        />
      )}
    </div>
  );
}

export default function App() {
  const [clients, setClients] = useState<Client[] | null>(null);
  const [projectId, setProjectId] = useState("");
  const [error, setError] = useState("");

  async function loadClients(preferredProjectId = "") {
    try {
      const loaded = await request<Client[]>("/api/clients");
      setClients(loaded);
      const firstProject = loaded.flatMap((client) => client.projects)[0];
      setProjectId(preferredProjectId || firstProject?.id || "");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not open the local API.");
    }
  }

  useEffect(() => {
    void loadClients();
  }, []);

  if (error) {
    return (
      <main className="fatal-screen">
        <CircleAlert size={32} />
        <h1>The local workspace did not open</h1>
        <p>{error}</p>
        <p>Start the RainTech API, then refresh this page.</p>
      </main>
    );
  }
  if (clients === null) {
    return <div className="loading-screen"><LoaderCircle className="spin" /><span>Opening local workspace…</span></div>;
  }
  if (!projectId) {
    return <Setup onCreated={(id) => void loadClients(id)} />;
  }
  return (
    <Workspace
      clients={clients}
      projectId={projectId}
      onProjectChange={setProjectId}
      onWorkspaceCreated={(id) => void loadClients(id)}
    />
  );
}
