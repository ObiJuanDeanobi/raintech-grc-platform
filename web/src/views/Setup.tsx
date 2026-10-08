import {
  ArrowRight,
  BookOpen,
  Check,
  CircleAlert,
  LoaderCircle,
  ShieldCheck,
} from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { request } from "../api";
import type {
  Client,
  FrameworkOption,
} from "../types";

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

export function Setup({ onCreated }: { onCreated: (projectId: string) => void }) {
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

export function WorkspaceCreator({
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
