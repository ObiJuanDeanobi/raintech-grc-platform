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
import { SraPanel } from "./SraPanel";
import type {
  Artifact,
  Assessment,
  Client,
  CloseReadiness,
  CmmcScore,
  FrameworkDeclarations,
  FrameworkOption,
  RequirementFinding,
  SspView,
  GeneratedPackage,
  RevalidationItem,
  AssessmentReopening,
  RecordIndex,
  PackageReview,
  IssueReadiness,
  EvidenceMapping,
  Prompt,
  ProfileReadiness,
  RecordDetail,
  ReconciliationDisposition,
  ReconciliationRecord,
  CorrectiveActionValidation,
  Status,
} from "./types";

function ReadinessPanel({
  readiness,
  hasAssessment,
  onChanged,
  onStarted,
}: {
  readiness: ProfileReadiness;
  hasAssessment: boolean;
  onChanged: () => Promise<void>;
  onStarted?: () => void;
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
      onStarted?.();
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
          {nextState === "Profile complete" && (
            <>
              <label>
                Named reviewer
                <input value={reviewedBy} onChange={(event) => setReviewedBy(event.target.value)} />
              </label>
              <label>
                Review / approval evidence
                <textarea rows={2} value={approvalEvidence} onChange={(event) => setApprovalEvidence(event.target.value)} />
              </label>
            </>
          )}
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
        <button className="small-button" disabled={working} type="submit">
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

const GUIDANCE_LABELS: Record<string, string> = {
  evidence_type: "Evidence type",
  evidence_examples: "Evidence examples",
  assessment_considerations: "Assessment considerations",
  c3pao_guidance: "C3PAO guidance",
};

const DEFAULT_FRAMEWORK: FrameworkOption = {
  id: "hipaa-45cfr164-2026-07-01",
  name: "HIPAA 45 CFR Part 164",
};

function useFrameworks(): FrameworkOption[] {
  const [frameworks, setFrameworks] = useState<FrameworkOption[]>([DEFAULT_FRAMEWORK]);
  useEffect(() => {
    let live = true;
    request<FrameworkOption[]>("/api/frameworks")
      .then((options) => {
        if (live && Array.isArray(options) && options.length > 0) setFrameworks(options);
      })
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, []);
  return frameworks;
}

function FrameworkSelect({
  frameworks,
  value,
  onChange,
}: {
  frameworks: FrameworkOption[];
  value: string;
  onChange: (id: string) => void;
}) {
  return (
    <label>
      Framework
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {frameworks.map((framework) => (
          <option key={framework.id} value={framework.id}>{framework.name} · {framework.id}</option>
        ))}
      </select>
    </label>
  );
}

function Setup({ onCreated }: { onCreated: (projectId: string) => void }) {
  const [clientName, setClientName] = useState("");
  const [projectName, setProjectName] = useState("");
  const frameworks = useFrameworks();
  const [frameworkId, setFrameworkId] = useState(DEFAULT_FRAMEWORK.id);
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
        body: JSON.stringify({ name: projectName, framework_version_id: frameworkId }),
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
            placeholder="e.g. CMMC L2 2026"
            value={projectName}
            onChange={(event) => setProjectName(event.target.value)}
          />
        </label>
        <FrameworkSelect frameworks={frameworks} value={frameworkId} onChange={setFrameworkId} />
        <div className="pinned-framework">
          <BookOpen size={18} />
          <div>
            <strong>{frameworks.find((framework) => framework.id === frameworkId)?.name ?? frameworkId}</strong>
            <span>Version {frameworkId}</span>
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
  const [projectName, setProjectName] = useState("");
  const frameworks = useFrameworks();
  const [frameworkId, setFrameworkId] = useState(DEFAULT_FRAMEWORK.id);
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
        {
          method: "POST",
          body: JSON.stringify({ name: projectName, framework_version_id: frameworkId }),
        },
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
          <h2>Add a client project</h2>
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
          <input required placeholder="e.g. CMMC L2 2026" value={projectName} onChange={(event) => setProjectName(event.target.value)} />
        </label>
        <FrameworkSelect frameworks={frameworks} value={frameworkId} onChange={setFrameworkId} />
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
          <input
            aria-label={prompt.text}
            type="checkbox"
            checked={answer.trim().length > 0}
            disabled
            tabIndex={-1}
            readOnly
          />
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
          <div><p className="eyebrow">ROLLED UP</p><h3>Derived {detail.record.record_type === "requirement" ? "requirement" : "standard"} status</h3></div>
          <StatusPill status={detail.determination.status} derived />
        </div>
        <p className="muted">
          {detail.record.record_type === "requirement"
            ? "This requirement has no editable determination. Its status follows its assessment objectives; notes and evidence here remain independently recordable."
            : "This standard has no editable determination. Its status follows the child specifications; notes and evidence here remain independently recordable."}
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

function CmmcScorePanel({ projectId, assessmentId, refreshKey }: { projectId: string; assessmentId: string; refreshKey: unknown }) {
  const [score, setScore] = useState<CmmcScore | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    request<CmmcScore>(`/api/projects/${projectId}/assessments/${assessmentId}/cmmc-score`, { signal: controller.signal })
      .then(setScore)
      .catch(() => undefined);
    return () => controller.abort();
  }, [projectId, assessmentId, refreshKey]);
  if (!score) return null;
  return (
    <section className="cmmc-score" aria-label="Official CMMC score">
      <div>
        <p className="eyebrow">OFFICIAL SCORE · {score.authority}</p>
        <h3>
          {score.score} <small>of {score.maximum_score}{score.complete ? "" : " · provisional"}</small>
        </h3>
      </div>
      <dl>
        <div><dt>Not Met</dt><dd>{score.deductions.length}</dd></div>
        <div><dt>Unscored</dt><dd>{score.unscored.length}</dd></div>
        <div><dt>Follow-up</dt><dd>{score.follow_up.length}</dd></div>
        <div><dt>Conditional status</dt><dd>{score.conditional.eligible ? "Eligible" : "Not eligible"}</dd></div>
      </dl>
      {score.blockers.length > 0 && <ul className="cmmc-score-blockers">{score.blockers.map((blocker) => <li key={blocker}>{blocker}</li>)}</ul>}
    </section>
  );
}

function RequirementFindingPanel({
  projectId,
  assessmentId,
  requirementId,
  status,
  scoring,
  onChanged,
}: {
  projectId: string;
  assessmentId: string;
  requirementId: string;
  status: string;
  scoring: NonNullable<FrameworkDeclarations["scoring"]>["requirements"][string] | undefined;
  onChanged: () => void;
}) {
  const base = `/api/projects/${projectId}/assessments/${assessmentId}/requirements/${encodeURIComponent(requirementId)}`;
  const [finding, setFinding] = useState<RequirementFinding | null>(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [implementation, setImplementation] = useState<"partial" | "none">("partial");
  const [rationale, setRationale] = useState("");
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    request<RequirementFinding | null>(`${base}/finding`, { signal: controller.signal })
      .then(setFinding)
      .catch(() => undefined);
    return () => controller.abort();
  }, [base, status]);

  async function addPoam(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      setFinding(await request<RequirementFinding>(`${base}/poam`, { method: "POST", body: JSON.stringify({ title, description }) }));
      setTitle("");
      setDescription("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not add the POA&M item.");
    }
  }

  async function closePoam(actionId: string) {
    const rationale = window.prompt("How was the remediation verified?");
    if (!rationale?.trim()) return;
    setError("");
    try {
      setFinding(await request<RequirementFinding>(`${base}/poam/${actionId}/close`, { method: "POST", body: JSON.stringify({ rationale }) }));
      onChanged();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not close the POA&M item.");
    }
  }

  async function savePartial(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await request(`${base}/partial-implementation`, { method: "PUT", body: JSON.stringify({ implementation, rationale }) });
      onChanged();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save the implementation level.");
    }
  }

  const points = scoring?.rule === "fixed" ? `${scoring.points} point${scoring.points === 1 ? "" : "s"}` : scoring?.rule === "partial" ? "3 or 5 points" : "No point value";
  return (
    <section className="working-section requirement-finding" aria-label="Requirement finding">
      <div className="section-title">
        <div><p className="eyebrow">SCORING AND FINDING</p><h3>{points} if Not Met</h3></div>
        {finding && <span className="status-pill status-not-met">{finding.requirement_status === "Not Met" ? "Finding open" : "Finding history"}</span>}
      </div>
      {scoring && <p className="muted">{scoring.source}{scoring.note ? ` · ${scoring.note}` : ""}</p>}
      {status === "Not Met" && scoring?.rule === "partial" && (
        <form className="reconciliation-form" onSubmit={savePartial}>
          <label>Implementation<select value={implementation} onChange={(e) => setImplementation(e.target.value as "partial" | "none")}><option value="partial">Partial (3 points)</option><option value="none">None (5 points)</option></select></label>
          <label>Rationale <span className="required">required</span><textarea rows={2} value={rationale} onChange={(e) => setRationale(e.target.value)} required /></label>
          <button className="small-button" type="submit">Save implementation level</button>
        </form>
      )}
      {!finding && <p className="muted">{status === "Pending" ? "Pending objectives create follow-up work, never a finding." : "No finding. One is opened when this requirement derives Not Met."}</p>}
      {finding && (
        <>
          <strong>{finding.finding.title}</strong>
          <ul className="finding-objectives">
            {finding.failed_objectives.map((objective) => (
              <li key={objective.record_id}>
                <span>{objective.citation}</span> {objective.regulation_text}
                {objective.note && <small>Note: {objective.note}</small>}
                {objective.evidence.map((item) => <small key={item.name}>Evidence: {item.name} · {item.rationale}</small>)}
              </li>
            ))}
          </ul>
          <strong>POA&amp;M items</strong>
          {finding.poam_items.length === 0 ? <p className="muted">None yet.</p> : (
            <ul className="finding-objectives">{finding.poam_items.map((item) => (
              <li key={item.id}>
                {item.title} · {item.status}
                {item.status !== "Closed" && finding.requirement_status === "Met" && (
                  <button type="button" className="text-button" onClick={() => void closePoam(item.id)}>Close item</button>
                )}
              </li>
            ))}</ul>
          )}
          {finding.requirement_status === "Not Met" && (
            <form className="reconciliation-form" onSubmit={addPoam}>
              <label>POA&amp;M item title<input value={title} onChange={(e) => setTitle(e.target.value)} required /></label>
              <label>Description<textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} /></label>
              <button className="small-button" type="submit">Add POA&amp;M item</button>
            </form>
          )}
          <details className="reconciliation-history"><summary>Finding history</summary><ul>{finding.history.map((entry) => <li key={`${entry.event}:${entry.created_at}`}>{entry.event.replaceAll("_", " ")} · {entry.failed_objectives.join(", ") || "none"} · {new Date(entry.created_at).toLocaleString()}</li>)}</ul></details>
        </>
      )}
      {error && <p className="form-error"><CircleAlert size={16} /> {error}</p>}
    </section>
  );
}

