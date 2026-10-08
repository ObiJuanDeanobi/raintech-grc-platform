import {
  CircleAlert,
  FileCheck2,
  FileUp,
  X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useRef, useState } from "react";

import { ApiError, request } from "../../api";
import { RoutineSaveStatus } from "../../components/RoutineSaveStatus";
import { StatusPill } from "../../components/StatusPill";
import { artifactLabel, reviewDetail, shortHash } from "../../lib/evidence";
import { RoutineRecordSaveCoordinator, RoutineSaveReporter, useRoutineAutosave } from "../../components/routineSave";
import { PoamEligibility, PoamSection } from "./PoamSection";
import type {
  Artifact,
  Assessment,
  CmmcScore,
  FrameworkDeclarations,
  RequirementFinding,
  SspView,
  EvidenceMapping,
  Prompt,
  RecordDetail,
  ReconciliationDisposition,
  ReconciliationRecord,
  CorrectiveActionValidation,
  Status,
} from "../../types";

export function PromptCard({
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
    error: answerError,
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
      <RoutineSaveStatus state={answerSaveState} retry={retryAnswer} label="answer" message={answerError} />
    </article>
  );
}

export function DeterminationPanel({
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
    error: determinationError,
    saved: savedDetermination,
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
        {/* A refused save keeps showing the last saved status (#140). */}
        <StatusPill status={determinationSaveState === "failed" ? savedDetermination.status : form.status} />
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
      <RoutineSaveStatus state={determinationSaveState} retry={retryDetermination} label="determination" message={determinationError} />
    </section>
  );
}

export function RequirementFindingPanel({
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
  const [eligibility, setEligibility] = useState<PoamEligibility | null>(null);
  const [eligibilityTick, setEligibilityTick] = useState(0);
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

  // 32 CFR 170.21 POA&M eligibility comes from this requirement's score line (#141, #143).
  useEffect(() => {
    if (status !== "Not Met") {
      setEligibility(null);
      return;
    }
    const controller = new AbortController();
    request<CmmcScore | null>(`/api/projects/${projectId}/assessments/${assessmentId}/cmmc-score`, { signal: controller.signal })
      .then((score) => {
        const line = score?.deductions?.find((deduction) => deduction.record_id === requirementId);
        setEligibility(line ? { allowed: line.conditional_poam_allowed, reason: line.poam_reason } : null);
      })
      .catch(() => undefined);
    return () => controller.abort();
  }, [projectId, assessmentId, requirementId, status, eligibilityTick]);

  async function savePartial(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      await request(`${base}/partial-implementation`, { method: "PUT", body: JSON.stringify({ implementation, rationale }) });
      setEligibilityTick((tick) => tick + 1);
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
          <PoamSection base={base} finding={finding} eligibility={eligibility} onFinding={setFinding} onChanged={onChanged} />
          <details className="reconciliation-history"><summary>Finding history</summary><ul>{finding.history.map((entry) => <li key={`${entry.event}:${entry.created_at}`}>{entry.event.replaceAll("_", " ")} · {entry.failed_objectives.join(", ") || "none"} · {new Date(entry.created_at).toLocaleString()}</li>)}</ul></details>
        </>
      )}
      {error && <p className="form-error"><CircleAlert size={16} /> {error}</p>}
    </section>
  );
}

