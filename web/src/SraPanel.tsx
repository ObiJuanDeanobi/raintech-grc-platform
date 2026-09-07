import { Check, CircleAlert, LoaderCircle, ShieldCheck } from "lucide-react";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { request } from "./api";
import type { SraRisk, SraScopeItem, SraWorkspace } from "./types";

type RiskDraft = Omit<
  SraRisk,
  "id" | "inherent" | "residual" | "evidence_links" | "profile_version_id" | "assessment_id"
>;

function newRisk(): RiskDraft {
  const timestamp = new Date().toISOString();
  return {
    title: "",
    threat: "",
    vulnerability: "",
    cia_impact: "",
    safeguards: "",
    corrective_action: "",
    inherent_likelihood: 1,
    inherent_impact: 1,
    residual_likelihood: 1,
    residual_impact: 1,
    treatment: "corrective_action",
    owner: "",
    status: "Open",
    acceptance_rationale: "",
    approver: "",
    approved_at: null,
    review_date: null,
    reviewed_by: "Johnathan",
    reviewed_at: timestamp,
  };
}

function riskBand(score: number): string {
  if (score <= 4) return "Low";
  if (score <= 9) return "Moderate";
  if (score <= 16) return "High";
  return "Critical";
}

function toRiskDraft(item: SraRisk): RiskDraft {
  return {
    title: item.title,
    threat: item.threat,
    vulnerability: item.vulnerability,
    cia_impact: item.cia_impact,
    safeguards: item.safeguards,
    corrective_action: item.corrective_action,
    inherent_likelihood: item.inherent_likelihood,
    inherent_impact: item.inherent_impact,
    residual_likelihood: item.residual_likelihood,
    residual_impact: item.residual_impact,
    treatment: item.treatment,
    owner: item.owner,
    status: item.status,
    acceptance_rationale: item.acceptance_rationale,
    approver: item.approver,
    approved_at: item.approved_at,
    review_date: item.review_date,
    reviewed_by: item.reviewed_by,
    reviewed_at: item.reviewed_at,
  };
}