function BackupControl() {
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

function SspPanel({ projectId, assessmentId, requirementId }: { projectId: string; assessmentId: string; requirementId: string | null }) {
  const [ssp, setSsp] = useState<SspView | null>(null);
  const [error, setError] = useState("");
  const base = `/api/projects/${projectId}`;
  const load = useCallback(() => {
    request<SspView | null>(`${base}/assessments/${assessmentId}/ssp`)
      .then((value) => setSsp(value && value.latest ? value : null))
      .catch(() => undefined);
  }, [base, assessmentId]);
  useEffect(load, [load]);

  async function act(path: string, init: RequestInit) {
    setError("");
    try {
      setSsp(await request<SspView>(path, init));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "SSP action failed.");
    }
  }

  const frozen = Boolean(ssp?.approval);
  return (
    <section className="cmmc-ssp" aria-label="System Security Plan">
      <div className="section-title">
        <div><p className="eyebrow">SYSTEM SECURITY PLAN · NIST SP 800-171 STRUCTURE</p>
          <h3>{ssp ? `Version ${ssp.latest.version_number}${frozen ? " · approved and frozen" : ""}` : "Not generated"}</h3></div>
        {ssp && <a className="text-button" href={`${base}/ssp/${ssp.id}/versions/${ssp.latest.version_number}/docx`}>Download DOCX copy</a>}
      </div>
      {!ssp && (
        <>
          <p className="muted">Generate once every requirement is Met or Not Met and the Profile is approved.</p>
          <button className="small-button" type="button" onClick={() => void act(`${base}/assessments/${assessmentId}/ssp`, { method: "POST" })}>Generate SSP</button>
        </>
      )}
      {ssp && (
        // Keyed so the fields start from the loaded version, never from an empty draft.
        <SspEditor
          key={`${ssp.latest.id}:${requirementId ?? ""}`}
          ssp={ssp}
          requirementId={requirementId}
          onSave={(body) => void act(`${base}/ssp/${ssp.id}`, { method: "PUT", body: JSON.stringify(body) })}
          onApprove={() => void act(`${base}/ssp/${ssp.id}/approve`, { method: "POST" })}
        />
      )}
      {error && <p className="form-error"><CircleAlert size={16} /> {error}</p>}
    </section>
  );
}