export function SspPanel({ projectId, assessmentId, requirementId, onChanged }: { projectId: string; assessmentId: string; requirementId: string | null; onChanged?: () => void }) {
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
      onChanged?.();
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

export function NotMetReconciliation({ projectId, assessmentId, recordId, status }: { projectId: string; assessmentId: string; recordId: string; status: string }) {
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

export function RecordNotes({
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
    error: noteError,
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
      <RoutineSaveStatus state={noteSaveState} retry={retryNote} label="note" message={noteError} />
    </section>
  );
}

export function EvidencePanel({
  assessment,
  detail,
  artifacts,
  onChanged,
  onArtifactsChanged,
  onSaveState,
  mapForm = true,
}: {
  assessment: Assessment;
  detail: RecordDetail;
  artifacts: Artifact[];
  onChanged: () => void;
  onArtifactsChanged: () => void;
  onSaveState: (state: "saving" | "saved" | "error", message?: string) => void;
  /** False where the requirement view's multi-objective picker links evidence instead (#142). */
  mapForm?: boolean;
}) {
  const [artifactId, setArtifactId] = useState("");
  const [rationale, setRationale] = useState("");
  const [uploading, setUploading] = useState(false);
  const [editing, setEditing] = useState<{ mappingId: string; text: string } | null>(null);
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
      if (!isCurrent(target)) return false;
      onSaveState("saved");
      onChanged();
      if (refreshArtifacts) onArtifactsChanged();
      return true;
    } catch (caught) {
      if (isCurrent(target)) onSaveState("error", caught instanceof Error ? caught.message : undefined);
      return false;
    }
  }

  function replaceFile(mapping: EvidenceMapping, file: File) {
    const data = new FormData();
    data.append("file", file);
    void evidenceAction(`/api/projects/${assessment.project.id}/evidence/${mapping.artifact_id}/versions`, { method: "POST", body: data });
  }

  async function saveRationale(mapping: EvidenceMapping, text: string) {
    const saved = await evidenceAction(
      `/api/projects/${assessment.project.id}/assessments/${assessment.id}/evidence-mappings/${mapping.mapping_id}/rationale`,
      { method: "PUT", body: JSON.stringify({ rationale: text }) },
      false,
    );
    if (saved) setEditing(null);
  }

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
        {detail.evidence.map((mapping) => {
          // Older payloads carry only the date; the server's status wins when present.
          const review = mapping.review_status ?? (mapping.review_date && mapping.review_date < today ? "stale" : undefined);
          return (
            <article className={`evidence-item ${review === "stale" ? "evidence-stale" : review === "due_soon" ? "evidence-due-soon" : ""}`} key={mapping.mapping_id}>
              <FileCheck2 size={18} />
              <div>
                <strong>{mapping.name}</strong>
                {editing?.mappingId === mapping.mapping_id ? (
                  <form className="rationale-edit" onSubmit={(event) => { event.preventDefault(); void saveRationale(mapping, editing.text); }}>
                    <textarea
                      aria-label={`Rationale for ${mapping.name}`}
                      rows={2}
                      required
                      value={editing.text}
                      onChange={(event) => setEditing({ mappingId: mapping.mapping_id, text: event.target.value })}
                    />
                    <span className="rationale-actions">
                      <button type="submit" className="text-button" disabled={!editing.text.trim()}>Save rationale</button>
                      <button type="button" className="text-button" onClick={() => setEditing(null)}>Cancel</button>
                    </span>
                  </form>
                ) : (
                  <p>
                    {mapping.rationale}{" "}
                    <button type="button" className="text-button" aria-label={`Edit rationale for ${mapping.name}`} onClick={() => setEditing({ mappingId: mapping.mapping_id, text: mapping.rationale })}>Edit</button>
                  </p>
                )}
                <span>Version {mapping.version_number}</span>
                {mapping.latest_version_number && mapping.latest_version_number > mapping.version_number && (
                  <span className="evidence-newer">
                    Version {mapping.latest_version_number} is available.{" "}
                    <button type="button" className="text-button" onClick={() => void evidenceAction(`/api/projects/${assessment.project.id}/assessments/${assessment.id}/evidence-mappings/${mapping.mapping_id}/version`, { method: "PUT" }, false)}>Use latest version</button>
                  </span>
                )}
                {review === "stale" && (
                  <>
                    <span className="evidence-overdue">Review overdue since {mapping.review_date}</span>
                    <span className="evidence-overdue">Stale: no longer verifies a Met</span>
                  </>
                )}
                {review === "due_soon" && (
                  <span className="evidence-due">{reviewDetail(mapping.review_date, review, mapping.days_until_review)}</span>
                )}
                <span title={`SHA-256 ${mapping.sha256}`}>SHA-256: {shortHash(mapping.sha256)}</span>
                <label className="text-button evidence-replace">Replace file<input type="file" aria-label={`Replace ${mapping.name}`} onChange={(event) => event.target.files?.[0] && replaceFile(mapping, event.target.files[0])} /></label>
                <span>{mapping.review_state}</span>
                <span>Shared across {mapping.shared_record_count} record{mapping.shared_record_count === 1 ? "" : "s"}</span>
              </div>
              <button className="icon-button" aria-label={`Unmap ${mapping.name}`} onClick={() => void unmap(mapping)}>
                <X size={15} />
              </button>
            </article>
          );
        })}
      </div>
      {mapForm && (
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
                <option key={artifact.id} value={artifact.id} title={`SHA-256 ${artifact.sha256}`}>
                  {artifactLabel(artifact)}
                  {" "}({artifact.shared_record_count} mappings){artifact.review_status === "stale" ? " · stale" : artifact.review_status === "due_soon" ? " · due soon" : ""}
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
      )}
      <p className="muted">Renewal, review dates and the recycle bin are in the Evidence view.</p>
    </section>
  );
}
