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
import { ReadinessPanel, StartAssessmentCard } from "./views/ReadinessPanel";
import { Setup, WorkspaceCreator } from "./views/Setup";
import { DeterminationPanel, EvidencePanel, NotMetReconciliation, PromptCard, RecordNotes } from "./views/assessment/RecordPanels";
import { RequirementList } from "./views/assessment/RequirementList";
import { CmmcScoreLine } from "./views/assessment/CmmcScore";
import { UnplannedNotMet } from "./views/assessment/PoamSection";
import { RequirementWorkspace } from "./views/assessment/RequirementWorkspace";
import { BackupControl, RevalidationPanel } from "./views/close/ClosePanels";
import { EvidenceLibraryView } from "./views/evidence/EvidenceLibraryView";
import { OverviewView } from "./views/overview/OverviewView";
import { ReportsView } from "./views/reports/ReportsView";
import type {
  Artifact,
  Assessment,
  BlockerGroup,
  Client,
  OverviewData,
  NotMetWithoutPoam,
  ProfileReadiness,
  RecordDetail,
  RecordState,
} from "./types";

type WorkspaceView = "assessment" | "overview" | "profile" | "sra" | "evidence" | "reports";

/**
 * A list narrowed to some records, with the words the chip shows (#143, #144).
 * `ids` are requirement ids for CMMC and record ids for HIPAA; `count` is the
 * figure the user pressed, which can differ from the number of ids. A filter
 * opened from a grouped count carries its `groupKey` and is recomputed from
 * the server as work changes, so the chip never goes stale.
 */
export interface RecordFilter {
  label: string;
  ids: string[];
  count?: number;
  groupKey?: string;
}

