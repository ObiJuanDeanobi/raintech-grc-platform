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

type ScoreLine = { record_id: string; title?: string; points: number; state: "evidence_pending" | "not_met" | "pending" | "not_assessed" };

/**
 * A /cmmc-score response in the #141 shape: verified and projected figures with
 * literal arithmetic and the three 32 CFR 170.21 checks, built from deduction lines.
 */
export function cmmcScoreFixture(lines: ScoreLine[], options: { complete?: boolean; blockers?: string[] } = {}) {
  const figure = (included: ScoreLine[]) => {
    const value = 110 - included.reduce((sum, line) => sum + line.points, 0);
    const terms = included.map((line) => ` − ${line.points}`).join("");
    return {
      value,
      deductions: included.map((line) => ({ record_id: line.record_id, points: line.points, state: line.state })),
      arithmetic: `110${terms} = ${value < 0 ? `−${-value}` : value}`,
    };
  };
  const verified = figure(lines);
  const projected = figure(lines.filter((line) => line.state !== "evidence_pending"));
  const reason = (line: ScoreLine) => line.points <= 1
    ? "1-point requirement (32 CFR 170.21(a)(2)(ii))."
    : `${line.points}-point requirement; only 1-point requirements may be on a POA&M (32 CFR 170.21(a)(2)(ii)).`;
  const items = lines.map((line) => ({
    record_id: line.record_id, title: line.title ?? line.record_id, state: line.state, points: line.points,
    allowed: line.points <= 1,
    reason: reason(line),
  }));
  const complete = options.complete ?? !lines.some((line) => line.state === "pending" || line.state === "not_assessed");
  const checks = [
    { key: "minimum_score", source: "32 CFR 170.21(a)(2)(i)", passed: verified.value >= 88, detail: `Verified score ${verified.value} ÷ 110; at least 88 of 110 is required.` },
    { key: "maximum_points", source: "32 CFR 170.21(a)(2)(ii)", passed: items.every((item) => item.allowed), detail: "Only POA&M-eligible requirements may be unverified.", items },
    { key: "excluded", source: "32 CFR 170.21(a)(2)(iii)", passed: true, detail: "Never on a POA&M.", items: [{ record_id: "CA.L2-3.12.4", title: "System Security Plan", state: "met" }] },
  ];
  return {
    authority: "32 CFR 170.24 CMMC Scoring Methodology", methodology: "NIST SP 800-171 DoD Assessment Methodology v1.2.1",
    maximum_score: 110, minimum_score: -203, score: verified.value, verified, projected, complete,
    blockers: options.blockers ?? [],
    deductions: lines.map((line) => ({ record_id: line.record_id, citation: line.record_id, title: line.title ?? line.record_id, points: line.points, state: line.state, source: "32 CFR 170.24", conditional_poam_allowed: line.points <= 1, poam_reason: reason(line) })),
    evidence_pending: lines.filter((line) => line.state === "evidence_pending").map((line) => line.record_id),
    unscored: [], partial_inputs_needed: [], partial_implementations: {}, follow_up: [],
    conditional: { source: "32 CFR 170.21(a)(2)", score_ratio: verified.value / 110, minimum_score: 88, eligible: complete && checks.every((check) => check.passed), checks },
  };
}