function SspEditor({
  ssp,
  requirementId,
  onSave,
  onApprove,
}: {
  ssp: SspView;
  requirementId: string | null;
  onSave: (body: Record<string, unknown>) => void;
  onApprove: () => void;
}) {
  const content = ssp.latest.content;
  const hasRequirement = Boolean(requirementId && content.requirements[requirementId]);
  const [draft, setDraft] = useState(() => ({
    system_description: content.system_description,
    environment_narrative: content.environment_narrative,
    implementation: hasRequirement ? content.requirements[requirementId!].implementation : "",
  }));
  const frozen = Boolean(ssp.approval);
  function save() {
    onSave({
      system_description: draft.system_description,
      environment_narrative: draft.environment_narrative,
      note: "Edited in the workspace.",
      ...(hasRequirement ? { requirements: { [requirementId!]: draft.implementation } } : {}),
    });
  }
  return (
    <>
      <label>System description<textarea rows={2} disabled={frozen} value={draft.system_description} onChange={(e) => setDraft({ ...draft, system_description: e.target.value })} /></label>
      <label>Environment narrative<textarea rows={2} disabled={frozen} value={draft.environment_narrative} onChange={(e) => setDraft({ ...draft, environment_narrative: e.target.value })} /></label>
      {hasRequirement && (
        <label>Implementation statement for {requirementId}<textarea rows={3} disabled={frozen} value={draft.implementation} onChange={(e) => setDraft({ ...draft, implementation: e.target.value })} /></label>
      )}
      {!frozen && (
        <div className="modal-actions">
          <button className="small-button" type="button" onClick={save}>Save new version</button>
          <button className="small-button" type="button" disabled={ssp.missing_for_approval.length > 0} onClick={onApprove}>Approve and freeze</button>
        </div>
      )}
      {!frozen && ssp.missing_for_approval.length > 0 && <p className="muted">{ssp.missing_for_approval.length} section(s) still need text before approval.</p>}
    </>
  );
}

