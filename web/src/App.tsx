import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  ChevronDown,
  CircleAlert,
  Cloud,
  FolderKanban,
  ListFilter,
  LoaderCircle,
  Search,
  ShieldCheck,
  UserRound,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ApiError, request } from "./api";
import { ProfilePanel } from "./ProfilePanel";
import { SraPanel } from "./SraPanel";
import { StatusPill } from "./components/StatusPill";
import { RoutineSaveReporter, RoutineSaveState, useRoutineRecordSaveCoordinator } from "./components/routineSave";
import { GUIDANCE_LABELS } from "./lib/guidance";
import { firstActionableRequirement } from "./lib/requirements";
import { ReadinessPanel } from "./views/ReadinessPanel";
import { Setup, WorkspaceCreator } from "./views/Setup";
import { DeterminationPanel, EvidencePanel, NotMetReconciliation, PromptCard, RecordNotes } from "./views/assessment/RecordPanels";
import { RequirementList } from "./views/assessment/RequirementList";
import { CmmcScoreLine, CmmcScorePanel } from "./views/assessment/CmmcScore";
import { RequirementWorkspace } from "./views/assessment/RequirementWorkspace";
import { BackupControl, CloseReadinessPanel, PackageGenerationPanel, RevalidationPanel } from "./views/close/ClosePanels";
import type {
  Artifact,
  Assessment,
  Client,
  ProfileReadiness,
  RecordDetail,
  RecordState,
} from "./types";

function isRequirementCentred(assessment: Assessment | null | undefined): boolean {
  return assessment?.framework?.declarations?.presentation_mode === "requirement_with_objectives";
}

