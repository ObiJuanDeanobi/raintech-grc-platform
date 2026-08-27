import {
  CheckCircle2,
  FilePlus2,
  History,
  Link2,
  Plus,
  ShieldCheck,
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

import { ApiError, request } from "./api";
import type {
  Artifact,
  ProfileEvidenceMapping,
  ProfileItem,
  ProfileItemType,
  ProfileValue,
  ProfileVersion,
  ProjectProfile,
} from "./types";

const sections: {
  title: string;
  itemType: ProfileItemType | null;
  section: string;
  addLabel?: string;
}[] = [
  { title: "Project metadata", itemType: null, section: "project_metadata" },
  {
    title: "Environments & inventory",
    itemType: "environment",
    section: "environments",
    addLabel: "Add environment",
  },
  {
    title: "Business processes",
    itemType: "business_process",
    section: "business_processes",
    addLabel: "Add business process",
  },
  { title: "Locations", itemType: "location", section: "locations", addLabel: "Add location" },
  {
    title: "External services & vendors",
    itemType: "external_service",
    section: "external_services",
    addLabel: "Add external service",
  },
  {
    title: "People & roles",
    itemType: "person_role",
    section: "people_roles",
    addLabel: "Add person or role",
  },
  {
    title: "Exclusions & constraints",
    itemType: "exclusion_constraint",
    section: "exclusions_constraints",
    addLabel: "Add exclusion or constraint",
  },
  {
    title: "References",
    itemType: "reference",
    section: "references",
    addLabel: "Add reference",
  },
  {
    title: "Unknowns & follow-up",
    itemType: "unknown_follow_up",
    section: "unknowns_follow_up",
    addLabel: "Add unknown",
  },
];

function todayTimestamp(): string {
  return new Date().toISOString();
}

function emptyValue(section: string, fieldKey: string, label: string): ProfileValue {
  return {
    section,
    field_key: fieldKey,
    label,
    value: "",
    source: "Operator entry",
    reviewer: "Johnathan",
    last_reviewed_at: todayTimestamp(),
  };
}

function newItem(itemType: ProfileItemType, section: string): ProfileItem {
  const key = `${itemType}-${crypto.randomUUID()}`;
  const values = [emptyValue(section, "name", itemType === "unknown_follow_up" ? "Unknown" : "Name")];
  if (itemType === "environment") {
    values.push({
      ...emptyValue(section, "environment_type", "Environment type"),
      value: "cloud",
    });
  }
  if (itemType === "unknown_follow_up") {
    values.push(
      emptyValue(section, "owner", "Owner"),
      emptyValue(section, "target_date", "Target date"),
      emptyValue(section, "follow_up_reference", "Follow-up reference"),
    );
  }
  return {
    client_key: key,
    item_type: itemType,
    environment_item_id: null,
    environment_item_key: null,
    values,
  };
}

function FieldEditor({
  field,
  disabled,
  onChange,
}: {
  field: ProfileValue;
  disabled: boolean;
  onChange: (next: ProfileValue) => void;
}) {
  return (
    <div className="profile-value">
      <label>
        {field.label}
        {field.field_key === "environment_type" ? (
          <select
            disabled={disabled}
            value={field.value}
            onChange={(event) => onChange({ ...field, value: event.target.value })}
          >
            <option value="cloud">Cloud</option>
            <option value="physical">Physical systems</option>
            <option value="site">Site</option>
            <option value="network">Network</option>
          </select>
        ) : (
          <input
            disabled={disabled}
            type={field.field_key === "target_date" ? "date" : "text"}
            value={field.value}
            onChange={(event) => onChange({ ...field, value: event.target.value })}
          />
        )}
      </label>
      <div className="provenance-grid">
        <label>
          Source
          <input
            disabled={disabled}
            aria-label={`Source for ${field.label}`}
            value={field.source}
            onChange={(event) => onChange({ ...field, source: event.target.value })}
          />
        </label>
        <label>
          Reviewer
          <input
            disabled={disabled}
            aria-label={`Reviewer for ${field.label}`}
            value={field.reviewer}
            onChange={(event) => onChange({ ...field, reviewer: event.target.value })}
          />
        </label>
        <label>
          Last reviewed
          <input
            disabled={disabled}
            aria-label={`Last reviewed for ${field.label}`}
            type="datetime-local"
            value={field.last_reviewed_at.slice(0, 16)}
            onChange={(event) =>
              onChange({
                ...field,
                last_reviewed_at: new Date(event.target.value).toISOString(),
              })
            }
          />
        </label>
      </div>
    </div>
  );
}

export function ProfilePanel({
  projectId,
  onDirtyChange,
}: {
  projectId: string;
  onDirtyChange?: (dirty: boolean) => void;
}) {
  const [profile, setProfile] = useState<ProjectProfile | null>(null);
  const [selectedVersion, setSelectedVersion] = useState<ProfileVersion | null>(null);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [lifecycleWorking, setLifecycleWorking] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [reviewer, setReviewer] = useState("");
  const [reuseArtifactId, setReuseArtifactId] = useState("");
  const [reuseTarget, setReuseTarget] = useState("");
  const [reuseRationale, setReuseRationale] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadTarget, setUploadTarget] = useState("");
  const [uploadRationale, setUploadRationale] = useState("");
  const [dirty, setDirty] = useState(false);
  const requestSequence = useRef(0);
  const localEditRevision = useRef(0);

  useEffect(() => {
    const controller = new AbortController();
    const sequence = ++requestSequence.current;
    setLoading(true);
    setProfile(null);
    setSelectedVersion(null);
    setArtifacts([]);
    setError("");
    setMessage("");
    setWorking(false);
    setLifecycleWorking(false);
    setDirty(false);
    localEditRevision.current = 0;
    void Promise.all([
      request<ProjectProfile>(`/api/projects/${projectId}/profile`, {
        signal: controller.signal,
      }),
      request<Artifact[]>(`/api/projects/${projectId}/evidence`, {
        signal: controller.signal,
      }),
    ])
      .then(([loadedProfile, loadedArtifacts]) => {
        if (controller.signal.aborted || requestSequence.current !== sequence) return;
        setProfile(loadedProfile);
        setSelectedVersion(loadedProfile.versions[0] ?? null);
        setArtifacts(loadedArtifacts);
      })
      .catch((caught) => {
        if (!controller.signal.aborted && requestSequence.current === sequence) {
          setError(caught instanceof Error ? caught.message : "Profile could not be loaded.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted && requestSequence.current === sequence) setLoading(false);
      });
    return () => controller.abort();
  }, [projectId]);

  useEffect(() => {
    onDirtyChange?.(dirty || working);
  }, [dirty, onDirtyChange, working]);

  const profileTargets = useMemo(
    () => {
      const targets = [
        ...(selectedVersion?.values ?? []).map((field) => ({
          key: field.target_key ?? `field:${field.section}:${field.field_key}`,
          label: `Project metadata · ${field.label}`,
        })),
        ...(selectedVersion?.items ?? []).flatMap((item) =>
          item.values.map((field) => ({
            key: field.target_key ?? `item:${item.client_key}:${field.field_key}`,
            label: `${item.item_type.replaceAll("_", " ")} · ${field.label}`,
          }))
        ),
      ];
      return [...new Map(targets.map((target) => [target.key, target])).values()];
    },
    [selectedVersion],
  );

  function replaceVersion(next: ProfileVersion) {
    setSelectedVersion(next);
    setProfile((current) =>
      current
        ? {
            ...current,
            versions: current.versions.some((item) => item.id === next.id)
              ? current.versions.map((item) => (item.id === next.id ? next : item))
              : [next, ...current.versions],
          }
        : current,
    );
  }

  function mergeVersion(
    versionId: string,
    updater: (current: ProfileVersion) => ProfileVersion,
  ) {
    setSelectedVersion((current) =>
      current?.id === versionId ? updater(current) : current
    );
    setProfile((current) =>
      current
        ? {
            ...current,
            versions: current.versions.map((item) =>
              item.id === versionId ? updater(item) : item
            ),
          }
        : current
    );
  }

  async function reloadVersionAfterConflict(
    targetProjectId: string,
    targetVersionId: string,
    generation: number,
  ) {
    const current = await request<ProfileVersion>(
      `/api/projects/${targetProjectId}/profile/versions/${targetVersionId}`,
    );
    if (
      requestSequence.current !== generation
      || targetProjectId !== projectId
      || selectedVersion?.id !== targetVersionId
    ) return;
    replaceVersion(current);
    setDirty(false);
  }

  function updateTopValue(index: number, next: ProfileValue) {
    if (!selectedVersion) return;
    replaceVersion({
      ...selectedVersion,
      values: selectedVersion.values.map((field, fieldIndex) =>
        fieldIndex === index ? next : field
      ),
    });
    localEditRevision.current += 1;
    setDirty(true);
  }

  function updateItem(itemKey: string, updater: (item: ProfileItem) => ProfileItem) {
    if (!selectedVersion) return;
    replaceVersion({
      ...selectedVersion,
      items: selectedVersion.items.map((item) =>
        item.client_key === itemKey ? updater(item) : item
      ),
    });
    localEditRevision.current += 1;
    setDirty(true);
  }

  function addItem(itemType: ProfileItemType, section: string) {
    if (!selectedVersion) return;
    const item = newItem(itemType, section);
    if (itemType === "scope_item") {
      const firstEnvironment = selectedVersion.items.find(
        (candidate) => candidate.item_type === "environment"
      );
      if (!firstEnvironment) {
        setError("Add an environment before adding inventory.");
        return;
      }
      item.environment_item_key = firstEnvironment.client_key;
    }
    replaceVersion({
      ...selectedVersion,
      items: [...selectedVersion.items, item],
    });
    localEditRevision.current += 1;
    setDirty(true);
  }

  async function saveDraft() {
    if (!selectedVersion) return;
    const generation = requestSequence.current;
    const targetProjectId = projectId;
    const targetVersionId = selectedVersion.id;
    const submittedLocalRevision = localEditRevision.current;
    setWorking(true);
    setMessage("");
    setError("");
    try {
      const environmentKeyById = new Map(
        selectedVersion.items
          .filter((item) => item.item_type === "environment" && item.id)
          .map((item) => [item.id!, item.client_key]),
      );
      const saved = await request<ProfileVersion>(
        `/api/projects/${projectId}/profile/versions/${selectedVersion.id}`,
        {
          method: "PUT",
          body: JSON.stringify({
            expected_revision: selectedVersion.content_revision,
            values: selectedVersion.values,
            items: selectedVersion.items.map((item) => ({
              client_key: item.client_key,
              item_type: item.item_type,
              environment_item_key:
                item.environment_item_key
                ?? (item.environment_item_id
                  ? environmentKeyById.get(item.environment_item_id) ?? null
                  : null),
              values: item.values,
            })),
          }),
        },
      );
      if (
        requestSequence.current !== generation
        || targetProjectId !== projectId
        || targetVersionId !== selectedVersion.id
      ) return;
      if (localEditRevision.current === submittedLocalRevision) {
        replaceVersion(saved);
        setDirty(false);
        setMessage("Draft saved with provenance.");
      } else {
        setSelectedVersion((current) =>
          current?.id === targetVersionId
            ? { ...current, content_revision: saved.content_revision }
            : current
        );
        setProfile((current) =>
          current
            ? {
                ...current,
                versions: current.versions.map((item) =>
                  item.id === targetVersionId
                    ? { ...item, content_revision: saved.content_revision }
                    : item
                ),
              }
            : current
        );
        setDirty(true);
        setMessage("Earlier edits saved; newer Profile edits remain unsaved.");
      }
    } catch (caught) {
      if (requestSequence.current === generation && targetProjectId === projectId) {
        if (caught instanceof ApiError && caught.status === 409) {
          try {
            await reloadVersionAfterConflict(targetProjectId, targetVersionId, generation);
            setError(`${caught.message} The displayed version was reloaded.`);
          } catch {
            setError(`${caught.message} Reload the Profile before continuing.`);
          }
        } else {
          setError(caught instanceof Error ? caught.message : "Profile draft could not be saved.");
        }
      }
    } finally {
      if (requestSequence.current === generation && targetProjectId === projectId) setWorking(false);
    }
  }

  async function lifecycle(status: "Reviewed" | "Approved") {
    if (!selectedVersion) return;
    if (dirty) {
      setError("Save the displayed Profile draft before recording review.");
      return;
    }
    const generation = requestSequence.current;
    const targetProjectId = projectId;
    const targetVersionId = selectedVersion.id;
    const submittedLocalRevision = localEditRevision.current;
    setWorking(true);
    setLifecycleWorking(true);
    setError("");
    try {
      const result = await request<{
        active_version_id: string | null;
        version: ProfileVersion;
      }>(
        `/api/projects/${projectId}/profile/versions/${selectedVersion.id}/lifecycle`,
        {
          method: "POST",
          body: JSON.stringify({
            status,
            reviewer,
            expected_revision: selectedVersion.content_revision,
          }),
        },
      );
      if (
        requestSequence.current !== generation
        || targetProjectId !== projectId
        || targetVersionId !== selectedVersion.id
      ) return;
      if (localEditRevision.current === submittedLocalRevision) {
        replaceVersion(result.version);
      } else {
        setDirty(true);
        setError(
          "Lifecycle recorded against the earlier saved snapshot. "
          + "Newer local edits were not reviewed; reload and review again."
        );
      }
      setProfile((current) =>
        current ? { ...current, active_version_id: result.active_version_id } : current
      );
      setMessage(status === "Reviewed" ? `Reviewed by ${reviewer}` : "Version approved.");
    } catch (caught) {
      if (requestSequence.current === generation && targetProjectId === projectId) {
        if (caught instanceof ApiError && caught.status === 409) {
          try {
            await reloadVersionAfterConflict(targetProjectId, targetVersionId, generation);
            setError(`${caught.message} The displayed version was reloaded; review it again.`);
          } catch {
            setError(`${caught.message} Reload the Profile and review it again.`);
          }
        } else {
          setError(caught instanceof Error ? caught.message : "Lifecycle update failed.");
        }
      }
    } finally {
      if (requestSequence.current === generation && targetProjectId === projectId) {
        setWorking(false);
        setLifecycleWorking(false);
      }
    }
  }

  async function createVersion() {
    if (!selectedVersion) return;
    const generation = requestSequence.current;
    const targetProjectId = projectId;
    const targetVersionId = selectedVersion.id;
    setWorking(true);
    setError("");
    try {
      const next = await request<ProfileVersion>(
        `/api/projects/${projectId}/profile/versions`,
        {
          method: "POST",
          body: JSON.stringify({ base_version_id: selectedVersion.id }),
        },
      );
      if (
        requestSequence.current !== generation
        || targetProjectId !== projectId
        || targetVersionId !== selectedVersion.id
      ) return;
      replaceVersion(next);
      setMessage(`Version ${next.version_number} created as a new draft.`);
    } catch (caught) {
      if (requestSequence.current === generation && targetProjectId === projectId) {
        setError(caught instanceof Error ? caught.message : "New version could not be created.");
      }
    } finally {
      if (requestSequence.current === generation && targetProjectId === projectId) setWorking(false);
    }
  }

  async function mapExisting(event: FormEvent) {
    event.preventDefault();
    if (!selectedVersion) return;
    const artifact = artifacts.find((item) => item.id === reuseArtifactId);
    if (!artifact) return;
    const generation = requestSequence.current;
    const targetProjectId = projectId;
    const targetVersionId = selectedVersion.id;
    const submittedLocalRevision = localEditRevision.current;
    setWorking(true);
    setError("");
    try {
      const mapping = await request<ProfileEvidenceMapping>(
        `/api/projects/${projectId}/profile/versions/${selectedVersion.id}/evidence-mappings`,
        {
          method: "POST",
          body: JSON.stringify({
            expected_revision: selectedVersion.content_revision,
            artifact_id: artifact.id,
            evidence_version_id: artifact.version_id,
            target_key: reuseTarget,
            rationale: reuseRationale,
          }),
        },
      );
      if (
        requestSequence.current !== generation
        || targetProjectId !== projectId
        || targetVersionId !== selectedVersion.id
      ) return;
      mergeVersion(targetVersionId, (current) => ({
        ...current,
        content_revision: mapping.content_revision ?? current.content_revision,
        evidence: current.evidence.some(
          (candidate) => candidate.mapping_id === mapping.mapping_id
        )
          ? current.evidence
          : [...current.evidence, mapping],
      }));
      if (localEditRevision.current !== submittedLocalRevision) setDirty(true);
      setReuseRationale("");
      setMessage("Existing immutable evidence version mapped.");
    } catch (caught) {
      if (requestSequence.current === generation && targetProjectId === projectId) {
        if (caught instanceof ApiError && caught.status === 409) {
          try {
            await reloadVersionAfterConflict(targetProjectId, targetVersionId, generation);
            setError(`${caught.message} The displayed version was reloaded; review it again.`);
          } catch {
            setError(`${caught.message} Reload the Profile and review it again.`);
          }
        } else {
          setError(caught instanceof Error ? caught.message : "Evidence could not be mapped.");
        }
      }
    } finally {
      if (requestSequence.current === generation && targetProjectId === projectId) setWorking(false);
    }
  }

  async function uploadAndMap(event: FormEvent) {
    event.preventDefault();
    if (!selectedVersion || !uploadFile) return;
    const generation = requestSequence.current;
    const targetProjectId = projectId;
    const targetVersionId = selectedVersion.id;
    const submittedLocalRevision = localEditRevision.current;
    const form = new FormData();
    form.append("file", uploadFile);
    form.append("target_key", uploadTarget);
    form.append("rationale", uploadRationale);
    form.append("expected_revision", selectedVersion.content_revision);
    setWorking(true);
    setError("");
    try {
      const result = await request<{
        artifact: Artifact & { version: { id: string; version_number: number; sha256: string } };
        mapping: ProfileEvidenceMapping;
        content_revision: string;
      }>(`/api/projects/${projectId}/profile/versions/${selectedVersion.id}/evidence`, {
        method: "POST",
        body: form,
      });
      if (
        requestSequence.current !== generation
        || targetProjectId !== projectId
        || targetVersionId !== selectedVersion.id
      ) return;
      mergeVersion(targetVersionId, (current) => ({
        ...current,
        content_revision: result.content_revision,
        evidence: current.evidence.some(
          (candidate) => candidate.mapping_id === result.mapping.mapping_id
        )
          ? current.evidence
          : [...current.evidence, result.mapping],
      }));
      setArtifacts((current) =>
        current.some((candidate) => candidate.id === result.artifact.id)
          ? current
          : [...current, result.artifact]
      );
      if (localEditRevision.current !== submittedLocalRevision) setDirty(true);
      setUploadFile(null);
      setUploadRationale("");
      setMessage("Sanitized file stored, hashed, and mapped.");
    } catch (caught) {
      if (requestSequence.current === generation && targetProjectId === projectId) {
        if (caught instanceof ApiError && caught.status === 409) {
          try {
            await reloadVersionAfterConflict(targetProjectId, targetVersionId, generation);
            setError(`${caught.message} The displayed version was reloaded; review it again.`);
          } catch {
            setError(`${caught.message} Reload the Profile and review it again.`);
          }
        } else {
          setError(caught instanceof Error ? caught.message : "Upload could not be mapped.");
        }
      }
    } finally {
      if (requestSequence.current === generation && targetProjectId === projectId) setWorking(false);
    }
  }

  if (loading) return <div className="profile-loading">Opening project Profile…</div>;
  if (error && !profile) return <p className="form-error" role="alert">{error}</p>;
  if (!profile || !selectedVersion) return <p className="form-error">No Profile version exists.</p>;

  const editable = selectedVersion.status === "Draft" && !lifecycleWorking;
  const environmentItems = selectedVersion.items.filter((item) => item.item_type === "environment");
  const inventoryItems = selectedVersion.items.filter((item) => item.item_type === "scope_item");

  return (
    <section className="profile-workspace" aria-labelledby="profile-title">
      <header className="profile-heading">
        <div>
          <p className="eyebrow">PROJECT DELIVERY SOURCE</p>
          <h1 id="profile-title">Versioned project profile</h1>
          <p>
            Descriptive scope metadata only. CUI, PHI, and ePHI remain excluded upstream and
            must not be entered into Profile fields or supporting files.
          </p>
        </div>
        <div className="profile-version-picker">
          <label>
            Profile version
            <select
              disabled={lifecycleWorking}
              value={selectedVersion.id}
              onChange={(event) => {
                if (
                  dirty
                  && !window.confirm(
                    "This Profile version has unsaved changes. Switch versions and discard them?"
                  )
                ) return;
                const next = profile.versions.find((item) => item.id === event.target.value);
                if (next) {
                  requestSequence.current += 1;
                  setWorking(false);
                  setSelectedVersion(next);
                  localEditRevision.current = 0;
                  setDirty(false);
                }
              }}
            >
              {profile.versions.map((item) => (
                <option key={item.id} value={item.id}>
                  Version {item.version_number} · {item.status}
                </option>
              ))}
            </select>
          </label>
          <span className={`profile-status ${selectedVersion.status.toLowerCase()}`}>
            Version {selectedVersion.version_number} · {selectedVersion.status}
          </span>
          {profile.active_version_id === selectedVersion.id && (
            <span className="active-snapshot"><CheckCircle2 size={14} /> Active approved snapshot</span>
          )}
        </div>
      </header>

      <div className="template-gate">
        <ShieldCheck size={18} />
        <div><strong>Neutral form · no released template</strong><p>{profile.template.message}</p></div>
      </div>

      <div className="profile-lifecycle">
        <div>
          <History size={18} />
          <div>
            <strong>Append-only lifecycle</strong>
            <span>
              {selectedVersion.lifecycle.map((event) => event.status).join(" → ")}
            </span>
          </div>
        </div>
        <label>
          Lifecycle reviewer
          <input value={reviewer} onChange={(event) => setReviewer(event.target.value)} />
        </label>
        {selectedVersion.status === "Draft" && (
          <button
            className="secondary-button"
            disabled={working || dirty}
            onClick={() => void lifecycle("Reviewed")}
          >
            Record review
          </button>
        )}
        {selectedVersion.status === "Reviewed" && (
          <button
            className="small-button"
            disabled={working || !reviewer.trim()}
            onClick={() => void lifecycle("Approved")}
          >
            Approve version
          </button>
        )}
        {selectedVersion.status === "Approved" && (
          <button className="small-button" disabled={working} onClick={() => void createVersion()}>
            Create new version
          </button>
        )}
      </div>
      {dirty && (
        <p className="profile-unsaved" role="status">
          Unsaved Profile changes must be saved before review or navigation.
        </p>
      )}

      <div className="profile-sections">
        {sections.map((section) => {
          let items = section.itemType
            ? selectedVersion.items.filter((item) => item.item_type === section.itemType)
            : [];
          if (section.itemType === "environment") items = environmentItems;
          return (
            <section className="profile-section" key={section.title}>
              <div className="section-title">
                <h2>{section.title}</h2>
                {editable && section.itemType && (
                  <button
                    className="text-button"
                    onClick={() => addItem(section.itemType!, section.section)}
                  >
                    <Plus size={14} /> {section.addLabel}
                  </button>
                )}
              </div>
              {section.itemType === "unknown_follow_up" && (
                <p className="profile-section-help">
                  Each unknown requires an owner and target date or an explicit follow-up reference.
                </p>
              )}
              {!section.itemType && selectedVersion.values.map((field, index) => (
                <FieldEditor
                  key={field.id ?? `${field.field_key}-${index}`}
                  field={field}
                  disabled={!editable}
                  onChange={(next) => updateTopValue(index, next)}
                />
              ))}
              {items.map((item) => (
                <article className="profile-item-card" key={item.client_key}>
                  {item.values.map((field, index) => (
                    <FieldEditor
                      key={field.id ?? `${field.field_key}-${index}`}
                      field={field}
                      disabled={!editable}
                      onChange={(next) =>
                        updateItem(item.client_key, (current) => ({
                          ...current,
                          values: current.values.map((value, valueIndex) =>
                            valueIndex === index ? next : value
                          ),
                        }))
                      }
                    />
                  ))}
                  {section.itemType === "environment" && (
                    <div className="nested-inventory">
                      <h3>Inventory in this environment</h3>
                      {inventoryItems
                        .filter((inventory) =>
                          inventory.environment_item_key === item.client_key
                          || inventory.environment_item_id === item.id
                        )
                        .map((inventory) => (
                          <article
                            className="profile-item-card inventory"
                            key={inventory.client_key}
                          >
                            {editable && (
                              <label>
                                Environment
                                <select
                                  value={
                                    inventory.environment_item_key
                                    ?? environmentItems.find(
                                      (environment) =>
                                        environment.id === inventory.environment_item_id,
                                    )?.client_key
                                  }
                                  onChange={(event) =>
                                    updateItem(inventory.client_key, (current) => ({
                                      ...current,
                                      environment_item_key: event.target.value,
                                      environment_item_id: null,
                                    }))
                                  }
                                >
                                  {environmentItems.map((environment) => (
                                    <option
                                      key={environment.client_key}
                                      value={environment.client_key}
                                    >
                                      {environment.values.find(
                                        (field) => field.field_key === "name"
                                      )?.value || "Unnamed environment"}
                                    </option>
                                  ))}
                                </select>
                              </label>
                            )}
                            {inventory.values.map((field, index) => (
                              <FieldEditor
                                key={field.id ?? `${field.field_key}-${index}`}
                                field={field}
                                disabled={!editable}
                                onChange={(next) =>
                                  updateItem(inventory.client_key, (current) => ({
                                    ...current,
                                    values: current.values.map((value, valueIndex) =>
                                      valueIndex === index ? next : value
                                    ),
                                  }))
                                }
                              />
                            ))}
                          </article>
                        ))}
                    </div>
                  )}
                </article>
              ))}
              {section.itemType === "environment" && (
                <div className="inventory-group">
                  <div className="section-title">
                    <h3>Inventory grouped by environment</h3>
                    {editable && (
                      <button
                        className="text-button"
                        onClick={() => addItem("scope_item", "scope_items")}
                      >
                        <Plus size={14} /> Add inventory / scope item
                      </button>
                    )}
                  </div>
                </div>
              )}
            </section>
          );
        })}
      </div>

      {editable && (
        <div className="profile-save-row">
          <button className="small-button" disabled={working} onClick={() => void saveDraft()}>
            Save draft
          </button>
          <span>Every value retains source, reviewer, and last-reviewed timestamp.</span>
        </div>
      )}

      <section className="profile-evidence">
        <div className="section-title">
          <div><p className="eyebrow">SUPPORTING FILES</p><h2>Profile evidence mappings</h2></div>
          <span>Initial state: Not reviewed</span>
        </div>
        <div className="profile-evidence-list">
          {selectedVersion.evidence.map((mapping) => (
            <article key={mapping.mapping_id}>
              <FilePlus2 size={17} />
              <div>
                <strong>{mapping.name}</strong>
                <span>{mapping.target_key} · {mapping.rationale}</span>
              </div>
              <div>
                <span>{mapping.review_state}</span>
                <code>{mapping.sha256}</code>
                <small>Version {mapping.version_number} · SHA-256</small>
              </div>
            </article>
          ))}
        </div>
        {editable && (
          <div className="profile-evidence-actions">
            <form onSubmit={(event) => void mapExisting(event)}>
              <h3><Link2 size={16} /> Reuse same-project evidence</h3>
              <label>
                Immutable evidence version
                <select
                  required
                  value={reuseArtifactId}
                  onChange={(event) => setReuseArtifactId(event.target.value)}
                >
                  <option value="">Select evidence</option>
                  {artifacts.map((artifact) => (
                    <option key={artifact.id} value={artifact.id}>{artifact.name}</option>
                  ))}
                </select>
              </label>
              {artifacts.map((artifact) => (
                <p key={artifact.id} className={artifact.id === reuseArtifactId ? "" : "sr-only"}>
                  {artifact.name} · Version {artifact.version_number} · {artifact.sha256}
                </p>
              ))}
              <label>
                Reuse target
                <select
                  required
                  value={reuseTarget}
                  onChange={(event) => setReuseTarget(event.target.value)}
                >
                  <option value="">Select Profile field</option>
                  {profileTargets.map((target) => (
                    <option key={target.key} value={target.key}>{target.label}</option>
                  ))}
                </select>
              </label>
              <label>
                Reuse rationale
                <textarea required value={reuseRationale} onChange={(event) => setReuseRationale(event.target.value)} />
              </label>
              <button className="secondary-button" disabled={working} type="submit">
                Map existing version
              </button>
            </form>
            <form onSubmit={(event) => void uploadAndMap(event)}>
              <h3><FilePlus2 size={16} /> New sanitized file</h3>
              <label>
                New sanitized Profile file
                <input
                  type="file"
                  onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
                />
              </label>
              <label>
                Upload target
                <select
                  required
                  value={uploadTarget}
                  onChange={(event) => setUploadTarget(event.target.value)}
                >
                  <option value="">Select Profile field</option>
                  {profileTargets.map((target) => (
                    <option key={target.key} value={target.key}>{target.label}</option>
                  ))}
                </select>
              </label>
              <label>
                Upload rationale
                <textarea required value={uploadRationale} onChange={(event) => setUploadRationale(event.target.value)} />
              </label>
              <button className="secondary-button" disabled={working} type="submit">
                Upload and map
              </button>
            </form>
          </div>
        )}
      </section>

      {message && <p className="profile-message" aria-live="polite">{message}</p>}
      {error && <p className="form-error" role="alert">{error}</p>}
    </section>
  );
}
