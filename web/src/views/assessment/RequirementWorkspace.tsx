import { ArrowLeft, ArrowRight, ChevronDown, ChevronRight, CircleAlert, FileCheck2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { request } from "../../api";
import { RoutineSaveStatus } from "../../components/RoutineSaveStatus";
import { StatusPill } from "../../components/StatusPill";
import { RoutineRecordSaveCoordinator, RoutineSaveReporter, useRoutineAutosave } from "../../components/routineSave";
import { GUIDANCE_LABELS } from "../../lib/guidance";
import { NOTE_METHODS, methodLabel, parseObjectiveNotes, serializeObjectiveNotes } from "../../lib/objectiveNotes";
import { isDecided } from "../../lib/requirements";
import type {
  Artifact,
  Assessment,
  CmmcScore,
  Determination,
  RecordDetail,
  RecordState,
  RecordSummary,
  SspView,
  Status,
} from "../../types";
import { EvidencePanel, RequirementFindingPanel, SspPanel } from "./RecordPanels";

const EMPTY_DETERMINATION: Determination = {
  status: "",
  derived: false,
  na_rationale: "",
  addressable_disposition: null,
  disposition_reason: "",
  interview_observation: "",
};

const STATUS_KEYS: Record<string, Status> = { m: "Met", n: "Not Met", p: "Pending" };

type ObjectiveHandle = { setStatus: (status: Status) => void };

function isTyping(target: EventTarget | null): boolean {
  if (!(target instanceof Element)) return false;
  return Boolean(target.closest("input, textarea, select, [contenteditable='true'], [contenteditable='']"));
}

function statusSlug(status: Status): string {
  return status.toLowerCase().replaceAll(" ", "-");
}

/** One compact line in place of the full score panel (#140). */
export function CmmcScoreLine({ projectId, assessmentId, refreshKey }: { projectId: string; assessmentId: string; refreshKey: unknown }) {
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
    <section className="cmmc-score-line" aria-label="Official CMMC score" title={score.blockers.join(" ")}>
      <span className="eyebrow">SCORE</span>
      <strong>{score.score}</strong>
      <small>of {score.maximum_score}{score.complete ? "" : " · provisional"}</small>
      <span>Not Met {score.deductions.length}</span>
      <span>Unscored {score.unscored.length}</span>
      <span>Conditional {score.conditional.eligible ? "Eligible" : "Not eligible"}</span>
    </section>
  );
}