/** CMMC opens on the first requirement with an undecided objective (#140). */
function openingRecordId(assessment: Assessment | null): string {
  if (!assessment) return "";
  if (isRequirementCentred(assessment)) {
    return firstActionableRequirement(assessment.work_list, assessment.record_states ?? {});
  }
  return assessment.work_list[0]?.record_id || "";
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
  initialView?: "assessment" | "overview" | "profile";
}) {
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [loadedProjectId, setLoadedProjectId] = useState("");
  const [revalidationTick, setRevalidationTick] = useState(0);
  const [scoreTick, setScoreTick] = useState(0);
  const [readiness, setReadiness] = useState<ProfileReadiness | null>(null);
  const [progress, setProgress] = useState<Assessment["progress"] | null>(null);
  const [recordId, setRecordId] = useState("");
  const [focusObjectiveId, setFocusObjectiveId] = useState("");
  const [recordStates, setRecordStates] = useState<Record<string, RecordState>>({});
  const [expandedFamilies, setExpandedFamilies] = useState<Map<string, boolean>>(() => new Map());
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
    setRecordStates(next?.record_states ?? {});
    setFocusObjectiveId("");
    setRecordId(openingRecordId(next));
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
    setRecordStates(next.record_states ?? {});
    if (next.id !== targetAssessmentId) {
      setDetail(null);
      detailLoadedTargetRef.current = { assessmentId: "", recordId: "" };
      setFocusObjectiveId("");
      setRecordId(openingRecordId(next));
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
    setFocusObjectiveId("");
    setRecordStates({});
    setExpandedFamilies(new Map());
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

  // CMMC presents each requirement with its objectives; HIPAA one record at a time.
  const objectiveMode = isRequirementCentred(assessment);

  const changeRecord = useCallback((nextRecordId: string, nextReturnRecordId = "") => {
    // CMMC objectives are worked on their requirement's view (#140).
    const parentId = objectiveMode
      ? assessment?.work_list.find((record) => record.record_id === nextRecordId)?.parent_id
      : null;
    const targetRecordId = parentId ?? nextRecordId;
    if (targetRecordId === recordId || !confirmRoutineNavigation()) return;
    setFocusObjectiveId(parentId ? nextRecordId : "");
    setReturnRecordId(nextReturnRecordId);
    setRecordId(targetRecordId);
  }, [assessment, confirmRoutineNavigation, objectiveMode, recordId]);

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

  const filtered = useMemo(() => {
    if (!assessment || objectiveMode) return [];
    const term = search.toLowerCase();
    return assessment.work_list.filter(
      (record) =>
        (area === "all" || record.work_area === area) &&
        (!term ||
          record.title.toLowerCase().includes(term) ||
          record.citation.toLowerCase().includes(term)),
    );
  }, [assessment, search, area, objectiveMode]);

  const requirementIds = useMemo(
    () => (assessment && objectiveMode ? assessment.work_list.filter((record) => !record.parent_id).map((record) => record.record_id) : []),
    [assessment, objectiveMode],
  );
  const requirementIndex = requirementIds.indexOf(recordId);
  const previousRequirementId = requirementIndex > 0 ? requirementIds[requirementIndex - 1] : "";
  const nextRequirementId = requirementIndex >= 0 && requirementIndex < requirementIds.length - 1 ? requirementIds[requirementIndex + 1] : "";

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
    <div className={`app-shell ${objectiveMode ? "requirement-shell" : ""}`}>
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
          <span>{objectiveMode ? requirementIds.length : assessment.work_list.length}</span>
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
        {objectiveMode ? (
          <RequirementList
            workList={assessment.work_list}
            states={recordStates}
            activeRequirementId={recordId}
            search={search}
            area={area}
            expanded={expandedFamilies}
            onExpandedChange={setExpandedFamilies}
            onSelect={(requirementId) => changeRecord(requirementId)}
          />
        ) : (
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
        )}
      </aside>

      {view === "sra" && <SraPanel key={`${projectId}:${assessment.id}`} projectId={projectId} assessmentId={assessment.id} onDirtyChange={setProfileDirty} />}
      <main className={`assessment-main ${objectiveMode ? "requirement-main" : ""} ${view !== "assessment" ? "workspace-hidden" : ""}`}>
        {objectiveMode ? (
          <div className="record-toolbar">
            <div>
              <span className={`readiness-state compact ${readiness.assessment_entry_allowed ? "ready" : "blocked"}`}>
                {readiness.state}
              </span>
              <span className="position">Requirement {requirementIndex + 1} of {requirementIds.length}</span>
              <span className="position">
                {progress.resolved_determination_count} of {progress.determination_record_count} objectives decided
              </span>
              {assessment.framework.declarations.scoring && (
                <CmmcScoreLine projectId={assessment.project.id} assessmentId={assessment.id} refreshKey={`${scoreTick}:${progress.resolved_determination_count}`} />
              )}
            </div>
            <div className="previous-next">
              <button aria-label="Previous requirement" title="Previous requirement (K or [)" disabled={!previousRequirementId} onClick={() => previousRequirementId && changeRecord(previousRequirementId)}>
                <ArrowLeft size={16} /> Previous
              </button>
              <button aria-label="Next requirement" title="Next requirement (J or ])" disabled={!nextRequirementId} onClick={() => nextRequirementId && changeRecord(nextRequirementId)}>
                Next <ArrowRight size={16} />
              </button>
            </div>
          </div>
        ) : (
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
        )}
        {readiness.assessment_entry_blocking_reasons.length > 0 && (
          <div className="assessment-readiness-warning">
            <strong>New assessment entry is blocked.</strong>
            {readiness.assessment_entry_blocking_reasons.map((reason) => (
              <span key={reason}>{reason}</span>
            ))}
          </div>
        )}
        {assessment.reopening && <RevalidationPanel key={`revalidation:${assessment.id}`} projectId={assessment.project.id} assessmentId={assessment.id} reopening={assessment.reopening} items={assessment.revalidation_items ?? []} currentRecordId={recordId} onChanged={() => setRevalidationTick((tick) => tick + 1)} onOpenRecord={(next) => changeRecord(next)} />}

        {objectiveMode ? (
          <RequirementWorkspace
            key={`${assessment.id}:${detail.record.record_id}`}
            assessment={assessment}
            detail={detail}
            artifacts={artifacts}
            recordStates={recordStates}
            focusObjectiveId={focusObjectiveId}
            active={view === "assessment" && !creatingWorkspace}
            onDetermined={() => {
              void loadDetail();
              void refreshAssessmentProgress();
              setScoreTick((tick) => tick + 1);
            }}
            onRecordsChanged={() => void refreshAssessmentProgress()}
            onArtifactsChanged={() => void loadArtifacts()}
            onSaveState={updateSaveState}
            onRoutineSaveState={reportRoutineSave}
            coordinateSave={coordinateRoutineSave}
            onPreviousRequirement={previousRequirementId ? () => changeRecord(previousRequirementId) : null}
            onNextRequirement={nextRequirementId ? () => changeRecord(nextRequirementId) : null}
            onScoreChanged={() => setScoreTick((tick) => tick + 1)}
          />
        ) : (
        <>
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
        </>
        )}
      </main>

      {!objectiveMode && (
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
        {/* Objective-level reconciliation is HIPAA's; CMMC findings are requirement-level. */}
        <NotMetReconciliation
          key={`${assessment.id}:${detail.record.record_id}:reconciliation`}
          assessmentId={assessment.id}
          projectId={assessment.project.id}
          recordId={detail.record.record_id}
          status={detail.determination.status}
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
      )}
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
          {assessment.framework.declarations.scoring && (
            <CmmcScorePanel projectId={assessment.project.id} assessmentId={assessment.id} refreshKey={`${scoreTick}:${progress.resolved_determination_count}:${revalidationTick}`} />
          )}
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
          {assessment.framework.declarations.close_readiness && <CloseReadinessPanel key={`close:${assessment.project.id}:${assessment.id}:${revalidationTick}`} projectId={assessment.project.id} assessmentId={assessment.id} onNavigate={(link) => {
            const target = String(link.target ?? link.view ?? "");
            if (target === "profile" || target === "sra") changeView(target as "profile" | "sra");
            else if (link.record_id || link.recordId) {
              changeRecord(String(link.record_id ?? link.recordId));
              setView("assessment");
            }
          }} />}
          {assessment.framework.declarations.close_readiness && <PackageGenerationPanel key={`package:${assessment.project.id}:${assessment.id}:${revalidationTick}`} projectId={assessment.project.id} assessmentId={assessment.id} records={assessment.record_index} onReopened={async () => {
            await refreshAssessmentProgress();
            setView("assessment");
          }} />}
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