const UNPLANNED_LABEL = "NOT MET without a POA&M";

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
  initialView?: "assessment" | "overview" | "profile" | "reports";
}) {
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [loadedProjectId, setLoadedProjectId] = useState("");
  const [revalidationTick, setRevalidationTick] = useState(0);
  const [scoreTick, setScoreTick] = useState(0);
  const [evidenceTick, setEvidenceTick] = useState(0);
  const [readiness, setReadiness] = useState<ProfileReadiness | null>(null);
  const [progress, setProgress] = useState<Assessment["progress"] | null>(null);
  const [recordId, setRecordId] = useState("");
  const [focusObjectiveId, setFocusObjectiveId] = useState("");
  const [recordStates, setRecordStates] = useState<Record<string, RecordState>>({});
  // NOT MET requirements not on any open POA&M item, and whether the list shows only them (#143).
  const [unplanned, setUnplanned] = useState<NotMetWithoutPoam | null>(null);
  const [listFilter, setListFilter] = useState<RecordFilter | null>(null);
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
  const [view, setView] = useState<WorkspaceView>(initialView);
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
    setUnplanned(next?.not_met_without_poam ?? null);
    setListFilter(null);
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
    setUnplanned(next.not_met_without_poam ?? null);
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
        // The screen offers a retry when readiness loaded but the assessment did not.
        if (!controller.signal.aborted) console.error(error);
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

  const changeView = useCallback((nextView: WorkspaceView) => {
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

  // The "without a POA&M" filter follows the live count as drafts are created.
  const activeFilter = useMemo<RecordFilter | null>(
    () => (listFilter?.label === UNPLANNED_LABEL && unplanned
      ? { label: UNPLANNED_LABEL, ids: unplanned.requirement_ids }
      : listFilter),
    [listFilter, unplanned],
  );

  const filtered = useMemo(() => {
    if (!assessment || objectiveMode) return [];
    const term = search.toLowerCase();
    const only = activeFilter ? new Set(activeFilter.ids) : null;
    return assessment.work_list.filter(
      (record) =>
        (!only || only.has(record.record_id)) &&
        (area === "all" || record.work_area === area) &&
        (!term ||
          record.title.toLowerCase().includes(term) ||
          record.citation.toLowerCase().includes(term)),
    );
  }, [assessment, search, area, objectiveMode, activeFilter]);

  // CMMC objectives are worked on their requirement, so objective ids map to the parent.
  const mapFilterIds = useCallback((recordIds: string[]) => {
    if (!assessment) return [];
    const parentOf = new Map(assessment.work_list.map((record) => [record.record_id, record.parent_id]));
    return [...new Set(recordIds.map((id) => (objectiveMode ? parentOf.get(id) ?? id : id)))];
  }, [assessment, objectiveMode]);

  // Every grouped count on the Overview opens Assessments narrowed to its records (#144).
  const openGroup = useCallback((group: BlockerGroup) => {
    const target = group.target;
    if (target === "profile") return changeView("profile");
    if (target === "sra") return changeView("sra");
    if (target === "evidence") return changeView("evidence");
    if (target === "overview") return changeView("reports");
    if (!assessment || !confirmRoutineNavigation()) return;
    if (target === "ssp") {
      // The SSP is edited in the requirement view, under "System Security Plan".
      const first = assessment.work_list.find((record) => !record.parent_id)?.record_id ?? "";
      setListFilter(null);
      setView("assessment");
      if (first && first !== recordId) {
        setFocusObjectiveId("");
        setReturnRecordId("");
        setRecordId(first);
      }
      return;
    }
    const ids = mapFilterIds(group.record_ids);
    setListFilter({ label: group.label, ids, count: group.count, groupKey: group.key });
    setView("assessment");
    if (ids.length > 0 && !ids.includes(recordId)) {
      setFocusObjectiveId("");
      setReturnRecordId("");
      setRecordId(ids[0]);
    }
  }, [assessment, changeView, confirmRoutineNavigation, mapFilterIds, recordId]);

  // Keep a grouped-count filter live: recompute it as determinations, evidence and records change.
  const filterGroupKey = listFilter?.groupKey;
  const filterProjectId = assessment?.project.id;
  const filterAssessmentId = assessment?.id;
  const filterProgress = progress?.resolved_determination_count;
  useEffect(() => {
    if (!filterGroupKey || !filterProjectId || !filterAssessmentId) return;
    const controller = new AbortController();
    request<OverviewData>(`/api/projects/${filterProjectId}/assessments/${filterAssessmentId}/overview`, { signal: controller.signal })
      .then((next) => {
        const group = next.left_before_issue?.groups?.find((candidate) => candidate.key === filterGroupKey);
        setListFilter((current) => (
          current?.groupKey === filterGroupKey
            ? { ...current, ids: mapFilterIds(group?.record_ids ?? []), count: group?.count ?? 0 }
            : current
        ));
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, [filterGroupKey, filterProjectId, filterAssessmentId, filterProgress, scoreTick, evidenceTick, revalidationTick, mapFilterIds]);

  const openStep = useCallback((target: string) => {
    if (target === "profile") changeView("profile");
    else if (target === "reports") changeView("reports");
    else changeView("assessment");
  }, [changeView]);

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
              <ReadinessPanel readiness={readiness} onChanged={reloadWorkspace} />
            </>
          ) : view === "sra" ? (
            <SraPanel key={`${projectId}:${assessment?.id ?? "none"}`} projectId={projectId} assessmentId={assessment?.id} onDirtyChange={setProfileDirty} />
          ) : readiness.assessment_exists ? (
            <section className="start-card" role="alert">
              <h1>The assessment did not open</h1>
              <p>It exists, but its records could not be loaded. Nothing was lost.</p>
              <button className="primary-button" onClick={() => void reloadWorkspace()}>Try again</button>
            </section>
          ) : (
            <StartAssessmentCard
              readiness={readiness}
              onChanged={reloadWorkspace}
              onStarted={() => setView("assessment")}
              onOpenProfile={() => setView("profile")}
            />
          )}
        </main>
        {creatingWorkspace && (
          <WorkspaceCreator
            clients={clients}
            onCancel={() => setCreatingWorkspace(false)}
            onCreated={(id) => {
              setCreatingWorkspace(false);
              setView("assessment");
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
          <button className={view === "evidence" ? "active" : ""} onClick={() => changeView("evidence")}>Evidence</button>
          <button className={view === "reports" ? "active" : ""} onClick={() => changeView("reports")}>Reports</button>
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
          {activeFilter && (
            <div className="list-filter-chip" role="status">
              <span>{`Showing: ${activeFilter.label} (${activeFilter.count ?? activeFilter.ids.length}) ·`}</span>
              {" "}
              <button type="button" className="text-button" onClick={() => setListFilter(null)}>Show all</button>
            </div>
          )}
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
            onlyIds={activeFilter ? new Set(activeFilter.ids) : null}
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
              {unplanned && (
                <UnplannedNotMet
                  summary={unplanned}
                  active={listFilter?.label === UNPLANNED_LABEL}
                  onToggle={() => setListFilter((current) => (
                    current?.label === UNPLANNED_LABEL ? null : { label: UNPLANNED_LABEL, ids: unplanned.requirement_ids }
                  ))}
                />
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
            key={`${assessment.id}:${detail.record.record_id}:${evidenceTick}`}
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
        <OverviewView
          key={`overview:${assessment.project.id}:${assessment.id}`}
          projectId={assessment.project.id}
          assessmentId={assessment.id}
          projectName={assessment.project.name}
          clientName={assessment.project.client_name}
          frameworkName={assessment.framework.name}
          scored={Boolean(assessment.framework.declarations.scoring)}
          refreshKey={`${scoreTick}:${progress.resolved_determination_count}:${revalidationTick}:${evidenceTick}`}
          otherProjects={projects
            .filter((project) => project.id !== projectId)
            .map((project) => ({ id: project.id, name: project.name, clientName: project.clientName, framework: project.framework_version_id }))}
          onOpenProject={(id) => {
            if (changeProject(id)) setView("assessment");
          }}
          onOpenStep={openStep}
          onOpenGroup={openGroup}
          onOpenRecord={(next) => {
            changeRecord(next);
            setView("assessment");
          }}
        />
      )}
      {view === "reports" && (
        <ReportsView
          projectId={assessment.project.id}
          assessmentId={assessment.id}
          records={assessment.record_index}
          hasClose={Boolean(assessment.framework.declarations.close_readiness)}
          refreshKey={revalidationTick}
          onNavigate={(link) => {
            const target = String(link.target ?? link.view ?? "");
            if (target === "profile" || target === "sra") changeView(target as "profile" | "sra");
            else if (link.record_id || link.recordId) {
              changeRecord(String(link.record_id ?? link.recordId));
              setView("assessment");
            }
          }}
          onReopened={async () => {
            await refreshAssessmentProgress();
            setView("assessment");
          }}
        />
      )}
      {view === "evidence" && (
        <EvidenceLibraryView
          key={`evidence:${projectId}`}
          projectId={assessment.project.id}
          onOpenRecord={(next) => {
            const parentId = objectiveMode ? assessment.work_list.find((record) => record.record_id === next)?.parent_id : null;
            if ((parentId ?? next) === recordId) {
              // Already on that requirement: refocus the objective row.
              setFocusObjectiveId(parentId ? next : "");
              setEvidenceTick((tick) => tick + 1);
            } else {
              changeRecord(next);
            }
            setView("assessment");
          }}
          onChanged={() => {
            // Staleness, renewal and lead time change derived verification (#142).
            void loadArtifacts();
            void loadDetail();
            void refreshAssessmentProgress();
            setScoreTick((tick) => tick + 1);
            setEvidenceTick((tick) => tick + 1);
          }}
        />
      )}
      {view === "profile" && (
        <main className="overview-panel">
          <ProfilePanel key={projectId} projectId={projectId} onDirtyChange={setProfileDirty} />
          <ReadinessPanel readiness={readiness} onChanged={reloadWorkspace} />
        </main>
      )}
      {creatingWorkspace && (
        <WorkspaceCreator
          clients={clients}
          onCancel={() => setCreatingWorkspace(false)}
          onCreated={(id) => {
            setCreatingWorkspace(false);
            setView("assessment");
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
    return (
      <Setup
        onCreated={(id) => {
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
      initialView="assessment"
    />
  );
}
