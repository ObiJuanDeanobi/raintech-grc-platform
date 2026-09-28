export interface ProjectIdentity {
  clientId: string;
  clientName: string;
  projectId: string;
  projectName: string;
}

export interface ActiveRevisionFixture<T> {
  project: ProjectIdentity;
  revisions: T[];
  activeAssessment: T;
}

export interface ClientProjectsFixture {
  id: string;
  name: string;
  projects: { id: string; name: string; framework_version_id: string }[];
}

/** Build reusable same-client or cross-client project isolation fixtures. */
export function clientProjectsFixture(crossClient = false): ClientProjectsFixture[] {
  const firstProject = { id: "project-1", name: "HIPAA A", framework_version_id: "framework-version" };
  const secondProject = { id: "project-2", name: "HIPAA B", framework_version_id: "framework-version" };
  if (!crossClient) {
    return [{ id: "client-1", name: "Northwind Health", projects: [firstProject, secondProject] }];
  }
  return [
    { id: "client-1", name: "Northwind Health", projects: [firstProject] },
    { id: "client-2", name: "Fabrikam Medical", projects: [secondProject] },
  ];
}

export function clientAssessmentProjectsFixture<
  T extends { id: string; project: { id: string; client_id: string; client_name: string; name: string } },
>(
  base: T,
  options: { crossClient?: boolean; revisionIds?: Record<string, string[]>; activeAssessmentIds?: Record<string, string> } = {},
) {
  const clients = clientProjectsFixture(options.crossClient ?? false);
  const projects = Object.fromEntries(clients.flatMap((client) => client.projects.map((project) => {
    const revisions = activeRevisionFixture(
      base,
      { clientId: client.id, clientName: client.name, projectId: project.id, projectName: project.name },
      options.revisionIds?.[project.id] ?? [project.id === "project-1" ? "assessment-1" : "assessment-2"],
      options.activeAssessmentIds?.[project.id],
    );
    return [project.id, revisions] as const;
  })));
  return { clients, projects };
}

/** Build project revisions while making the selected active revision explicit. */
export function activeRevisionFixture<
  T extends { id: string; project: { id: string; client_id: string; client_name: string; name: string } },
>(
  base: T,
  identity: ProjectIdentity,
  revisionIds: string[] = [base.id],
  activeAssessmentId = revisionIds[revisionIds.length - 1] ?? base.id,
): ActiveRevisionFixture<T> {
  if (revisionIds.length === 0 || !revisionIds.includes(activeAssessmentId)) {
    throw new Error("The active assessment must be included in the project revisions.");
  }
  const revisions = revisionIds.map((id) => ({
    ...base,
    id,
    project: {
      ...base.project,
      id: identity.projectId,
      client_id: identity.clientId,
      client_name: identity.clientName,
      name: identity.projectName,
    },
  }));
  return {
    project: identity,
    revisions,
    activeAssessment: revisions.find(({ id }) => id === activeAssessmentId)!,
  };
}

/** A manually released response supports deterministic stale-request tests. */
export function delayedResponse<T = Response>() {
  let resolve!: (value: T) => void;
  const promise = new Promise<T>((done) => { resolve = done; });
  return { promise, resolve };
}
