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
  MoveRight,
  Search,
  ShieldCheck,
  UserRound,
  X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { ApiError, request } from "./api";
import type {
  Artifact,
  Assessment,
  Client,
  Determination,
  EvidenceMapping,
  Prompt,
  PromptWorkingRecord,
  RecordDetail,
  Status,
} from "./types";

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
          Create the first client project. The assessment is pinned to the July 2026
          HIPAA catalog and saved locally as you work.
        </p>
        <div className="setup-facts">
          <span><Check size={16} /> 194 cited records</span>
          <span><Check size={16} /> 1,163 assessor prompts</span>
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
  selected,
  onSelect,
  onChanged,
  onSaveState,
}: {
  prompt: Prompt;
  assessment: Assessment;
  selected: boolean;
  onSelect: () => void;
  onChanged: () => void;
  onSaveState: (state: "saving" | "saved" | "error", message?: string) => void;
}) {
  const [moving, setMoving] = useState(false);
  const [destination, setDestination] = useState("");
  const [rule, setRule] = useState("");
  const [reason, setReason] = useState("");

  async function movePrompt(event: FormEvent) {
    event.preventDefault();
    onSaveState("saving");
    try {
      await request(`/api/assessments/${assessment.id}/prompts/${prompt.id}/placement`, {
        method: "PUT",
        body: JSON.stringify({
          destination_record_id: destination === "__context__" ? null : destination,
          rule_citation: rule,
          reason,
        }),
      });
      setMoving(false);
      onSaveState("saved");
      onChanged();
    } catch (caught) {
      onSaveState("error", caught instanceof Error ? caught.message : undefined);
    }
  }

  return (
    <article className={`prompt-card role-${prompt.role} ${selected ? "selected" : ""}`}>
      <div className="prompt-heading">
        {prompt.working_record ? (
          <StatusPill status={prompt.working_record.status} />
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
        <button
          className="icon-button"
          aria-label={`Move question: ${prompt.text}`}
          title="Move this question"
          onClick={() => setMoving((value) => !value)}
        >
          <MoveRight size={16} />
        </button>
      </div>
      {prompt.moved_from && (
        <p className="moved-note">
          Moved from {prompt.moved_from.citation} · {prompt.placement?.rule_citation}
        </p>
      )}
      {prompt.working_record ? (
        <button
          className="open-question-record"
          type="button"
          aria-label={`Open question working record: ${prompt.text}`}
          onClick={onSelect}
        >
          {selected ? "Working record open" : "Open working record"}
          <ArrowRight size={14} />
        </button>
      ) : (
        <span className="guidance-label">Guidance only</span>
      )}
      {moving && (
        <form className="move-form" onSubmit={movePrompt}>
          <label>
            Move to
            <select required value={destination} onChange={(event) => setDestination(event.target.value)}>
              <option value="">Choose a record…</option>
              <option value="__context__">Context only (no rule)</option>
              {assessment.record_index.map((record) => (
                <option key={record.record_id} value={record.record_id}>
                  {record.citation} — {record.title}
                </option>
              ))}
            </select>
          </label>
          {destination && destination !== "__context__" && (
            <label>
              Rule this question tests
              <input required value={rule} onChange={(event) => setRule(event.target.value)} placeholder="45 CFR …" />
            </label>
          )}
          <label>
            Reason
            <input required value={reason} onChange={(event) => setReason(event.target.value)} />
          </label>
          <div className="inline-actions">
            <button className="small-button" type="submit">Save move</button>
            <button className="text-button" type="button" onClick={() => setMoving(false)}>Cancel</button>
          </div>
        </form>
      )}
    </article>
  );
}

function DeterminationPanel({
  assessmentId,
  statuses,
  detail,
  onChanged,
  onSaveState,
}: {
  assessmentId: string;
  statuses: Status[];
  detail: RecordDetail;
  onChanged: () => void;
  onSaveState: (state: "saving" | "saved" | "error", message?: string) => void;
}) {
  const [form, setForm] = useState<Determination>(detail.determination);

  useEffect(() => setForm(detail.determination), [detail.determination]);

  async function save(next: Determination) {
    setForm(next);
    onSaveState("saving");
    try {
      await request(
        `/api/assessments/${assessmentId}/determinations/${detail.record.record_id}`,
        {
          method: "PUT",
          body: JSON.stringify(next),
        },
      );
      onSaveState("saved");
      onChanged();
    } catch (caught) {
      onSaveState("error", caught instanceof ApiError ? caught.message : undefined);
    }
  }

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
              setForm(next);
              if (status !== "N/A" && detail.record.designation !== "addressable") void save(next);
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
            onChange={(event) => setForm({ ...form, na_rationale: event.target.value })}
            onBlur={() => void save(form)}
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
                setForm(next);
                if (event.target.value === "standard_measure") void save(next);
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
                onChange={(event) => setForm({ ...form, disposition_reason: event.target.value })}
                onBlur={() => void save(form)}
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
          onChange={(event) => setForm({ ...form, interview_observation: event.target.value })}
          onBlur={() => form.status && void save(form)}
          placeholder="Who was interviewed or what was observed?"
        />
      </details>
    </section>
  );
}

function AddressableDecisionPanel({
  assessmentId,
  detail,
  onChanged,
  onSaveState,
}: {
  assessmentId: string;
  detail: RecordDetail;
  onChanged: () => void;
  onSaveState: (state: "saving" | "saved" | "error", message?: string) => void;
}) {
  const [form, setForm] = useState<Determination>(detail.determination);

  useEffect(() => setForm(detail.determination), [detail.determination]);

  if (detail.record.designation !== "addressable") return null;

  async function save(next: Determination) {
    setForm(next);
    onSaveState("saving");
    try {
      await request(
        `/api/assessments/${assessmentId}/determinations/${detail.record.record_id}`,
        { method: "PUT", body: JSON.stringify(next) },
      );
      onSaveState("saved");
      onChanged();
    } catch (caught) {
      onSaveState("error", caught instanceof ApiError ? caught.message : undefined);
    }
  }

  return (
    <section className="working-section addressable-shared">
      <div className="addressable-box">
        <p className="eyebrow">ADDRESSABLE SPECIFICATION</p>
        <p className="muted">This decision applies to every assessment question under this cited specification.</p>
        <label>
          Disposition <span className="required">required</span>
          <select
            value={form.addressable_disposition ?? ""}
            onChange={(event) => {
              const next = { ...form, addressable_disposition: event.target.value };
              setForm(next);
              if (event.target.value === "standard_measure") void save(next);
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
              onChange={(event) => setForm({ ...form, disposition_reason: event.target.value })}
              onBlur={() => void save(form)}
            />
          </label>
        )}
      </div>
    </section>
  );
}

function QuestionWorkingPanel({
  assessmentId,
  statuses,
  prompt,
  onChanged,
  onSaveState,
}: {
  assessmentId: string;
  statuses: Status[];
  prompt: Prompt;
  onChanged: () => void;
  onSaveState: (state: "saving" | "saved" | "error", message?: string) => void;
}) {
  const [form, setForm] = useState<PromptWorkingRecord>(prompt.working_record!);

  useEffect(() => setForm(prompt.working_record!), [prompt]);

  async function save(next: PromptWorkingRecord) {
    setForm(next);
    onSaveState("saving");
    try {
      await request(
        `/api/assessments/${assessmentId}/prompts/${prompt.id}/working-record`,
        {
          method: "PUT",
          body: JSON.stringify(next),
        },
      );
      onSaveState("saved");
      onChanged();
    } catch (caught) {
      onSaveState("error", caught instanceof ApiError ? caught.message : undefined);
    }
  }

  return (
    <>
      <section className="working-section question-context">
        <p className="eyebrow">ASSESSMENT QUESTION</p>
        <p className="working-question-text">{prompt.text}</p>
        <span>{prompt.source_detail || prompt.source}</span>
      </section>
      <section className="working-section">
        <div className="section-title">
          <div><p className="eyebrow">DECISION</p><h3>Question status</h3></div>
          <StatusPill status={form.status} />
        </div>
        <div className="status-grid">
          {statuses.filter(Boolean).map((status) => (
            <button
              key={status}
              type="button"
              className={`${statusClass(status)} ${form.status === status ? "selected" : ""}`}
              onClick={() => {
                const next = { ...form, status };
                setForm(next);
                if (status !== "N/A") void save(next);
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
              onChange={(event) => setForm({ ...form, na_rationale: event.target.value })}
              onBlur={() => void save(form)}
              placeholder="Explain why this question does not apply…"
            />
          </label>
        )}
        <details className="interview-box">
          <summary>Document an interview or observation</summary>
          <p>Use this when a Met decision relies on direct observation instead of evidence.</p>
          <textarea
            rows={3}
            value={form.interview_observation}
            onChange={(event) => setForm({ ...form, interview_observation: event.target.value })}
            onBlur={() => form.status && void save(form)}
            placeholder="Who was interviewed or what was observed?"
          />
        </details>
      </section>
      <section className="working-section">
        <div className="section-title">
          <div><p className="eyebrow">DISCUSSION</p><h3>Assessment notes</h3></div>
        </div>
        <textarea
          key={`${prompt.id}:${form.updated_at ?? "new"}`}
          defaultValue={form.note}
          rows={5}
          placeholder="Record the client's answer, implementation details, and assessor observations…"
          onBlur={(event) => void save({ ...form, note: event.target.value })}
        />
      </section>
    </>
  );
}

function EvidencePanel({
  assessment,
  evidence,
  targetKind,
  targetId,
  artifacts,
  onChanged,
  onArtifactsChanged,
  onSaveState,
}: {
  assessment: Assessment;
  evidence: EvidenceMapping[];
  targetKind: "record" | "question";
  targetId: string;
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
      const endpoint = targetKind === "question"
        ? `/api/assessments/${assessment.id}/prompt-evidence-mappings`
        : `/api/assessments/${assessment.id}/evidence-mappings`;
      const target = targetKind === "question"
        ? { prompt_id: targetId }
        : { record_id: targetId };
      await request(endpoint, {
        method: "POST",
        body: JSON.stringify({
          artifact_id: artifactId,
          ...target,
          rationale,
        }),
      });
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
      const endpoint = targetKind === "question"
        ? `/api/assessments/${assessment.id}/prompt-evidence-mappings/${mapping.mapping_id}`
        : `/api/assessments/${assessment.id}/evidence-mappings/${mapping.mapping_id}`;
      await request(
        endpoint,
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
        <span className="count-badge">{evidence.length}</span>
      </div>
      <div className="evidence-list">
        {evidence.length === 0 && (
          <p className="empty-copy">No evidence mapped to this {targetKind} yet.</p>
        )}
        {evidence.map((mapping) => (
          <article className="evidence-item" key={mapping.mapping_id}>
            <FileCheck2 size={18} />
            <div>
              <strong>{mapping.name}</strong>
              <p>{mapping.rationale || "No support rationale added."}</p>
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
                {artifact.name} ({artifact.shared_record_count} mappings)
              </option>
            ))}
          </select>
        </label>
        <label>
          Support rationale <span className="optional">optional</span>
          <textarea
            rows={2}
            value={rationale}
            onChange={(event) => setRationale(event.target.value)}
            placeholder="What does this artifact support here?"
          />
        </label>
        <button className="small-button" type="submit">Map to this {targetKind}</button>
      </form>
    </section>
  );
}

function Workspace({
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
  const [recordId, setRecordId] = useState("");
  const [returnRecordId, setReturnRecordId] = useState("");
  const [detail, setDetail] = useState<RecordDetail | null>(null);
  const [selectedPromptId, setSelectedPromptId] = useState("");
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [search, setSearch] = useState("");
  const [area, setArea] = useState("all");
  const [saveState, setSaveState] = useState<"saved" | "saving" | "error">("saved");
  const [saveMessage, setSaveMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [creatingWorkspace, setCreatingWorkspace] = useState(false);
  const [view, setView] = useState<"assessment" | "overview">("assessment");

  const loadAssessment = useCallback(async () => {
    setLoading(true);
    const next = await request<Assessment>(`/api/projects/${projectId}/assessment`);
    setAssessment(next);
    setRecordId((current) => current || next.work_list[0]?.record_id || "");
    setLoading(false);
  }, [projectId]);

  const loadDetail = useCallback(async () => {
    if (!assessment || !recordId) return;
    const next = await request<RecordDetail>(
      `/api/assessments/${assessment.id}/records/${encodeURIComponent(recordId)}`,
    );
    setDetail(next);
  }, [assessment, recordId]);

  const loadArtifacts = useCallback(async () => {
    if (!assessment) return;
    setArtifacts(await request<Artifact[]>(`/api/projects/${assessment.project.id}/evidence`));
  }, [assessment]);

  const refreshAssessment = useCallback(async () => {
    setAssessment(await request<Assessment>(`/api/projects/${projectId}/assessment`));
  }, [projectId]);

  const refreshRecord = useCallback(async () => {
    await Promise.all([loadDetail(), refreshAssessment()]);
  }, [loadDetail, refreshAssessment]);

  useEffect(() => {
    setAssessment(null);
    setRecordId("");
    void loadAssessment();
  }, [loadAssessment]);

  useEffect(() => {
    void loadDetail();
  }, [loadDetail]);

  useEffect(() => {
    void loadArtifacts();
  }, [loadArtifacts]);

  useEffect(() => {
    if (!detail) return;
    if (selectedPromptId === "__record__") return;
    const questions = [...detail.prompts, ...detail.parent_prompts].filter(
      (prompt) => prompt.working_record,
    );
    if (!questions.some((prompt) => prompt.id === selectedPromptId)) {
      const firstRecordQuestion = detail.prompts.find((prompt) => prompt.working_record);
      setSelectedPromptId(firstRecordQuestion?.id ?? questions[0]?.id ?? "");
    }
  }, [detail, selectedPromptId]);

  function updateSaveState(state: "saving" | "saved" | "error", message = "") {
    setSaveState(state);
    setSaveMessage(message);
  }

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

  const selectedPrompt = detail
    ? [...detail.prompts, ...detail.parent_prompts].find(
        (prompt) => prompt.id === selectedPromptId && prompt.working_record,
      ) ?? null
    : null;

  if (loading || !assessment || !detail) {
    return <div className="loading-screen"><LoaderCircle className="spin" /><span>Opening assessment workspace…</span></div>;
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-brand">
          <div className="brand-mark small"><ShieldCheck size={20} /></div>
          <span>RainTech GRC</span>
        </div>
        <nav>
          <button className={view === "assessment" ? "active" : ""} onClick={() => setView("assessment")}>Assessments</button>
          <button className={view === "overview" ? "active" : ""} onClick={() => setView("overview")}>Overview</button>
          <button disabled>Profile</button>
          <button disabled>Actions</button>
        </nav>
        <div className="topbar-utility">
          <span className={`save-state ${saveState}`} title={saveMessage}>
            {saveState === "saving" && <LoaderCircle className="spin" size={14} />}
            {saveState === "saved" && <Cloud size={14} />}
            {saveState === "error" && <CircleAlert size={14} />}
            {saveState === "saving" ? "Saving…" : saveState === "error" ? saveMessage || "Not saved" : "Saved"}
          </span>
          <span className="account"><UserRound size={16} /> Johnathan</span>
        </div>
      </header>

      <aside className="rail">
        <div className="project-switcher">
          <p className="eyebrow">CLIENT PROJECT</p>
          <select value={projectId} onChange={(event) => onProjectChange(event.target.value)}>
            {projects.map((project) => (
              <option key={project.id} value={project.id}>{project.clientName} · {project.name}</option>
            ))}
          </select>
          <span>{assessment.framework.name}</span>
          <button className="add-workspace" onClick={() => setCreatingWorkspace(true)}>
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
              className={`record-row ${statusClass(record.determination?.status ?? "")} ${record.record_id === recordId ? "active" : ""}`}
              onClick={() => { setReturnRecordId(""); setSelectedPromptId(""); setRecordId(record.record_id); }}
            >
              <span className="record-number">{String(index + 1).padStart(3, "0")}</span>
              <span>
                <strong>{record.title}</strong>
                <small>{record.citation}</small>
                <StatusPill status={record.determination?.status ?? ""} />
              </span>
              {record.designation && <em>{record.designation}</em>}
            </button>
          ))}
        </div>
      </aside>

      <main className={`assessment-main ${view === "overview" ? "workspace-hidden" : ""}`}>
        <div className="record-toolbar">
          <div>
            {returnRecordId ? (
              <button className="back-link" onClick={() => { setSelectedPromptId(""); setRecordId(returnRecordId); setReturnRecordId(""); }}>
                <ArrowLeft size={15} /> Back to determination
              </button>
            ) : detail.position ? (
              <span className="position">{detail.position.current} of {detail.position.total}</span>
            ) : (
              <span className="position rollup-label">Rollup header · no editable status</span>
            )}
          </div>
          {detail.position && (
            <div className="previous-next">
              <button disabled={!detail.position.previous_record_id} onClick={() => { setSelectedPromptId(""); if (detail.position?.previous_record_id) setRecordId(detail.position.previous_record_id); }}>
                <ArrowLeft size={16} /> Previous
              </button>
              <button disabled={!detail.position.next_record_id} onClick={() => { setSelectedPromptId(""); if (detail.position?.next_record_id) setRecordId(detail.position.next_record_id); }}>
                Next <ArrowRight size={16} />
              </button>
            </div>
          )}
        </div>

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
                    {detail.parent_prompts.map((prompt) => (
                      <li key={prompt.id}>
                        {prompt.working_record ? (
                          <button
                            type="button"
                            className={selectedPromptId === prompt.id ? "selected" : ""}
                            onClick={() => setSelectedPromptId(prompt.id)}
                          >
                            <span>{prompt.text}</span>
                            <StatusPill status={prompt.working_record.status} />
                          </button>
                        ) : (
                          <span>{prompt.text}</span>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
                <p>Open the standard work to record answers, notes, and evidence.</p>
              </details>
            </div>
            <div className="parent-actions">
              <StatusPill status={detail.parent.determination?.status ?? ""} derived />
              <button className="text-button" onClick={() => { setReturnRecordId(recordId); setSelectedPromptId("__record__"); setRecordId(detail.parent!.record_id); }}>
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
          <button
            type="button"
            className="text-button record-notes-link"
            onClick={() => setSelectedPromptId("__record__")}
          >
            Open record notes & evidence
          </button>
        </section>

        {detail.context_prompts.length > 0 && (
          <details className="context-guidance">
            <summary>
              <BookOpen size={15} />
              Assessment context ({detail.context_prompts.length})
            </summary>
            <p>These questions were deliberately separated from a determination because no rule was identified for them.</p>
            <ul>
              {detail.context_prompts.map((prompt) => (
                <li key={prompt.id}>
                  <strong>{prompt.text}</strong>
                  {prompt.moved_from && <span>From {prompt.moved_from.citation}</span>}
                </li>
              ))}
            </ul>
          </details>
        )}

        <section className="prompt-section">
          <div className="content-heading">
            <div><p className="eyebrow">ASSESSOR GUIDANCE</p><h2>Questions to work through</h2></div>
            <span>{detail.prompts.length} question{detail.prompts.length === 1 ? "" : "s"}</span>
          </div>
          {detail.prompts.length === 0 ? (
            <div className="empty-panel"><BookOpen size={22} /><p>No guidance prompts are attached to this record. Assess the cited requirement directly.</p></div>
          ) : (
            <div className="prompt-list">
              {detail.prompts.map((prompt) => (
                <PromptCard
                  key={prompt.id}
                  prompt={prompt}
                  assessment={assessment}
                  selected={selectedPromptId === prompt.id}
                  onSelect={() => setSelectedPromptId(prompt.id)}
                  onChanged={() => void refreshRecord()}
                  onSaveState={updateSaveState}
                />
              ))}
            </div>
          )}
        </section>
      </main>

      <aside className={`working-record ${view === "overview" ? "workspace-hidden" : ""}`}>
        {selectedPrompt ? (
          <>
            <div className="working-header">
              <div><p className="eyebrow">WORKING RECORD</p><h2>Question record</h2></div>
              <ShieldCheck size={20} />
            </div>
            {selectedPrompt.record_id === detail.record.record_id && (
              <AddressableDecisionPanel
                assessmentId={assessment.id}
                detail={detail}
                onChanged={() => void refreshRecord()}
                onSaveState={updateSaveState}
              />
            )}
            <QuestionWorkingPanel
              assessmentId={assessment.id}
              statuses={assessment.framework.declarations.status_set}
              prompt={selectedPrompt}
              onChanged={() => void refreshRecord()}
              onSaveState={updateSaveState}
            />
            <EvidencePanel
              assessment={assessment}
              evidence={selectedPrompt.working_record!.evidence}
              targetKind="question"
              targetId={selectedPrompt.id}
              artifacts={artifacts}
              onChanged={() => void refreshRecord()}
              onArtifactsChanged={() => void loadArtifacts()}
              onSaveState={updateSaveState}
            />
          </>
        ) : (
          <>
            <div className="working-header">
              <div><p className="eyebrow">WORKING RECORD</p><h2>Record notes</h2></div>
              <ShieldCheck size={20} />
            </div>
            <DeterminationPanel
              assessmentId={assessment.id}
              statuses={assessment.framework.declarations.status_set}
              detail={detail}
              onChanged={() => void refreshRecord()}
              onSaveState={updateSaveState}
            />
            <section className="working-section">
              <div className="section-title"><div><p className="eyebrow">DISCUSSION</p><h3>Record notes</h3></div></div>
              <textarea
                key={`${detail.record.record_id}:${detail.note}`}
                defaultValue={detail.note}
                rows={5}
                placeholder="Record implementation details, scope, and assessor observations…"
                onBlur={async (event) => {
                  updateSaveState("saving");
                  try {
                    await request(`/api/assessments/${assessment.id}/records/${detail.record.record_id}/note`, {
                      method: "PUT",
                      body: JSON.stringify({ note: event.target.value }),
                    });
                    updateSaveState("saved");
                  } catch (caught) {
                    updateSaveState("error", caught instanceof Error ? caught.message : undefined);
                  }
                }}
              />
            </section>
            <EvidencePanel
              assessment={assessment}
              evidence={detail.evidence}
              targetKind="record"
              targetId={detail.record.record_id}
              artifacts={artifacts}
              onChanged={() => void refreshRecord()}
              onArtifactsChanged={() => void loadArtifacts()}
              onSaveState={updateSaveState}
            />
          </>
        )}
      </aside>
      {view === "overview" && (
        <main className="overview-panel">
          <div className="overview-heading">
            <div>
              <p className="eyebrow">PROJECT OVERVIEW</p>
              <h1>{assessment.project.client_name} · {assessment.project.name}</h1>
              <p>{assessment.framework.name} is pinned to {assessment.framework.id}.</p>
            </div>
            <button className="small-button" onClick={() => setView("assessment")}>
              Continue assessment <ArrowRight size={15} />
            </button>
          </div>
          <div className="overview-metrics">
            <article><strong>{assessment.framework.determination_record_count}</strong><span>determinations</span></article>
            <article><strong>{assessment.framework.record_count}</strong><span>cited records</span></article>
            <article><strong>{assessment.framework.prompt_count}</strong><span>assessor prompts</span></article>
          </div>
          <div className="overview-projects">
            <div className="section-title"><h2>Client projects</h2><span>{projects.length}</span></div>
            {projects.map((project) => (
              <button key={project.id} onClick={() => { onProjectChange(project.id); setView("assessment"); }}>
                <FolderKanban size={18} />
                <span><strong>{project.clientName}</strong><small>{project.name}</small></span>
                <ArrowRight size={16} />
              </button>
            ))}
          </div>
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