export function RequirementWorkspace({
  assessment,
  detail,
  artifacts,
  recordStates,
  focusObjectiveId,
  active,
  onDetermined,
  onRecordsChanged,
  onArtifactsChanged,
  onSaveState,
  onRoutineSaveState,
  coordinateSave,
  onPreviousRequirement,
  onNextRequirement,
  onScoreChanged,
}: {
  assessment: Assessment;
  detail: RecordDetail;
  artifacts: Artifact[];
  recordStates: Record<string, RecordState>;
  focusObjectiveId: string;
  /** False while another top-level view covers the assessment; keys are ignored then. */
  active: boolean;
  onDetermined: () => void;
  onRecordsChanged: () => void;
  onArtifactsChanged: () => void;
  onSaveState: (state: "saving" | "saved" | "error", message?: string) => void;
  onRoutineSaveState: RoutineSaveReporter;
  coordinateSave: RoutineRecordSaveCoordinator;
  onPreviousRequirement: (() => void) | null;
  onNextRequirement: (() => void) | null;
  onScoreChanged: () => void;
}) {
  const objectives = detail.children;
  const projectId = assessment.project.id;
  const statuses = assessment.framework.declarations.status_set.filter(Boolean);
  const [focusId, setFocusId] = useState(() => {
    if (objectives.some((objective) => objective.record_id === focusObjectiveId)) return focusObjectiveId;
    return (objectives.find((objective) => !isDecided(objective.determination?.status)) ?? objectives[0])?.record_id ?? "";
  });
  const [mode, setMode] = useState<"requirement" | "interview">("requirement");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [objectiveDetails, setObjectiveDetails] = useState<Record<string, RecordDetail>>({});
  const [sspTick, setSspTick] = useState(0);
  const handlesRef = useRef(new Map<string, ObjectiveHandle>());
  const rowRefs = useRef(new Map<string, HTMLLIElement>());
  const scrolledRef = useRef(false);

  const childIds = objectives.map((objective) => objective.record_id).join("|");
  const recordUrl = useCallback(
    (recordId: string) => `/api/projects/${projectId}/assessments/${assessment.id}/records/${encodeURIComponent(recordId)}`,
    [projectId, assessment.id],
  );

  // Objective notes and evidence live on each objective's own record.
  useEffect(() => {
    const controller = new AbortController();
    for (const recordId of childIds ? childIds.split("|") : []) {
      request<RecordDetail>(recordUrl(recordId), { signal: controller.signal })
        .then((next) => setObjectiveDetails((current) => ({ ...current, [recordId]: next })))
        .catch(() => undefined);
    }
    return () => controller.abort();
  }, [childIds, recordUrl]);

  const reloadObjective = useCallback((recordId: string) => {
    request<RecordDetail>(recordUrl(recordId))
      .then((next) => setObjectiveDetails((current) => ({ ...current, [recordId]: next })))
      .catch(() => undefined);
  }, [recordUrl]);

  const register = useCallback((recordId: string, handle: ObjectiveHandle | null) => {
    if (handle) handlesRef.current.set(recordId, handle);
    else handlesRef.current.delete(recordId);
  }, []);

  const focusIndex = Math.max(0, objectives.findIndex((objective) => objective.record_id === focusId));
  const moveFocus = useCallback((delta: number) => {
    if (objectives.length === 0) return;
    const next = Math.min(objectives.length - 1, Math.max(0, focusIndex + delta));
    setFocusId(objectives[next].record_id);
  }, [focusIndex, objectives]);

  useEffect(() => {
    // Keep the opening view at the top; follow focus once the user moves it.
    if (!scrolledRef.current) {
      scrolledRef.current = true;
      return;
    }
    rowRefs.current.get(focusId)?.scrollIntoView?.({ block: "nearest" });
  }, [focusId]);

  useEffect(() => {
    if (!active) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey || isTyping(event.target)) return;
      const key = event.key.length === 1 ? event.key.toLowerCase() : event.key;
      if (key === "ArrowDown") moveFocus(1);
      else if (key === "ArrowUp") moveFocus(-1);
      else if (key in STATUS_KEYS && statuses.includes(STATUS_KEYS[key])) handlesRef.current.get(focusId)?.setStatus(STATUS_KEYS[key]);
      else if ((key === "j" || key === "]") && onNextRequirement) onNextRequirement();
      else if ((key === "k" || key === "[") && onPreviousRequirement) onPreviousRequirement();
      else return;
      event.preventDefault();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [active, focusId, moveFocus, onNextRequirement, onPreviousRequirement, statuses]);

  const decided = objectives.filter((objective) => isDecided(objective.determination?.status)).length;
  const focused = objectives[focusIndex];
  const focusedDetail = focused ? objectiveDetails[focused.record_id] : undefined;
  const guidance = detail.practitioner_guidance;
  const scoring = assessment.framework.declarations.scoring;

  return (
    <div className={`requirement-workspace mode-${mode}`}>
      <section className="requirement-head">
        <div className="requirement-head-top">
          <div>
            <p className="citation">{detail.record.citation} · {detail.record.work_area}</p>
            <h1>{detail.record.title}</h1>
          </div>
          <div className="requirement-head-actions">
            <StatusPill status={detail.determination.status} derived />
            <div className="mode-toggle" role="group" aria-label="Assessment view">
              <button type="button" aria-pressed={mode === "requirement"} className={mode === "requirement" ? "selected" : ""} onClick={() => setMode("requirement")}>Requirement view</button>
              <button type="button" aria-pressed={mode === "interview"} className={mode === "interview" ? "selected" : ""} onClick={() => setMode("interview")}>Interview view</button>
            </div>
          </div>
        </div>
        <blockquote>{detail.record.regulation_text}</blockquote>
      </section>

      {(guidance || detail.prompts.length > 0) && (
        <details className="requirement-guidance">
          <summary><ChevronRight size={13} /> Guidance{detail.prompts.length > 0 ? ` and ${detail.prompts.length} question${detail.prompts.length === 1 ? "" : "s"}` : ""}</summary>
          {guidance && (
            <section className="practitioner-guidance" aria-label="RainTech practitioner guidance">
              <p className="eyebrow">RAINTECH PRACTITIONER GUIDANCE · NOT DOD OR NIST TEXT</p>
              <dl>
                {Object.entries(guidance.fields)
                  .filter(([field, value]) => value && field !== "worksheet_level")
                  .map(([field, value]) => (
                    <div key={field}>
                      <dt>{GUIDANCE_LABELS[field] ?? field.replaceAll("_", " ")}</dt>
                      <dd>{value}</dd>
                    </div>
                  ))}
              </dl>
              <small>{guidance.provenance}</small>
            </section>
          )}
          {detail.prompts.length > 0 && (
            <ul className="parent-question-list">
              {detail.prompts.map((prompt) => <li key={prompt.id}>{prompt.text}</li>)}
            </ul>
          )}
        </details>
      )}

      <section className="objective-table" aria-label="Assessment objectives">
        <div className="objective-table-head">
          <h2>Objectives <span>{decided} of {objectives.length} decided</span></h2>
          <p className="key-legend" aria-label="Keyboard shortcuts">
            <kbd>↑</kbd><kbd>↓</kbd> objective · <kbd>M</kbd> Met · <kbd>N</kbd> Not Met · <kbd>P</kbd> Pending · <kbd>J</kbd>/<kbd>K</kbd> or <kbd>]</kbd>/<kbd>[</kbd> requirement
          </p>
        </div>
        {mode === "interview" && focused && (
          <div className="interview-nav">
            <button type="button" className="small-button" disabled={focusIndex === 0} onClick={() => moveFocus(-1)}><ArrowLeft size={14} /> Previous objective</button>
            <span>Objective {focusIndex + 1} of {objectives.length}</span>
            <button type="button" className="small-button" disabled={focusIndex >= objectives.length - 1} onClick={() => moveFocus(1)}>Next objective <ArrowRight size={14} /></button>
          </div>
        )}
        <ul>
          {objectives.map((objective) => (
            <ObjectiveRow
              key={`${assessment.id}:${objective.record_id}`}
              assessmentId={assessment.id}
              objective={objective}
              statuses={statuses}
              focused={objective.record_id === focused?.record_id}
              interview={mode === "interview"}
              expanded={expanded.has(objective.record_id)}
              objectiveDetail={objectiveDetails[objective.record_id]}
              evidenceCount={objectiveDetails[objective.record_id]?.evidence.length ?? recordStates[objective.record_id]?.evidence_count ?? 0}
              rowRef={(element) => {
                if (element) rowRefs.current.set(objective.record_id, element);
                else rowRefs.current.delete(objective.record_id);
              }}
              onFocus={() => setFocusId(objective.record_id)}
              onToggle={() => setExpanded((current) => {
                const next = new Set(current);
                if (next.has(objective.record_id)) next.delete(objective.record_id);
                else next.add(objective.record_id);
                return next;
              })}
              register={register}
              onDetermined={onDetermined}
              onRoutineSaveState={onRoutineSaveState}
              coordinateSave={coordinateSave}
            />
          ))}
        </ul>
      </section>

      <div className="requirement-columns">
        {scoring && (
          <ImplementationStatement
            key={`statement:${detail.record.record_id}:${sspTick}`}
            projectId={projectId}
            assessmentId={assessment.id}
            requirementId={detail.record.record_id}
            initialNote={detail.note}
            onRoutineSaveState={onRoutineSaveState}
            coordinateSave={coordinateSave}
          />
        )}
        <section className="linked-evidence" aria-label="Linked evidence">
          <div className="linked-evidence-head">
            <p className="eyebrow">LINKED EVIDENCE</p>
            <h3>{focused ? focused.citation : "No objective"}</h3>
          </div>
          {focused && focusedDetail ? (
            <EvidencePanel
              key={`${assessment.id}:${focused.record_id}:evidence`}
              assessment={assessment}
              detail={focusedDetail}
              artifacts={artifacts}
              onChanged={() => {
                reloadObjective(focused.record_id);
                onRecordsChanged();
              }}
              onArtifactsChanged={onArtifactsChanged}
              onSaveState={onSaveState}
            />
          ) : (
            <p className="muted">{focused ? "Loading evidence…" : "This requirement has no objectives."}</p>
          )}
        </section>
      </div>

      {scoring && (
        <div className="requirement-secondary">
          <RequirementFindingPanel
            key={`${assessment.id}:${detail.record.record_id}:finding`}
            projectId={projectId}
            assessmentId={assessment.id}
            requirementId={detail.record.record_id}
            status={detail.determination.status}
            scoring={scoring.requirements[detail.record.record_id]}
            onChanged={() => {
              onScoreChanged();
              onRecordsChanged();
            }}
          />
          <details className="ssp-details">
            <summary><ChevronRight size={13} /> System Security Plan</summary>
            <SspPanel
              key={`ssp:${assessment.id}`}
              projectId={projectId}
              assessmentId={assessment.id}
              requirementId={null}
              onChanged={() => setSspTick((tick) => tick + 1)}
            />
          </details>
        </div>
      )}
    </div>
  );
}