function NotMetReconciliation({ projectId, assessmentId, recordId, status }: { projectId: string; assessmentId: string; recordId: string; status: string }) {
  const [data, setData] = useState<ReconciliationRecord | null>(null);
  const [choice, setChoice] = useState<ReconciliationDisposition>("create");
  const [title, setTitle] = useState("");
  const [findingDescription, setFindingDescription] = useState("");
  const [actionTitle, setActionTitle] = useState("");
  const [actionDescription, setActionDescription] = useState("");
  const [rationale, setRationale] = useState("");
  const [existingId, setExistingId] = useState("");
  const [actionId, setActionId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [validation, setValidation] = useState<CorrectiveActionValidation | null>(null);
  const [validationOutcome, setValidationOutcome] = useState<"Validated" | "Failed">("Validated");
  const [validationNotes, setValidationNotes] = useState("");
  const [validationBusy, setValidationBusy] = useState(false);
  const correctiveAction = data?.links?.find((link) => link.type === "corrective_action") ?? (data?.corrective_action_id ? { id: data.corrective_action_id } : undefined);
  const actionIdForValidation = correctiveAction?.id ?? "";
  useEffect(() => {
    const controller = new AbortController();
    setData(null); setValidation(null); setError(""); setTitle(""); setFindingDescription(""); setActionTitle(""); setActionDescription(""); setRationale(""); setExistingId(""); setActionId(""); setValidationNotes("");
    if (status !== "Not Met" && status !== "Met") return () => controller.abort();
    void request<ReconciliationRecord | null>(`/api/projects/${projectId}/assessments/${assessmentId}/records/${encodeURIComponent(recordId)}/reconciliation`, { signal: controller.signal })
      .then((next) => { if (!controller.signal.aborted) { setData(next); setTitle(next?.prefill?.finding_title ?? `Not Met: ${recordId}`); setActionTitle(next?.prefill?.action_title ?? `Remediate: ${recordId}`); } })
      .catch((e) => { if (!controller.signal.aborted && (e as ApiError)?.status !== 404) setError(e instanceof Error ? e.message : "Could not load reconciliation."); });
    return () => controller.abort();
  }, [projectId, assessmentId, recordId, status]);
  useEffect(() => {
    const controller = new AbortController();
    if ((status !== "Not Met" && status !== "Met") || !actionIdForValidation) return () => controller.abort();
    void request<CorrectiveActionValidation>(`/api/projects/${projectId}/assessments/${assessmentId}/records/${encodeURIComponent(recordId)}/corrective-actions/${encodeURIComponent(actionIdForValidation)}/validation`, { signal: controller.signal })
      .then((next) => { if (!controller.signal.aborted) setValidation(next); })
      .catch((e) => { if (!controller.signal.aborted && (e as ApiError)?.status !== 404) setError(e instanceof Error ? e.message : "Could not load validation context."); });
    return () => controller.abort();
  }, [projectId, assessmentId, recordId, status, actionIdForValidation]);
  if (status === "Pending") return <section className="working-section reconciliation"><p className="eyebrow">RECONCILIATION</p><p className="muted">Pending does not create reconciliation work. Resolve the determination first.</p></section>;
  if (status !== "Not Met" && !validation) return null;
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const payload = choice === "create" ? { outcome: choice, title, description: findingDescription, action_title: actionTitle, action_description: actionDescription, rationale } : choice === "link_existing" ? { outcome: choice, finding_id: existingId, corrective_action_id: actionId, rationale } : { outcome: choice, rationale };
      const next = await request<ReconciliationRecord>(`/api/projects/${projectId}/assessments/${assessmentId}/records/${encodeURIComponent(recordId)}/reconciliation`, { method: "PUT", body: JSON.stringify(payload) });
      setData(next); setRationale("");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not save reconciliation."); } finally { setBusy(false); }
  };
  const saveActionState = async () => {
    if (!actionIdForValidation) return;
    setBusy(true); setError("");
    try {
      const next = await request<{ id: string; status: string }>(`/api/projects/${projectId}/corrective-actions/${encodeURIComponent(actionIdForValidation)}`, { method: "PUT", body: JSON.stringify({ actor_id: "johnathan", state: "Ready for Validation" }) });
      setData((current) => current ? { ...current, corrective_action_id: next.id, links: current.links.map((link) => link.id === next.id ? { ...link, status: next.status } : link) } : current);
      setValidation((current) => current ? { ...current, corrective_action: { ...current.corrective_action, status: "Ready for Validation", validation_state: "Ready" } } : current);
    } catch (e) { setError(e instanceof Error ? e.message : "Could not update corrective action."); } finally { setBusy(false); }
  };
  const submitValidation = async (event: FormEvent) => {
    event.preventDefault();
    if (!validationNotes.trim()) { setError("Validation notes are required."); return; }
    setValidationBusy(true); setError("");
    try {
      await request(`/api/projects/${projectId}/assessments/${assessmentId}/records/${encodeURIComponent(recordId)}/corrective-actions/${encodeURIComponent(actionIdForValidation)}/validation`, { method: "POST", body: JSON.stringify({ actor_id: "johnathan", outcome: validationOutcome, notes: validationNotes }) });
      const refreshed = await request<CorrectiveActionValidation>(`/api/projects/${projectId}/assessments/${assessmentId}/records/${encodeURIComponent(recordId)}/corrective-actions/${encodeURIComponent(actionIdForValidation)}/validation`);
      setValidation(refreshed);
      setData((current) => current ? { ...current, links: current.links.map((link) => link.id === refreshed.corrective_action.id ? { ...link, status: refreshed.corrective_action.status, validation_state: refreshed.corrective_action.validation_state } : link) } : current);
      setValidationNotes("");
    } catch (e) { setError(e instanceof Error ? e.message : "Could not save validation."); } finally { setValidationBusy(false); }
  };
  return <section className="working-section reconciliation"><div className="section-title"><div><p className="eyebrow">RECONCILIATION</p><h3>{status === "Not Met" ? "Not Met corrective work" : "Corrective action validation"}</h3></div><span className="status-pill status-not-met">{data?.outcome ?? "Resolved"}</span></div>
    {error && <p className="error-copy">{error}</p>}
    {data?.prefill && <div className="reconciliation-links"><strong>Prefilled context</strong>{Object.entries(data.prefill).filter(([, value]) => value).map(([key, value]) => <div key={key}><span>{key.replaceAll("_", " ")}</span><small>{value}</small></div>)}</div>}
    {data?.links?.length ? <div className="reconciliation-links"><strong>Current links</strong>{data.links.map((link) => <div key={link.id}><span>{link.title ?? link.finding_id}</span><small>{link.status}</small></div>)}</div> : <p className="muted">No finding or corrective action is linked yet.</p>}
    {status === "Not Met" && actionIdForValidation && <div className="reconciliation-links"><strong>Corrective action readiness</strong><button className="small-button" type="button" disabled={busy || validation?.corrective_action.status === "Ready for Validation"} onClick={() => void saveActionState()}>{validation?.corrective_action.status === "Ready for Validation" ? "Ready for Validation" : "Mark Ready for Validation"}</button></div>}
    {status === "Not Met" && <form className="reconciliation-form" onSubmit={submit}><label>Disposition<select value={choice} onChange={(e) => setChoice(e.target.value as ReconciliationDisposition)}><option value="create">Create prefilled finding</option><option value="link_existing">Link existing finding</option><option value="not_needed">Not needed</option></select></label>{choice === "create" && <><label>Finding title<input value={title} onChange={(e) => setTitle(e.target.value)} required /></label><label>Finding description<textarea rows={2} value={findingDescription} onChange={(e) => setFindingDescription(e.target.value)} /></label><label>Corrective action title<input value={actionTitle} onChange={(e) => setActionTitle(e.target.value)} required /></label><label>Corrective action description<textarea rows={2} value={actionDescription} onChange={(e) => setActionDescription(e.target.value)} /></label></>}{choice === "link_existing" && <><label>Finding ID<input value={existingId} onChange={(e) => setExistingId(e.target.value)} required /></label><label>Corrective action ID<input value={actionId} onChange={(e) => setActionId(e.target.value)} required /></label></>}<label>{choice === "not_needed" ? "Rationale (required)" : "Rationale"}<textarea rows={2} value={rationale} onChange={(e) => setRationale(e.target.value)} required={choice === "not_needed"} /></label><button className="small-button" disabled={busy} type="submit">{busy ? "Saving…" : "Save reconciliation"}</button></form>}
    {validation && <div className="reconciliation-links"><strong>Validation context</strong><div><span>Finding</span><small>{validation.finding.title} · {validation.finding.status}</small></div><div><span>Corrective action</span><small>{validation.corrective_action.title} · {validation.corrective_action.status}</small></div><div><span>Determination</span><small>{validation.determination?.status ?? "Unavailable"}</small></div><div><span>Evidence / interview</span><small>{validation.determination?.interview_observation || "See validation history for mapped evidence"}</small></div>{status === "Not Met" && <form className="reconciliation-form" onSubmit={submitValidation}><label>Outcome<select value={validationOutcome} onChange={(e) => setValidationOutcome(e.target.value as "Validated" | "Failed")}><option value="Validated">Validated</option><option value="Failed">Failed</option></select></label><label>Validation notes <span className="required">required</span><textarea rows={3} value={validationNotes} onChange={(e) => setValidationNotes(e.target.value)} required /></label><button className="small-button" disabled={validationBusy || validation.corrective_action.status !== "Ready for Validation"} type="submit">{validationBusy ? "Saving…" : "Record validation"}</button></form>}{validation.events.length > 0 && <details className="reconciliation-history"><summary>Validation history</summary><ul>{validation.events.map((event) => <li key={event.id}><strong>{event.outcome}</strong> from {event.prior_determination} · {event.notes} · {new Date(event.created_at).toLocaleDateString()} · {event.evidence_context.interview_observation || `${event.evidence_context.presented.length} mapped evidence item(s)`}</li>)}</ul></details>}</div>}
    {!!data?.history?.length && <details className="reconciliation-history"><summary>History</summary><ul>{data.history.map((item) => <li key={item.id}>{item.outcome} · {new Date(item.changed_at).toLocaleDateString()}</li>)}</ul></details>}
  </section>;
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
  const targetRef = useRef({ assessmentId: assessment.id, projectId: assessment.project.id, recordId: detail.record.record_id });
  const mountedRef = useRef(true);
  targetRef.current = { assessmentId: assessment.id, projectId: assessment.project.id, recordId: detail.record.record_id };
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  function isCurrent(target: typeof targetRef.current, includeRecord = false) {
    return mountedRef.current && targetRef.current.projectId === target.projectId
      && targetRef.current.assessmentId === target.assessmentId
      && (!includeRecord || targetRef.current.recordId === target.recordId);
  }

  async function upload(file: File) {
    const target = targetRef.current;
    setUploading(true);
    onSaveState("saving");
    const data = new FormData();
    data.append("file", file);
    try {
      const artifact = await request<Artifact>(`/api/projects/${assessment.project.id}/evidence`, {
        method: "POST",
        body: data,
      });
      if (!isCurrent(target)) return;
      setArtifactId(artifact.id);
      onArtifactsChanged();
      onSaveState("saved");
    } catch (caught) {
      if (isCurrent(target)) onSaveState("error", caught instanceof Error ? caught.message : undefined);
    } finally {
      if (isCurrent(target)) setUploading(false);
    }
  }

  async function mapEvidence(event: FormEvent) {
    event.preventDefault();
    const target = targetRef.current;
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
      if (!isCurrent(target, true)) return;
      setRationale("");
      onSaveState("saved");
      onChanged();
      onArtifactsChanged();
    } catch (caught) {
      if (isCurrent(target, true)) onSaveState("error", caught instanceof Error ? caught.message : undefined);
    }
  }

  async function evidenceAction(path: string, init: RequestInit, refreshArtifacts = true) {
    const target = targetRef.current;
    onSaveState("saving");
    try {
      await request(path, init);
      if (!isCurrent(target)) return;
      onSaveState("saved");
      onChanged();
      if (refreshArtifacts) onArtifactsChanged();
      setBinTick((tick) => tick + 1);
    } catch (caught) {
      if (isCurrent(target)) onSaveState("error", caught instanceof Error ? caught.message : undefined);
    }
  }

  function replaceFile(mapping: EvidenceMapping, file: File) {
    const data = new FormData();
    data.append("file", file);
    void evidenceAction(`/api/projects/${assessment.project.id}/evidence/${mapping.artifact_id}/versions`, { method: "POST", body: data });
  }

  const [binned, setBinned] = useState<Artifact[]>([]);
  const [binTick, setBinTick] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    request<Artifact[]>(`/api/projects/${assessment.project.id}/evidence?binned=true`, { signal: controller.signal })
      .then((rows) => setBinned(Array.isArray(rows) ? rows : []))
      .catch(() => undefined);
    return () => controller.abort();
  }, [assessment.project.id, binTick]);
  const evidenceBase = `/api/projects/${assessment.project.id}/evidence`;
  const today = new Date().toISOString().slice(0, 10);

  async function unmap(mapping: EvidenceMapping) {
    if (!window.confirm(`Remove the mapping to “${mapping.name}”? The evidence file is retained.`)) return;
    const target = targetRef.current;
    onSaveState("saving");
    try {
      await request(
        `/api/projects/${assessment.project.id}/assessments/${assessment.id}/evidence-mappings/${mapping.mapping_id}`,
        { method: "DELETE" },
      );
      if (!isCurrent(target, true)) return;
      onSaveState("saved");
      onChanged();
      onArtifactsChanged();
    } catch (caught) {
      if (isCurrent(target, true)) onSaveState("error", caught instanceof Error ? caught.message : undefined);
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
              {mapping.latest_version_number && mapping.latest_version_number > mapping.version_number && (
                <span className="evidence-newer">
                  Version {mapping.latest_version_number} is available.{" "}
                  <button type="button" className="text-button" onClick={() => void evidenceAction(`/api/projects/${assessment.project.id}/assessments/${assessment.id}/evidence-mappings/${mapping.mapping_id}/version`, { method: "PUT" }, false)}>Use latest version</button>
                </span>
              )}
              {mapping.review_date && mapping.review_date < today && <span className="evidence-overdue">Review overdue since {mapping.review_date}</span>}
              <span>SHA-256: {mapping.sha256}</span>
              <label className="text-button evidence-replace">Replace file<input type="file" aria-label={`Replace ${mapping.name}`} onChange={(event) => event.target.files?.[0] && replaceFile(mapping, event.target.files[0])} /></label>
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
      <details className="evidence-library">
        <summary>Evidence library and recycle bin</summary>
        <ul>
          {artifacts.filter((artifact) => artifact.shared_record_count === 0).map((artifact) => (
            <li key={artifact.id}>
              {artifact.name} · v{artifact.version_number}{artifact.overdue ? " · review overdue" : ""}
              <button type="button" className="text-button" onClick={() => void evidenceAction(`${evidenceBase}/${artifact.id}/recycle`, { method: "POST" })}>Move to bin</button>
            </li>
          ))}
        </ul>
        <p className="muted">Mapped evidence must be detached before it can be binned.</p>
        <strong>Recycle bin</strong>
        {binned.length === 0 ? <p className="muted">Empty.</p> : (
          <ul aria-label="Recycle bin">
            {binned.map((artifact) => (
              <li key={artifact.id}>
                {artifact.name}{artifact.purged_at ? " · file purged" : ""}
                {!artifact.purged_at && (
                  <>
                    <button type="button" className="text-button" onClick={() => void evidenceAction(`${evidenceBase}/${artifact.id}/restore`, { method: "POST" })}>Restore</button>
                    <button type="button" className="text-button" onClick={() => {
                      if (window.confirm(`Permanently delete the stored file for “${artifact.name}”? Its hash history is kept.`)) {
                        void evidenceAction(`${evidenceBase}/${artifact.id}`, { method: "DELETE" });
                      }
                    }}>Delete permanently</button>
                  </>
                )}
              </li>
            ))}
          </ul>
        )}
      </details>
    </section>
  );
}