export function SraPanel({
  projectId,
  onDirtyChange,
}: {
  projectId: string;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const [data, setData] = useState<SraWorkspace | null>(null);
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const [risk, setRisk] = useState<RiskDraft>(newRisk);
  const [editing, setEditing] = useState<string | null>(null);
  const [exclusions, setExclusions] = useState<Record<string, string>>({});
  const projectRef = useRef(projectId);
  projectRef.current = projectId;

  function markDirty(value: boolean) {
    onDirtyChange(value);
  }

  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setError("");
    setRisk(newRisk());
    setEditing(null);
    onDirtyChange(false);
    void request<SraWorkspace>(`/api/projects/${projectId}/sra`, {
      signal: controller.signal,
    })
      .then((next) => {
        setData(next);
        setExclusions(
          Object.fromEntries(
            next.scope_items.map((item) => [item.target_key, item.exclusion_rationale]),
          ),
        );
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : "SRA could not be loaded.");
        }
      });
    return () => controller.abort();
  }, [onDirtyChange, projectId]);

  async function refresh(expectedProjectId: string) {
    const next = await request<SraWorkspace>(
      `/api/projects/${expectedProjectId}/sra`,
    );
    if (projectRef.current === expectedProjectId) setData(next);
  }

  async function saveScope(item: SraScopeItem, included: boolean) {
    if (!data) return;
    const rationale = included ? "" : (exclusions[item.target_key] ?? "").trim();
    if (!included && !rationale) {
      setError("Exclusion requires a rationale.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await request(`/api/projects/${projectId}/sra/scope`, {
        method: "PUT",
        body: JSON.stringify({
          profile_version_id: data.profile_version_id,
          scope_type: item.scope_type,
          target_key: item.target_key,
          included,
          exclusion_rationale: rationale,
          reviewed_by: "Johnathan",
        }),
      });
      await refresh(projectId);
      if (projectRef.current === projectId) markDirty(false);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Scope update failed.");
    } finally {
      setSaving(false);
    }
  }

  async function submitRisk(event: FormEvent) {
    event.preventDefault();
    if (!data?.assessment_id) {
      setError("Start an assessment before recording SRA risks.");
      return;
    }
    setSaving(true);
    setError("");
    try {
      const url = editing
        ? `/api/projects/${projectId}/risks/${editing}`
        : `/api/projects/${projectId}/risks`;
      await request(url, {
        method: editing ? "PUT" : "POST",
        body: JSON.stringify({
          ...risk,
          profile_version_id: data.profile_version_id,
          assessment_id: data.assessment_id,
          reviewed_at: new Date().toISOString(),
        }),
      });
      await refresh(projectId);
      if (projectRef.current === projectId) {
        setRisk(newRisk());
        setEditing(null);
        markDirty(false);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Risk could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  const inherentScore = useMemo(
    () => risk.inherent_likelihood * risk.inherent_impact,
    [risk.inherent_impact, risk.inherent_likelihood],
  );
  const residualScore = useMemo(
    () => risk.residual_likelihood * risk.residual_impact,
    [risk.residual_impact, risk.residual_likelihood],
  );

  if (error && !data) {
    return <p className="error-copy"><CircleAlert size={14} /> {error}</p>;
  }
  if (!data) {
    return <div className="loading-screen"><LoaderCircle className="spin" /> Loading SRA…</div>;
  }

  return (
    <main className="overview-panel sra-panel" aria-labelledby="sra-title">
      <div className="overview-heading">
        <div>
          <p className="eyebrow">HIPAA WORK AREA</p>
          <h1 id="sra-title">{data.work_area}</h1>
          <p>{data.anchor.citation} · {data.anchor.title}</p>
        </div>
        <span className="readiness-state compact">{data.status}</span>
      </div>

      {error && <p className="error-copy"><CircleAlert size={14} /> {error}</p>}
      <section className="overview-readiness">
        <div><p className="eyebrow">COMPLETION</p><h2>{data.completion.percentage}% complete</h2></div>
        {data.completion.complete ? (
          <p className="readiness-ok"><Check size={15} /> Scope and risks are complete.</p>
        ) : (
          <ul className="blocking-reasons">
            {data.completion.missing.map((item) => <li key={item}>{item}</li>)}
          </ul>
        )}
      </section>

      <section className="working-section">
        <div className="section-title"><h2>Scope coverage</h2><span>{data.scope_items.length} facts</span></div>
        <p className="muted">Review every approved-Profile system, location, vendor, and flow. Exclusions require rationale.</p>
        <div className="sra-scope-list">
          {data.scope_items.map((item) => (
            <article key={`${item.scope_type}:${item.target_key}`}>
              <div><strong>{item.name}</strong><small>{item.scope_type}</small></div>
              <div className="scope-actions">
                <button disabled={saving} className="text-button" onClick={() => void saveScope(item, true)}>Include</button>
                <button disabled={saving} className="text-button" onClick={() => void saveScope(item, false)}>Exclude</button>
              </div>
              <label>
                Exclusion rationale
                <textarea
                  rows={2}
                  value={exclusions[item.target_key] ?? ""}
                  onChange={(event) => {
                    setExclusions({ ...exclusions, [item.target_key]: event.target.value });
                    markDirty(true);
                  }}
                />
              </label>
              <p className={item.included === null ? "muted" : "readiness-ok"}>
                {item.included === null ? "Not reviewed" : item.included ? "Included" : "Excluded with rationale"}
              </p>
            </article>
          ))}
        </div>
      </section>

      <section className="working-section">
        <div className="section-title"><h2>Risk register</h2><span>{data.risks.length} risks</span></div>
        {data.risks.map((item) => (
          <article className="sra-risk" key={item.id}>
            <div>
              <strong>{item.title}</strong>
              <p>{item.threat} · {item.vulnerability}</p>
              <small>Inherent {item.inherent.score} {item.inherent.band} · Residual {item.residual.score} {item.residual.band} · {item.owner}</small>
            </div>
            <button className="text-button" onClick={() => {
              setRisk(toRiskDraft(item));
              setEditing(item.id);
              markDirty(true);
            }}>Edit</button>
          </article>
        ))}

        <form className="sra-risk-form" onSubmit={(event) => void submitRisk(event)}>
          <h3>{editing ? "Edit risk" : "Add risk"}</h3>
          <label>Risk title<input required value={risk.title} onChange={(event) => { setRisk({ ...risk, title: event.target.value }); markDirty(true); }} /></label>
          <div className="sra-two-columns">
            <label>Threat<textarea required rows={2} value={risk.threat} onChange={(event) => { setRisk({ ...risk, threat: event.target.value }); markDirty(true); }} /></label>
            <label>Vulnerability<textarea required rows={2} value={risk.vulnerability} onChange={(event) => { setRisk({ ...risk, vulnerability: event.target.value }); markDirty(true); }} /></label>
            <label>CIA impact<textarea required rows={2} value={risk.cia_impact} onChange={(event) => { setRisk({ ...risk, cia_impact: event.target.value }); markDirty(true); }} /></label>
            <label>Existing safeguards<textarea required rows={2} value={risk.safeguards} onChange={(event) => { setRisk({ ...risk, safeguards: event.target.value }); markDirty(true); }} /></label>
          </div>
          <div className="readiness-fields">
            <label>Inherent likelihood<input aria-label="Inherent likelihood" type="number" min="1" max="5" value={risk.inherent_likelihood} onChange={(event) => setRisk({ ...risk, inherent_likelihood: Number(event.target.value) })} /></label>
            <label>Inherent impact<input aria-label="Inherent impact" type="number" min="1" max="5" value={risk.inherent_impact} onChange={(event) => setRisk({ ...risk, inherent_impact: Number(event.target.value) })} /></label>
            <label>Residual likelihood<input aria-label="Residual likelihood" type="number" min="1" max="5" value={risk.residual_likelihood} onChange={(event) => setRisk({ ...risk, residual_likelihood: Number(event.target.value) })} /></label>
            <label>Residual impact<input aria-label="Residual impact" type="number" min="1" max="5" value={risk.residual_impact} onChange={(event) => setRisk({ ...risk, residual_impact: Number(event.target.value) })} /></label>
          </div>
          <p className="risk-score">Inherent: <strong>{inherentScore} {riskBand(inherentScore)}</strong> · Residual: <strong>{residualScore} {riskBand(residualScore)}</strong></p>
          <div className="sra-two-columns">
            <label>Owner<input required value={risk.owner} onChange={(event) => setRisk({ ...risk, owner: event.target.value })} /></label>
            <label>Status<input required value={risk.status} onChange={(event) => setRisk({ ...risk, status: event.target.value })} /></label>
            <label>Treatment<select value={risk.treatment} onChange={(event) => setRisk({ ...risk, treatment: event.target.value as RiskDraft["treatment"] })}><option value="corrective_action">Corrective action</option><option value="acceptance">Risk acceptance</option></select></label>
            <label>Review date<input type="date" value={risk.review_date ?? ""} onChange={(event) => setRisk({ ...risk, review_date: event.target.value || null })} /></label>
          </div>
          <label>Corrective action<textarea rows={2} value={risk.corrective_action} onChange={(event) => setRisk({ ...risk, corrective_action: event.target.value })} /></label>
          {risk.treatment === "acceptance" && <label>Acceptance rationale<textarea required rows={2} value={risk.acceptance_rationale} onChange={(event) => setRisk({ ...risk, acceptance_rationale: event.target.value })} /></label>}
          {risk.treatment === "acceptance" && (inherentScore >= 10 || residualScore >= 10) && <div className="sra-two-columns"><label>Human approver<input required value={risk.approver} onChange={(event) => setRisk({ ...risk, approver: event.target.value })} /></label><label>Approval timestamp<input required type="datetime-local" value={risk.approved_at?.slice(0, 16) ?? ""} onChange={(event) => setRisk({ ...risk, approved_at: event.target.value ? new Date(event.target.value).toISOString() : null })} /></label></div>}
          <button className="small-button" disabled={saving || !data.assessment_id}><ShieldCheck size={15} /> {saving ? "Saving…" : "Save risk"}</button>
        </form>
      </section>
    </main>
  );
}