function ObjectiveRow({
  assessmentId,
  objective,
  statuses,
  focused,
  interview,
  expanded,
  objectiveDetail,
  evidenceCount,
  rowRef,
  onFocus,
  onToggle,
  register,
  onDetermined,
  onRoutineSaveState,
  coordinateSave,
}: {
  assessmentId: string;
  objective: RecordSummary;
  statuses: Status[];
  focused: boolean;
  interview: boolean;
  expanded: boolean;
  objectiveDetail: RecordDetail | undefined;
  evidenceCount: number;
  rowRef: (element: HTMLLIElement | null) => void;
  onFocus: () => void;
  onToggle: () => void;
  register: (recordId: string, handle: ObjectiveHandle | null) => void;
  onDetermined: () => void;
  onRoutineSaveState: RoutineSaveReporter;
  coordinateSave: RoutineRecordSaveCoordinator;
}) {
  const recordId = objective.record_id;
  const {
    draft: form,
    state,
    stage,
    save,
    retry,
    error,
    saved,
  } = useRoutineAutosave<Determination>(
    `determination:${assessmentId}:${recordId}`,
    `record:${assessmentId}:${recordId}`,
    { ...EMPTY_DETERMINATION, ...objective.determination },
    async (next) => {
      await request(`/api/assessments/${assessmentId}/determinations/${encodeURIComponent(recordId)}`, {
        method: "PUT",
        body: JSON.stringify(next),
      });
    },
    onRoutineSaveState,
    coordinateSave,
    onDetermined,
  );
  const formRef = useRef(form);
  formRef.current = form;
  useEffect(() => {
    register(recordId, { setStatus: (status) => save({ ...formRef.current, status }) });
    return () => register(recordId, null);
  }, [recordId, register, save]);

  // A refused save shows the last saved status, not the attempted one (#140).
  const shownStatus = state === "failed" ? saved.status : form.status;
  const open = expanded || interview;
  return (
    <li
      ref={rowRef}
      className={`objective-item ${focused ? "focused" : ""} ${interview && !focused ? "interview-hidden" : ""} ${state === "failed" ? "failed" : ""}`}
      aria-current={focused ? "true" : undefined}
      aria-label={`Objective ${objective.citation}`}
    >
      <div className="objective-line" onClick={onFocus}>
        <span className="objective-citation">{objective.citation}</span>
        <span className="objective-text">{objective.regulation_text}</span>
        <span
          className={`objective-evidence ${evidenceCount > 0 ? "has-evidence" : ""}`}
          title={evidenceCount > 0 ? `${evidenceCount} evidence mapping(s)` : "No evidence mapped"}
          aria-label={evidenceCount > 0 ? `${evidenceCount} evidence` : "No evidence"}
        >
          <FileCheck2 size={13} />{evidenceCount > 0 ? evidenceCount : ""}
        </span>
        <div className="objective-buttons" role="group" aria-label={`Determination for ${objective.citation}`}>
          {statuses.map((status) => (
            <button
              key={status}
              type="button"
              className={`det-${statusSlug(status)} ${shownStatus === status ? "selected" : ""} ${state === "failed" && form.status === status && saved.status !== status ? "attempted" : ""}`}
              aria-pressed={shownStatus === status}
              onClick={() => {
                onFocus();
                save({ ...form, status });
              }}
            >
              {status}
            </button>
          ))}
        </div>
        <button
          type="button"
          className="icon-button"
          aria-expanded={open}
          aria-label={`Notes for ${objective.citation}`}
          onClick={(event) => {
            event.stopPropagation();
            onToggle();
          }}
        >
          {open ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
        </button>
      </div>
      <RoutineSaveStatus
        state={state}
        retry={retry}
        label={`${objective.citation} determination`}
        message={error ? `${error}. Saved status is still ${saved.status || "Blank"}` : ""}
      />
      {open && (
        <div className="objective-notes">
          {objectiveDetail ? (
            <ObjectiveNotesEditor
              assessmentId={assessmentId}
              recordId={recordId}
              citation={objective.citation}
              initialNote={objectiveDetail.note}
              onRoutineSaveState={onRoutineSaveState}
              coordinateSave={coordinateSave}
            />
          ) : (
            <p className="muted">Loading notes…</p>
          )}
          <label className="observation-field">
            Documented interview or observation <small>supports Met without mapped evidence</small>
            <textarea
              aria-label={`Interview or observation record for ${objective.citation}`}
              rows={2}
              value={form.interview_observation}
              onChange={(event) => stage({ ...form, interview_observation: event.target.value })}
              onBlur={() => save(form)}
              placeholder="Who was interviewed or what was observed?"
            />
          </label>
        </div>
      )}
    </li>
  );
}

function ObjectiveNotesEditor({
  assessmentId,
  recordId,
  citation,
  initialNote,
  onRoutineSaveState,
  coordinateSave,
}: {
  assessmentId: string;
  recordId: string;
  citation: string;
  initialNote: string;
  onRoutineSaveState: RoutineSaveReporter;
  coordinateSave: RoutineRecordSaveCoordinator;
}) {
  const initial = useMemo(() => parseObjectiveNotes(initialNote), [initialNote]);
  const { draft, state, stage, save, retry, error } = useRoutineAutosave(
    `note:${assessmentId}:${recordId}`,
    `record:${assessmentId}:${recordId}`,
    initial,
    async (next) => {
      await request(`/api/assessments/${assessmentId}/records/${encodeURIComponent(recordId)}/note`, {
        method: "PUT",
        body: JSON.stringify({ note: serializeObjectiveNotes(next) }),
      });
    },
    onRoutineSaveState,
    coordinateSave,
  );
  return (
    <div className="method-notes">
      {NOTE_METHODS.map((method) => (
        <label key={method}>
          {methodLabel(method)}
          <textarea
            aria-label={`${methodLabel(method)} notes for ${citation}`}
            rows={2}
            value={draft[method]}
            onChange={(event) => stage({ ...draft, [method]: event.target.value })}
            onBlur={() => save(draft)}
          />
        </label>
      ))}
      {initial.general && (
        <label className="general-note">
          Earlier notes
          <textarea
            aria-label={`Earlier notes for ${citation}`}
            rows={2}
            value={draft.general}
            onChange={(event) => stage({ ...draft, general: event.target.value })}
            onBlur={() => save(draft)}
          />
        </label>
      )}
      <RoutineSaveStatus state={state} retry={retry} label={`${citation} notes`} message={error} />
    </div>
  );
}

/**
 * The requirement's implementation statement (#140).
 *
 * Before an SSP exists it is the requirement's record note, which SSP
 * generation already uses as the drafted implementation; it autosaves on blur.
 * Once an SSP draft exists, every SSP edit appends a version, so the statement
 * is written to the draft only when "Save to SSP draft" is pressed.
 */
function ImplementationStatement({
  projectId,
  assessmentId,
  requirementId,
  initialNote,
  onRoutineSaveState,
  coordinateSave,
}: {
  projectId: string;
  assessmentId: string;
  requirementId: string;
  initialNote: string;
  onRoutineSaveState: RoutineSaveReporter;
  coordinateSave: RoutineRecordSaveCoordinator;
}) {
  const [ssp, setSsp] = useState<SspView | null | undefined>(undefined);
  useEffect(() => {
    const controller = new AbortController();
    request<SspView | null>(`/api/projects/${projectId}/assessments/${assessmentId}/ssp`, { signal: controller.signal })
      .then((value) => setSsp(value && value.latest ? value : null))
      .catch(() => { if (!controller.signal.aborted) setSsp(null); });
    return () => controller.abort();
  }, [projectId, assessmentId]);

  const inSsp = Boolean(ssp?.latest.content.requirements[requirementId]);
  return (
    <section className="implementation-statement" aria-label="Implementation statement">
      <div className="section-title">
        <div><p className="eyebrow">IMPLEMENTATION STATEMENT · FEEDS THE SSP</p></div>
        {ssp && inSsp && <span className="muted-small">SSP version {ssp.latest.version_number}{ssp.approval ? " · approved and frozen" : " · draft"}</span>}
      </div>
      {ssp === undefined ? (
        <p className="muted">Loading…</p>
      ) : ssp && inSsp ? (
        <SspStatementEditor key={ssp.latest.id} projectId={projectId} ssp={ssp} requirementId={requirementId} onSaved={setSsp} />
      ) : (
        <NoteStatementEditor
          assessmentId={assessmentId}
          requirementId={requirementId}
          initialNote={initialNote}
          onRoutineSaveState={onRoutineSaveState}
          coordinateSave={coordinateSave}
        />
      )}
    </section>
  );
}

function NoteStatementEditor({
  assessmentId,
  requirementId,
  initialNote,
  onRoutineSaveState,
  coordinateSave,
}: {
  assessmentId: string;
  requirementId: string;
  initialNote: string;
  onRoutineSaveState: RoutineSaveReporter;
  coordinateSave: RoutineRecordSaveCoordinator;
}) {
  const { draft, state, stage, save, retry, error } = useRoutineAutosave(
    `note:${assessmentId}:${requirementId}`,
    `record:${assessmentId}:${requirementId}`,
    initialNote,
    async (next) => {
      await request(`/api/assessments/${assessmentId}/records/${encodeURIComponent(requirementId)}/note`, {
        method: "PUT",
        body: JSON.stringify({ note: next }),
      });
    },
    onRoutineSaveState,
    coordinateSave,
  );
  return (
    <>
      <textarea
        aria-label={`Implementation statement for ${requirementId}`}
        rows={4}
        value={draft}
        onChange={(event) => stage(event.target.value)}
        onBlur={() => save(draft)}
        placeholder="How the organization meets this requirement, in the words the SSP should use…"
      />
      <p className="muted-small">Saves when you leave the field. Generating the SSP uses it as this requirement's drafted implementation.</p>
      <RoutineSaveStatus state={state} retry={retry} label="implementation statement" message={error} />
    </>
  );
}

function SspStatementEditor({
  projectId,
  ssp,
  requirementId,
  onSaved,
}: {
  projectId: string;
  ssp: SspView;
  requirementId: string;
  onSaved: (ssp: SspView) => void;
}) {
  const savedText = ssp.latest.content.requirements[requirementId]?.implementation ?? "";
  const [text, setText] = useState(savedText);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const frozen = Boolean(ssp.approval);

  async function saveToSsp() {
    setBusy(true);
    setError("");
    try {
      onSaved(await request<SspView>(`/api/projects/${projectId}/ssp/${ssp.id}`, {
        method: "PUT",
        body: JSON.stringify({ requirements: { [requirementId]: text }, note: `Implementation statement for ${requirementId}.` }),
      }));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Could not save to the SSP.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <textarea
        aria-label={`Implementation statement for ${requirementId}`}
        rows={4}
        disabled={frozen}
        value={text}
        onChange={(event) => setText(event.target.value)}
      />
      {!frozen && (
        <div className="statement-actions">
          <button className="small-button" type="button" disabled={busy || text === savedText} onClick={() => void saveToSsp()}>
            {busy ? "Saving…" : "Save to SSP draft"}
          </button>
          <span className="muted-small">{text === savedText ? "Matches the SSP draft." : "Unsaved. Each save adds one SSP version."}</span>
        </div>
      )}
      {error && <p className="form-error"><CircleAlert size={16} /> {error}</p>}
    </>
  );
}