function CloseReadinessPanel({ projectId, assessmentId, onNavigate }: { projectId: string; assessmentId: string; onNavigate: (link: Record<string, unknown>) => void }) {
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

function PackageGenerationPanel({ projectId, assessmentId, records, onReopened }: { projectId: string; assessmentId: string; records: RecordIndex[]; onReopened: () => Promise<void> }) {
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

function RevalidationPanel({ projectId, assessmentId, reopening, items, currentRecordId, onChanged, onOpenRecord }: { projectId: string; assessmentId: string; reopening: AssessmentReopening; items: RevalidationItem[]; currentRecordId: string; onChanged: () => void; onOpenRecord: (recordId: string) => void }) {
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

export function Workspace({
  clients,
  projectId,
  onProjectChange,
  onWorkspaceCreated,
  initialView = "assessment",
}: {
  clients: Client[];
  projectId: string;
  onProjectChange: (id: string) => void;
  onWorkspaceCreated: (id: string) => void;
  initialView?: "assessment" | "profile";
}) {
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [loadedProjectId, setLoadedProjectId] = useState("");
  const [revalidationTick, setRevalidationTick] = useState(0);
  const [scoreTick, setScoreTick] = useState(0);
  const [readiness, setReadiness] = useState<ProfileReadiness | null>(null);
  const [progress, setProgress] = useState<Assessment["progress"] | null>(null);
  const [recordId, setRecordId] = useState("");
  const [returnRecordId, setReturnRecordId] = useState("");
  const [detail, setDetail] = useState<RecordDetail | null>(null);
  const detailLoadedTargetRef = useRef({ assessmentId: "", recordId: "" });
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [search, setSearch] = useState("");
  const [area, setArea] = useState("all");
  const [saveState, setSaveState] = useState<"saved" | "saving" | "error">("saved");
  const [saveMessage, setSaveMessage] = useState("");
  const [routineSaves, setRoutineSaves] = useState<Map<string, RoutineSaveState>>(new Map());
  const [loading, setLoading] = useState(true);
  const [creatingWorkspace, setCreatingWorkspace] = useState(false);
  const [profileDirty, setProfileDirty] = useState(false);
  const [view, setView] = useState<"assessment" | "overview" | "profile" | "sra">(initialView);
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
    setLoadedProjectId(targetProjectId);
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
    setLoadedProjectId(targetProjectId);
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
    if (assessmentRequestSequenceRef.current !== requestSequence || projectTargetRef.current !== targetProjectId) return;
    if (next.id !== targetAssessmentId) {
      setDetail(null);
      detailLoadedTargetRef.current = { assessmentId: "", recordId: "" };
      setRecordId(next.work_list[0]?.record_id || "");
      setReturnRecordId("");
      setRoutineSaves(new Map());
      setSaveState("saved");
      setAssessment(next);
      setProgress(next.progress);
    } else {
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
      detailLoadedTargetRef.current = target;
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
    setLoadedProjectId("");
    setReadiness(null);
    setProgress(null);
    setRecordId("");
    setReturnRecordId("");
    setLoading(true);
    setDetail(null);
    detailLoadedTargetRef.current = { assessmentId: "", recordId: "" };
    setArtifacts([]);
    setSaveState("saved");
    setSaveMessage("");
    setRoutineSaves(new Map());
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

  const changeView = useCallback((nextView: "assessment" | "overview" | "profile" | "sra") => {
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

  // CMMC presents each requirement with its objectives; HIPAA one record at a time.
  const objectiveMode = assessment?.framework?.declarations?.presentation_mode === "requirement_with_objectives";
  const activeRequirementId = objectiveMode
    ? assessment?.work_list?.find((record) => record.record_id === recordId)?.parent_id ?? recordId
    : "";

  const filtered = useMemo(() => {
    if (!assessment) return [];
    const term = search.toLowerCase();
    return assessment.work_list.filter(
      (record) =>
        (!objectiveMode || !record.parent_id || record.parent_id === activeRequirementId) &&
        (area === "all" || record.work_area === area) &&
        (!term ||
          record.title.toLowerCase().includes(term) ||
          record.citation.toLowerCase().includes(term)),
    );
  }, [assessment, search, area, objectiveMode, activeRequirementId]);

  const workAreas = useMemo(
    () => (assessment ? [...new Set(assessment.work_list.map((record) => record.work_area))] : []),
    [assessment],
  );

  const projects = clients.flatMap((client) =>
    client.projects.map((project) => ({ ...project, clientName: client.name })),
  );

  const selectedProject = projects.find((project) => project.id === projectId);

  const assessmentMatchesSelectedProject = assessment?.project.id === projectId && loadedProjectId === projectId;
  if (loading || !readiness || loadedProjectId !== projectId || (assessment && !assessmentMatchesSelectedProject)) {
    return <div className="loading-screen"><LoaderCircle className="spin" /><span>Opening assessment workspace…</span></div>;
  }

  if (!assessment || !progress || !detail || !assessmentMatchesSelectedProject || detailLoadedTargetRef.current.assessmentId !== assessment.id || detailLoadedTargetRef.current.recordId !== recordId) {
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
            <button
              className="add-workspace"
              onClick={() => {
                if (confirmRoutineNavigation()) setCreatingWorkspace(true);
              }}
            >
              + Client / project
            </button>
          </div>
          {view === "profile" ? (
            <>
              <ProfilePanel key={projectId} projectId={projectId} onDirtyChange={setProfileDirty} />
              <ReadinessPanel
                readiness={readiness}
                hasAssessment={Boolean(assessment)}
                onChanged={reloadWorkspace}
                onStarted={() => setView("assessment")}
              />
            </>
          ) : view === "sra" ? (
            <SraPanel key={`${projectId}:${assessment?.id ?? "none"}`} projectId={projectId} assessmentId={assessment?.id} onDirtyChange={setProfileDirty} />
          ) : (
            <ReadinessPanel
              readiness={readiness}
              hasAssessment={Boolean(assessment)}
              onChanged={reloadWorkspace}
              onStarted={() => setView("assessment")}
            />
          )}
        </main>
        {creatingWorkspace && (
          <WorkspaceCreator
            clients={clients}
            onCancel={() => setCreatingWorkspace(false)}
            onCreated={(id) => {
              setCreatingWorkspace(false);
              setView("profile");
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
          {assessment.framework.declarations.sra && (
            <button className={view === "sra" ? "active" : ""} onClick={() => changeView("sra")}>{assessment.framework.declarations.sra.work_area}</button>
          )}
          <button disabled>Actions</button>
        </nav>
        <div className="topbar-utility">
          <span className={`save-state ${visibleSaveState}`} title={visibleSaveMessage} aria-live="polite">
            {visibleSaveState === "saving" && <LoaderCircle className="spin" size={14} />}
            {visibleSaveState === "saved" && <Cloud size={14} />}
            {(visibleSaveState === "error" || visibleSaveState === "failed") && <CircleAlert size={14} />}
            {visibleSaveState === "saving" ? "Saving" : visibleSaveState === "saved" ? "Saved" : "Save failed"}
          </span>
          <BackupControl />
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
            {objectiveMode ? (
              workAreas.map((workArea) => <option key={workArea} value={workArea}>{workArea}</option>)
            ) : (
              <>
                <option value="security">Security</option>
                <option value="privacy">Privacy</option>
                <option value="breach">Breach notification</option>
              </>
            )}
          </select></label>
        </div>
        <div className="record-list">
          {filtered.map((record, index) => (
            <button
              key={record.record_id}
              className={`${record.record_id === recordId ? "active" : ""} ${objectiveMode && record.parent_id ? "nested-objective" : ""}`}
              onClick={() => changeRecord(record.record_id)}
            >
              <span className="record-number">{String(index + 1).padStart(3, "0")}</span>
              <span><strong>{record.title}</strong><small>{record.citation}</small></span>
              {record.designation && <em>{record.designation}</em>}
            </button>
          ))}
        </div>
      </aside>

      {view === "sra" && <SraPanel key={`${projectId}:${assessment.id}`} projectId={projectId} assessmentId={assessment.id} onDirtyChange={setProfileDirty} />}
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
        {assessment.reopening && <RevalidationPanel key={`revalidation:${assessment.id}`} projectId={assessment.project.id} assessmentId={assessment.id} reopening={assessment.reopening} items={assessment.revalidation_items ?? []} currentRecordId={recordId} onChanged={() => setRevalidationTick((tick) => tick + 1)} onOpenRecord={(next) => changeRecord(next)} />}
        {assessment.framework.declarations.close_readiness && <CloseReadinessPanel key={`close:${assessment.project.id}:${assessment.id}:${revalidationTick}`} projectId={assessment.project.id} assessmentId={assessment.id} onNavigate={(link) => {
          const target = String(link.target ?? link.view ?? "");
          if (target === "profile" || target === "sra" || target === "overview") changeView(target as "profile" | "sra" | "overview");
          else if (link.record_id || link.recordId) changeRecord(String(link.record_id ?? link.recordId));
        }} />}
        {assessment.framework.declarations.close_readiness && <PackageGenerationPanel key={`package:${assessment.project.id}:${assessment.id}:${revalidationTick}`} projectId={assessment.project.id} assessmentId={assessment.id} records={assessment.record_index} onReopened={refreshAssessmentProgress} />}

        {detail.parent && (
          <section className="parent-context">
            <div className="parent-icon"><FolderKanban size={18} /></div>
            <div>
              <p className="eyebrow">{objectiveMode ? "REQUIREMENT CONTEXT" : "STANDARD CONTEXT"}</p>
              <h3>{detail.parent.title}</h3>
              <span>{detail.parent.citation}</span>
              <p>{detail.parent.regulation_text}</p>
              <details>
                <summary><ChevronDown size={14} /> {objectiveMode ? "Requirement-level questions" : "Standard-level questions"}</summary>
                {detail.parent_prompts.length === 0 ? (
                  <p>No {objectiveMode ? "requirement-level" : "standard-level"} guidance questions are attached to this record.</p>
                ) : (
                  <ul className="parent-question-list">
                    {detail.parent_prompts.map((prompt) => <li key={prompt.id}>{prompt.text}</li>)}
                  </ul>
                )}
                <p>Open the {objectiveMode ? "requirement" : "standard"} work to record answers, notes, and evidence.</p>
              </details>
            </div>
            <div className="parent-actions">
              <StatusPill status={detail.parent.determination?.status ?? ""} derived />
              <button className="text-button" onClick={() => changeRecord(detail.parent!.record_id, recordId)}>
                {objectiveMode ? "Open requirement and all objectives" : "Open standard notes & evidence"}
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

        {detail.practitioner_guidance && (
          <section className="practitioner-guidance" aria-label="RainTech practitioner guidance">
            <p className="eyebrow">RAINTECH PRACTITIONER GUIDANCE · NOT DOD OR NIST TEXT</p>
            <dl>
              {Object.entries(detail.practitioner_guidance.fields)
                .filter(([field, value]) => value && field !== "worksheet_level")
                .map(([field, value]) => (
                  <div key={field}>
                    <dt>{GUIDANCE_LABELS[field] ?? field.replaceAll("_", " ")}</dt>
                    <dd>{value}</dd>
                  </div>
                ))}
            </dl>
            <small>{detail.practitioner_guidance.provenance}</small>
          </section>
        )}

        {objectiveMode && assessment.framework.declarations.scoring && (
          <SspPanel
            key={`ssp:${assessment.id}`}
            projectId={assessment.project.id}
            assessmentId={assessment.id}
            requirementId={detail.record.editable_determination ? null : detail.record.record_id}
          />
        )}
        {objectiveMode && assessment.framework.declarations.scoring && (
          <CmmcScorePanel projectId={assessment.project.id} assessmentId={assessment.id} refreshKey={`${scoreTick}:${progress.resolved_determination_count}:${detail.record.record_id}:${detail.determination.status}`} />
        )}

        {objectiveMode && detail.children.length > 0 && (
          <section className="objective-panel" aria-label="Assessment objectives">
            <div className="section-title">
              <div>
                <p className="eyebrow">ASSESSMENT OBJECTIVES</p>
                <h3>Determinations are recorded per objective</h3>
              </div>
              <StatusPill status={detail.determination.status} derived />
            </div>
            <p className="objective-rule">
              Requirement status is derived: any Not Met → Not Met; otherwise any Pending → Pending; all Met → Met; otherwise blank.
            </p>
            <ul>
              {detail.children.map((objective) => (
                <li key={objective.record_id}>
                  <button className="objective-row" onClick={() => changeRecord(objective.record_id)}>
                    <span className="citation">{objective.citation}</span>
                    <span>{objective.regulation_text}</span>
                    <StatusPill status={objective.determination?.status ?? ""} />
                  </button>
                </li>
              ))}
            </ul>
          </section>
        )}

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
        {objectiveMode && !detail.record.editable_determination && (
          <RequirementFindingPanel
            key={`${assessment.id}:${detail.record.record_id}:finding`}
            projectId={assessment.project.id}
            assessmentId={assessment.id}
            requirementId={detail.record.record_id}
            status={detail.determination.status}
            scoring={assessment.framework.declarations.scoring?.requirements[detail.record.record_id]}
            onChanged={() => setScoreTick((tick) => tick + 1)}
          />
        )}
        {/* Objective-level reconciliation is HIPAA's; CMMC findings are requirement-level. */}
        {!objectiveMode && (
          <NotMetReconciliation
            key={`${assessment.id}:${detail.record.record_id}:reconciliation`}
            assessmentId={assessment.id}
            projectId={assessment.project.id}
            recordId={detail.record.record_id}
            status={detail.determination.status}
          />
        )}
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
          <ProfilePanel key={projectId} projectId={projectId} onDirtyChange={setProfileDirty} />
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
            setView("profile");
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
  const [openedFromSetup, setOpenedFromSetup] = useState(false);
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
    return (
      <Setup
        onCreated={(id) => {
          setOpenedFromSetup(true);
          void loadClients(id);
        }}
      />
    );
  }
  return (
    <Workspace
      clients={clients}
      projectId={projectId}
      onProjectChange={setProjectId}
      onWorkspaceCreated={(id) => void loadClients(id)}
      initialView={openedFromSetup ? "profile" : "assessment"}
    />
  );
}
