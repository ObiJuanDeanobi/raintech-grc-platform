import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

// Selected read-only workspace direction retained as a throwaway prototype.
type Framework = "CMMC" | "HIPAA";
type Tone = "good" | "warn" | "bad" | "neutral";

// Distinct record types projected into the queues. Report blockers and stale-evidence
// warnings are derived signals, not records, so they never appear here.
type WorkRecord = {
  id: string;
  type: "POA&M" | "Corrective action" | "Finding" | "Evidence request" | "Risk treatment" | "Recurring review" | "Task";
  title: string;
  status: "Open" | "In Progress" | "Waiting" | "Ready for Validation";
  due: string;
  owner: string;
  tone: Tone;
  source: string;
  links: { label: string; value: string }[];
  nextAction: string;
  closeRule: string;
  customerVisible?: string;
};

type Project = {
  framework: Framework;
  client: string;
  project: string;
  assessment: string;
  phase: string;
  endDate: string;
  daysRemaining: number;
  completion: number;
  profile: number;
  frameworkAreas: string[];
  metrics: { label: string; value: string; tone: Tone }[];
  actions: { kind: string; title: string; context: string; due: string; tone: Tone }[];
  requirements: { id: string; title: string; status: string; evidence: string; finding: string }[];
  profileFacts: {
    label: string;
    baseline: string;
    current: string;
    target: string;
    status: "Confirmed" | "Changed" | "Missing";
    impact: string;
  }[];
  scopeSummary: { label: string; value: string; detail: string; tone: Tone }[];
  workRecords: WorkRecord[];
  evidence: { title: string; mappings: string; review: string; tone: Tone }[];
  risks: { title: string; inherent: string; residual: string; owner: string }[];
  policies: { title: string; state: string; review: string }[];
  reports: { title: string; readiness: string }[];
};

const projects: Record<Framework, Project> = {
  CMMC: {
    framework: "CMMC",
    client: "Aster Forge Systems",
    project: "CMMC Level 2 2026",
    assessment: "CMMC 2.0 Level 2 · Draft 01",
    phase: "Gap Analysis",
    endDate: "Dec 18, 2026",
    daysRemaining: 148,
    completion: 61,
    profile: 72,
    frameworkAreas: ["Scope", "Gap Analysis", "Findings", "Validation", "History"],
    metrics: [
      { label: "Requirements reviewed", value: "67 / 110", tone: "neutral" },
      { label: "Assessment objectives", value: "188 / 320", tone: "neutral" },
      { label: "Open POA&M", value: "14", tone: "bad" },
      { label: "Evidence due soon", value: "6", tone: "warn" },
    ],
    actions: [
      { kind: "Validation", title: "Confirm MFA enforcement for privileged roles", context: "IA.L2-3.5.3 · 2 evidence mappings", due: "Today", tone: "bad" },
      { kind: "Evidence request", title: "Obtain quarterly access review export", context: "AC.L2-3.1.5 · waiting on IT lead", due: "Jul 25", tone: "warn" },
      { kind: "POA&M", title: "Disable unmanaged USB storage", context: "MP.L2-3.8.7 · remediation owner assigned", due: "Jul 29", tone: "warn" },
      { kind: "Recurring review", title: "Review CUI enclave boundary inventory", context: "Scope profile · annual review", due: "Aug 02", tone: "neutral" },
      { kind: "Evidence validation", title: "Validate CUI data flow workshop notes", context: "AC.L2-3.1.3 · confirm approved paths", due: "Aug 04", tone: "warn" },
      { kind: "Risk treatment", title: "Reduce removable media residual risk", context: "RISK-007 · Operations owner", due: "Aug 06", tone: "bad" },
      { kind: "Report blocker", title: "Resolve unreviewed CMMC requirements", context: "Gap & Score Report · 43 requirements remain", due: "Aug 08", tone: "neutral" },
    ],
    requirements: [
      { id: "AC.L2-3.1.3", title: "Control CUI flow in accordance with authorizations", status: "Pending", evidence: "3 mapped", finding: "1 open" },
      { id: "IA.L2-3.5.3", title: "Use multifactor authentication", status: "Not Met", evidence: "2 mapped", finding: "POA&M-014" },
      { id: "MP.L2-3.8.7", title: "Control removable media use", status: "Pending", evidence: "1 stale", finding: "POA&M-011" },
      { id: "SC.L2-3.13.8", title: "Implement cryptographic mechanisms for CUI in transit", status: "Met", evidence: "4 mapped", finding: "—" },
      { id: "SI.L2-3.14.1", title: "Identify and correct system flaws", status: "Blank", evidence: "0 mapped", finding: "—" },
    ],
    profileFacts: [
      { label: "CUI boundary", baseline: "Microsoft 365 GCC and engineering workstations", current: "GCC enclave; 38 named users", target: "Validated enclave with controlled print", status: "Changed", impact: "Defines AC and SC assessment scope" },
      { label: "Endpoints", baseline: "Windows endpoints; inventory pending", current: "Windows 11 + 6 engineering workstations", target: "Intune-managed compliant endpoints", status: "Confirmed", impact: "Drives endpoint evidence and sampling" },
      { label: "Remote access", baseline: "Remote access used; method unconfirmed", current: "Windows 365 Government pilot", target: "KVM-only workflow; no redirection", status: "Missing", impact: "Blocks final boundary and CUI-flow decision" },
      { label: "Email & files", baseline: "Microsoft 365 GCC", current: "Microsoft 365 GCC", target: "GCC with DLP and retention baseline", status: "Confirmed", impact: "Supports inherited and configured controls" },
    ],
    scopeSummary: [
      { label: "People", value: "38", detail: "Named enclave users", tone: "good" },
      { label: "Systems", value: "12", detail: "In-scope systems", tone: "good" },
      { label: "Locations", value: "2", detail: "Office and controlled print", tone: "neutral" },
      { label: "Service providers", value: "4", detail: "One validation pending", tone: "warn" },
    ],
    workRecords: [
      {
        id: "POAM-014", type: "POA&M", title: "Enforce phishing-resistant MFA for privileged roles",
        status: "In Progress", due: "Aug 15", owner: "IT Lead", tone: "bad",
        source: "IA.L2-3.5.3 determined Not Met · Draft 01",
        links: [{ label: "Requirement", value: "IA.L2-3.5.3" }, { label: "Finding", value: "F-021" }, { label: "Risk", value: "RISK-011" }],
        nextAction: "Extend the Conditional Access policy to the four remaining administrator accounts.",
        closeRule: "Objective IA.L2-3.5.3[a] is re-determined Met with mapped evidence. Closing the POA&M does not close the finding.",
        customerVisible: "Included in the customer POA&M with milestone dates.",
      },
      {
        id: "POAM-011", type: "POA&M", title: "Disable unmanaged USB storage",
        status: "Ready for Validation", due: "Jul 29", owner: "Operations", tone: "warn",
        source: "MP.L2-3.8.7 determined Pending · Draft 01",
        links: [{ label: "Requirement", value: "MP.L2-3.8.7" }, { label: "Risk", value: "RISK-007" }],
        nextAction: "Confirm the Intune removable-media policy applied to all six engineering workstations.",
        closeRule: "Validation evidence is mapped and the objective is re-determined. Remains open until that decision is recorded.",
        customerVisible: "Included in the customer POA&M.",
      },
      {
        id: "F-021", type: "Finding", title: "Privileged accounts authenticate without phishing-resistant MFA",
        status: "Open", due: "—", owner: "Johnathan Dean", tone: "bad",
        source: "Gap analysis · CMMC 2.0 Level 2 Draft 01",
        links: [{ label: "Requirement", value: "IA.L2-3.5.3" }, { label: "POA&M", value: "POAM-014" }],
        nextAction: "No direct action. The finding tracks the gap; POAM-014 tracks the remediation.",
        closeRule: "Revalidation of the objective in a later assessment. A finding never closes because its POA&M closed.",
      },
      {
        id: "EVR-006", type: "Evidence request", title: "Quarterly access review export",
        status: "Waiting", due: "Jul 25", owner: "IT Lead (client)", tone: "warn",
        source: "AC.L2-3.1.5 · requested Jul 11",
        links: [{ label: "Requirement", value: "AC.L2-3.1.5" }],
        nextAction: "Second follow-up sent Jul 22. Escalate to the engagement sponsor if unanswered by the due date.",
        closeRule: "Artifact received, versioned, and mapped with a rationale for what it supports.",
      },
      {
        id: "EVR-009", type: "Evidence request", title: "Confirm approved paths in CUI data flow workshop notes",
        status: "Ready for Validation", due: "Aug 04", owner: "Johnathan Dean", tone: "warn",
        source: "AC.L2-3.1.3 · artifact received, mapping unconfirmed",
        links: [{ label: "Requirement", value: "AC.L2-3.1.3" }, { label: "Evidence", value: "CUI data flow workshop notes" }],
        nextAction: "Reconcile the workshop notes against the current enclave boundary before accepting the mapping.",
        closeRule: "A mapping rationale is recorded for each requirement the artifact is claimed to support.",
      },
      {
        id: "RISK-007", type: "Risk treatment", title: "Reduce removable media residual risk",
        status: "In Progress", due: "Aug 06", owner: "Operations", tone: "bad",
        source: "Inherent 20 Critical · residual 10 High",
        links: [{ label: "Risk", value: "RISK-007" }, { label: "POA&M", value: "POAM-011" }],
        nextAction: "Residual score is not recalculated until the USB policy is validated.",
        closeRule: "Residual recalculated, then accepted with rationale, owner, and review date.",
      },
      {
        id: "REV-003", type: "Recurring review", title: "CUI enclave boundary inventory",
        status: "Open", due: "Aug 02", owner: "Johnathan Dean", tone: "neutral",
        source: "Annual schedule · 30-day lead time",
        links: [{ label: "Profile fact", value: "CUI boundary" }],
        nextAction: "Confirm the boundary is unchanged since the Jul 08 onboarding baseline.",
        closeRule: "A review event is recorded. No new version is created if nothing changed.",
      },
    ],
    evidence: [
      { title: "Conditional Access policy export", mappings: "IA 3.5.3 · AC 3.1.12", review: "Current · reviewed Jul 18", tone: "good" },
      { title: "CUI data flow workshop notes", mappings: "AC 3.1.3 · SC 3.13.8", review: "Needs validation", tone: "warn" },
      { title: "Removable media policy v2.1", mappings: "MP 3.8.7 · MP 3.8.8", review: "Stale · 391 days", tone: "bad" },
    ],
    risks: [
      { title: "CUI copied to unmanaged removable media", inherent: "20 Critical", residual: "10 High", owner: "Operations" },
      { title: "Privileged session without phishing-resistant MFA", inherent: "16 High", residual: "8 Moderate", owner: "IT Lead" },
    ],
    policies: [
      { title: "Access Control Policy", state: "Client review", review: "Aug 15" },
      { title: "Media Protection Procedure", state: "Internal draft", review: "Jul 30" },
    ],
    reports: [
      { title: "CMMC Gap & Score Report", readiness: "Blocked · 43 requirements remain" },
      { title: "CMMC Readiness & Implementation Estimate", readiness: "Preliminary · $70k–$150k" },
      { title: "Customer POA&M", readiness: "Draft · 14 open items" },
    ],
  },
  HIPAA: {
    framework: "HIPAA",
    client: "Cedar Valley Community Health",
    project: "HIPAA 2026",
    assessment: "HIPAA Program Review · Draft 02",
    phase: "Remediation",
    endDate: "Oct 30, 2026",
    daysRemaining: 99,
    completion: 66,
    profile: 81,
    frameworkAreas: ["Security Rule", "Privacy Rule", "Breach Notification", "Security Risk Analysis"],
    metrics: [
      { label: "Standards reviewed", value: "41 / 62", tone: "neutral" },
      { label: "ePHI systems scoped", value: "23 / 24", tone: "warn" },
      { label: "Corrective actions", value: "9", tone: "bad" },
      { label: "Reviews due soon", value: "4", tone: "warn" },
    ],
    actions: [
      { kind: "Corrective action", title: "Document alternate measure for emergency access", context: "164.312(a)(2)(ii) · addressable", due: "Today", tone: "bad" },
      { kind: "Scope check", title: "Validate outreach tablet ePHI access", context: "SRA scope · one system unresolved", due: "Jul 24", tone: "bad" },
      { kind: "Evidence request", title: "Obtain BAA register from procurement", context: "Privacy · shared evidence request", due: "Jul 28", tone: "warn" },
      { kind: "Recurring review", title: "Review breach response contact tree", context: "Breach Notification · semiannual", due: "Aug 05", tone: "neutral" },
      { kind: "Evidence validation", title: "Confirm outreach tablet encryption state", context: "SRA evidence · Clinical Operations", due: "Aug 06", tone: "warn" },
      { kind: "Risk treatment", title: "Reduce offline ePHI exposure", context: "RISK-003 · residual risk remains High", due: "Aug 08", tone: "bad" },
      { kind: "Report blocker", title: "Resolve incomplete SRA system scope", context: "HIPAA Security Risk Analysis · 1 system remains", due: "Aug 11", tone: "neutral" },
    ],
    requirements: [
      { id: "164.308(a)(1)(ii)(A)", title: "Conduct an accurate and thorough risk analysis", status: "Pending", evidence: "5 mapped", finding: "SRA incomplete" },
      { id: "164.312(a)(2)(ii)", title: "Establish emergency access procedure", status: "Not Met", evidence: "1 mapped", finding: "CA-009" },
      { id: "164.312(e)(1)", title: "Guard against unauthorized access in transmission", status: "Met", evidence: "3 mapped", finding: "—" },
      { id: "164.530(j)", title: "Retain required documentation", status: "Met", evidence: "2 mapped", finding: "—" },
      { id: "164.404(a)(2)", title: "Breach discovery and notification timing", status: "N/A", evidence: "Rationale recorded", finding: "Test scenario only" },
    ],
    profileFacts: [
      { label: "ePHI systems", baseline: "23 known systems; outreach workflow pending", current: "23 confirmed; outreach tablet unresolved", target: "24 reviewed with explicit inclusion/exclusion", status: "Missing", impact: "Blocks completion of the security risk analysis" },
      { label: "Clinical platform", baseline: "Hosted EHR and e-prescribing", current: "Hosted EHR + e-prescribing", target: "Same vendors; validated BAAs and access logs", status: "Confirmed", impact: "Sets system and business-associate evidence" },
      { label: "Locations", baseline: "Four clinic locations", current: "4 clinics + mobile outreach", target: "Unified facility and device inventory", status: "Changed", impact: "Adds mobile outreach to physical scope" },
      { label: "Third parties", baseline: "16 known vendors", current: "18 vendors with ePHI touchpoints", target: "Current BAA and review owner for each", status: "Changed", impact: "Expands BAA and vendor-risk review" },
    ],
    scopeSummary: [
      { label: "Workforce groups", value: "9", detail: "Clinical and administrative", tone: "good" },
      { label: "ePHI systems", value: "23 / 24", detail: "One system unresolved", tone: "warn" },
      { label: "Locations", value: "5", detail: "Clinics plus mobile outreach", tone: "good" },
      { label: "Vendors", value: "18", detail: "BAA coverage under review", tone: "warn" },
    ],
    workRecords: [
      {
        id: "CA-009", type: "Corrective action", title: "Document and test emergency access procedure",
        status: "In Progress", due: "Aug 12", owner: "Security Officer", tone: "bad",
        source: "164.312(a)(2)(ii) determined Not Met · addressable specification",
        links: [{ label: "Standard", value: "164.312(a)(2)(ii)" }, { label: "Finding", value: "F-104" }],
        nextAction: "Draft the procedure, name the activation roles, and schedule the first test.",
        closeRule: "Procedure approved and one test recorded. The addressable decision and its rationale are recorded separately.",
        customerVisible: "Included in the executive corrective action plan.",
      },
      {
        id: "CA-004", type: "Corrective action", title: "Confirm outreach tablet encryption state",
        status: "Ready for Validation", due: "Aug 06", owner: "Clinical Operations", tone: "warn",
        source: "Security Risk Analysis scope gap · one system unresolved",
        links: [{ label: "Assessment check", value: "SRA-01" }, { label: "Risk", value: "RISK-003" }, { label: "Task", value: "TASK-021" }],
        nextAction: "Device returned Jul 24. Verify the managed encryption state before accepting the result.",
        closeRule: "Encryption confirmed, and the system is included in scope or excluded with a factual rationale.",
        customerVisible: "Included in the executive corrective action plan.",
      },
      {
        id: "F-104", type: "Finding", title: "No documented emergency access procedure for ePHI",
        status: "Open", due: "—", owner: "Johnathan Dean", tone: "bad",
        source: "Security Rule review · HIPAA Program Review Draft 02",
        links: [{ label: "Standard", value: "164.312(a)(2)(ii)" }, { label: "Corrective action", value: "CA-009" }],
        nextAction: "No direct action. The finding records the gap; CA-009 records the remediation.",
        closeRule: "Revalidation in a later assessment. Completing CA-009 does not close this finding.",
      },
      {
        id: "TASK-021", type: "Task", title: "Resolve outreach tablet inclusion in SRA scope",
        status: "Open", due: "Jul 24", owner: "Johnathan Dean", tone: "bad",
        source: "Security Risk Analysis cannot be issued with unresolved scope",
        links: [{ label: "Assessment check", value: "SRA-01" }, { label: "Corrective action", value: "CA-004" }],
        nextAction: "Include the system in scope or exclude it with a documented rationale and owner confirmation.",
        closeRule: "Every in-scope ePHI system, location, and vendor is reviewed or explicitly excluded.",
      },
      {
        id: "EVR-014", type: "Evidence request", title: "Business Associate Agreement register",
        status: "Waiting", due: "Jul 28", owner: "Procurement", tone: "warn",
        source: "Privacy minimum necessary · SRA vendor scope",
        links: [{ label: "Work area", value: "Privacy Rule" }, { label: "Work area", value: "Security Risk Analysis" }],
        nextAction: "Requested Jul 18, no response. 18 vendors currently have ePHI touchpoints.",
        closeRule: "Register received and each vendor mapped with its own support rationale. One artifact, many mappings.",
      },
      {
        id: "RISK-003", type: "Risk treatment", title: "Reduce offline ePHI exposure on outreach devices",
        status: "In Progress", due: "Aug 08", owner: "Clinical Ops", tone: "bad",
        source: "Inherent 20 Critical · residual 15 High",
        links: [{ label: "Risk", value: "RISK-003" }, { label: "Corrective action", value: "CA-004" }],
        nextAction: "Residual stays High until the encryption state is confirmed.",
        closeRule: "Residual recalculated. Acceptance at High or Critical requires a named approver and a review date.",
      },
      {
        id: "REV-007", type: "Recurring review", title: "Breach response contact tree",
        status: "Open", due: "Aug 05", owner: "Compliance", tone: "neutral",
        source: "Semiannual schedule · 30-day lead time",
        links: [{ label: "Policy", value: "Breach Notification Procedure" }],
        nextAction: "Verify after-hours and weekend contacts before the review date.",
        closeRule: "A review event is recorded. No new policy version is created if nothing changed.",
      },
    ],
    evidence: [
      { title: "Enterprise access review — Q2", mappings: "Security · Privacy minimum necessary", review: "Current · reviewed Jul 16", tone: "good" },
      { title: "Business Associate Agreement register", mappings: "Privacy · SRA vendor scope", review: "Requested · due Jul 28", tone: "warn" },
      { title: "Breach response tabletop record", mappings: "Breach Notification · Security incidents", review: "Review due in 13 days", tone: "warn" },
    ],
    risks: [
      { title: "Outreach tablet stores offline ePHI without confirmed encryption", inherent: "20 Critical", residual: "15 High", owner: "Clinical Ops" },
      { title: "Delayed access removal for departing workforce", inherent: "12 High", residual: "6 Moderate", owner: "HR + IT" },
    ],
    policies: [
      { title: "HIPAA Security Policy", state: "Approved", review: "Sep 01" },
      { title: "Breach Notification Procedure", state: "Client review", review: "Aug 05" },
    ],
    reports: [
      { title: "HIPAA Security Risk Analysis", readiness: "Blocked · 1 system not reviewed" },
      { title: "HIPAA Gap Report", readiness: "Draft · 12 decisions unresolved" },
      { title: "Executive Corrective Action Plan", readiness: "Ready for internal review" },
    ],
  },
};

function Pill({ children, tone = "neutral" }: { children: React.ReactNode; tone?: Tone }) {
  return <span className={`pill ${tone}`}>{children}</span>;
}

function ProjectPicker({ active, onChange, compact = false }: { active?: Framework; onChange: (value: Framework) => void; compact?: boolean }) {
  return (
    <div className={`project-picker ${compact ? "compact" : ""}`} aria-label="Synthetic client list">
      {(Object.keys(projects) as Framework[]).map((key) => (
        <button className={active === key ? "active" : ""} key={key} onClick={() => onChange(key)}>
          <span>{key === "CMMC" ? "AF" : "CV"}</span>
          <span><b>{projects[key].client}</b><small>{projects[key].project}</small><small className="project-end">Ends {projects[key].endDate}</small></span>
        </button>
      ))}
    </div>
  );
}

function Identity({ project }: { project: Project }) {
  return (
    <div className="identity">
      <div>
        <span className="eyebrow">{project.client} / {project.framework}</span>
        <h1>{project.project}</h1>
      </div>
      <div className="identity-meta">
        <Pill tone="warn">{project.phase}</Pill>
        <span>{project.assessment}</span>
        <span>Ends {project.endDate}</span>
      </div>
    </div>
  );
}

function UtilityBar() {
  return (
    <div className="utility-bar">
      <span>Prototype workspace</span>
      <div>
        <button aria-label="Notifications"><span aria-hidden="true">♢</span><i>3</i></button>
        <button className="user-menu" aria-label="Signed in user: Johnathan Dean">
          <span>JD</span>
          <b>Johnathan Dean</b>
          <em>⌄</em>
        </button>
      </div>
    </div>
  );
}

function Metrics({ project }: { project: Project }) {
  const metrics = [
    ...project.metrics.slice(0, 3),
    { label: "Project ends", value: project.endDate, tone: "warn" as Tone, detail: `${project.daysRemaining} days remaining` },
  ];
  return <div className="metric-strip">{metrics.map((metric) => <div className={"detail" in metric ? "schedule-metric" : ""} key={metric.label}><span>{metric.label}</span><b>{metric.value}</b>{"detail" in metric && <small>{metric.detail}</small>}<i className={metric.tone} /></div>)}</div>;
}

function ActionRows({ project, limit = 4 }: { project: Project; limit?: number }) {
  return <div className="rows">{project.actions.slice(0, limit).map((action) => <button className="row action-row" key={action.title}><i className={action.tone} /><span><b>{action.title}</b><small>{action.context}</small></span><Pill tone={action.tone}>{action.kind}</Pill><time>{action.due}</time><em>›</em></button>)}</div>;
}

function ProfileView({ project }: { project: Project }) {
  const unresolved = project.profileFacts.filter((fact) => fact.status !== "Confirmed");
  const statusTone = (status: "Confirmed" | "Changed" | "Missing"): Tone => status === "Confirmed" ? "good" : status === "Changed" ? "warn" : "bad";
  return (
    <div className="profile-view">
      <div className="profile-intro">
        <div><span className="eyebrow">Progressive client profile</span><h2>From onboarding assumptions to validated implementation</h2><p>Assessment work enriches the profile without erasing what the client originally supplied.</p></div>
        <div className="profile-completion"><b>{project.profile}%</b><span>Profile complete</span><div className="bar"><i style={{ width: `${project.profile}%` }} /></div></div>
      </div>
      <div className="profile-stages">
        <div><i>1</i><span><b>Onboarding profile</b><small>Initial facts captured · Jul 08</small></span><Pill tone="good">Created</Pill></div>
        <em>→</em>
        <div><i>2</i><span><b>Implementation profile</b><small>Enriched during {project.phase.toLowerCase()}</small></span><Pill tone="warn">{unresolved.length} unresolved</Pill></div>
        <div className="profile-schedule"><span>Project end</span><b>{project.endDate}</b><small>{project.daysRemaining} days remaining</small></div>
      </div>
      <div className="section-title profile-section-title"><div><span>Assessment boundary</span><h2>Scope snapshot</h2></div><small>Current validated counts</small></div>
      <div className="profile-scope">
        {project.scopeSummary.map((item) => <div key={item.label}><i className={item.tone} /><span>{item.label}</span><b>{item.value}</b><small>{item.detail}</small></div>)}
      </div>
      <div className="profile-layout">
        <section className="profile-facts">
          <div className="profile-facts-title"><div><span>Progressive record</span><h2>Profile facts</h2></div><small>Onboarding baseline → current validated state → required target</small></div>
          <div className="profile-facts-head"><span>Fact and assessment impact</span><span>Onboarding baseline</span><span>Current validated state</span><span>Target / required delta</span><span>Status</span></div>
          {project.profileFacts.map((fact) => (
            <button key={fact.label}>
              <span><b>{fact.label}</b><small>{fact.impact}</small></span>
              <p>{fact.baseline}</p>
              <p>{fact.current}</p>
              <p>{fact.target}</p>
              <Pill tone={statusTone(fact.status)}>{fact.status}</Pill>
            </button>
          ))}
        </section>
        <aside className="profile-attention">
          <div className="inspector-head"><span>Profile attention</span><Pill tone="warn">{unresolved.length} items</Pill></div>
          <h3>Needs confirmation</h3>
          {unresolved.map((fact) => <div className="attention-item" key={fact.label}><Pill tone={statusTone(fact.status)}>{fact.status}</Pill><b>{fact.label}</b><p>{fact.target}</p></div>)}
          <h3>Used by assessment</h3>
          <div className="profile-consumer"><b>Scope</b><span>Boundary, systems, people, locations, and providers</span></div>
          <div className="profile-consumer"><b>Gap Analysis</b><span>Objective applicability and implementation context</span></div>
          <div className="profile-consumer"><b>Reports</b><span>Client environment narrative and unresolved assumptions</span></div>
        </aside>
      </div>
    </div>
  );
}

const workTypeOrder: WorkRecord["type"][] = ["POA&M", "Corrective action", "Finding", "Evidence request", "Risk treatment", "Recurring review", "Task"];

function ActionsView({ project }: { project: Project }) {
  const [typeFilter, setTypeFilter] = useState<string>("All");
  const [selectedId, setSelectedId] = useState<string>(project.workRecords[0].id);
  const counts = new Map<string, number>();
  project.workRecords.forEach((record) => counts.set(record.type, (counts.get(record.type) ?? 0) + 1));
  const types = ["All", ...workTypeOrder.filter((type) => counts.has(type))];
  const visible = typeFilter === "All" ? project.workRecords : project.workRecords.filter((record) => record.type === typeFilter);
  const ready = visible.filter((record) => record.status === "Ready for Validation");
  const active = visible.filter((record) => record.status !== "Ready for Validation");
  const selected = visible.find((record) => record.id === selectedId) ?? visible[0] ?? project.workRecords[0];
  const statusTone = (status: WorkRecord["status"]): Tone =>
    status === "Ready for Validation" ? "good" : status === "In Progress" ? "warn" : status === "Waiting" ? "neutral" : "bad";
  const row = (record: WorkRecord) => (
    <button className={`work-row ${record.id === selected.id ? "selected" : ""}`} key={record.id} onClick={() => setSelectedId(record.id)}>
      <i className={record.tone} />
      <code>{record.id}</code>
      <span><b>{record.title}</b><small>{record.source}</small></span>
      <Pill tone={record.type === "POA&M" || record.type === "Corrective action" ? "warn" : "neutral"}>{record.type}</Pill>
      <em>{record.owner}</em>
      <time>{record.due}</time>
    </button>
  );
  return (
    <div className="work-view">
      <div className="section-title work-title">
        <div><span>Continuous remediation</span><h2>Actions and POA&amp;M</h2></div>
        <div className="queue-summary"><b>{project.workRecords.length} records</b><span>Queues prioritise this work; the records are managed here</span></div>
      </div>
      <div className="work-types">
        {types.map((type) => (
          <button className={type === typeFilter ? "active" : ""} key={type} onClick={() => setTypeFilter(type)}>
            {type}{type !== "All" && <i>{counts.get(type)}</i>}
          </button>
        ))}
      </div>
      <div className="work-layout">
        <section className="work-list">
          {ready.length > 0 && (
            <>
              <div className="work-group"><b>Ready for validation</b><small>Does not close automatically — each item needs an explicit validation decision</small><Pill tone="good">{ready.length}</Pill></div>
              {ready.map(row)}
            </>
          )}
          {active.length > 0 && (
            <>
              <div className="work-group"><b>Open work</b><small>Open, In Progress, and Waiting</small><Pill tone="neutral">{active.length}</Pill></div>
              {active.map(row)}
            </>
          )}
          <p className="work-note">Report blockers and stale-evidence warnings appear in the queues as derived signals. They are not records and are not managed here.</p>
        </section>
        <aside className="work-record">
          <div className="inspector-head"><span>Work record</span><Pill tone={statusTone(selected.status)}>{selected.status}</Pill></div>
          <div className="work-record-head"><code>{selected.id}</code><h3>{selected.title}</h3><Pill tone="neutral">{selected.type}</Pill></div>
          <div className="assessment-field first"><span>Owner and due</span><p>{selected.owner} · {selected.due}</p></div>
          <div className="assessment-field"><span>Raised by</span><p>{selected.source}</p></div>
          <div className="assessment-field">
            <span>Linked records</span>
            {selected.links.map((link) => <div className="work-link" key={`${link.label}-${link.value}`}><small>{link.label}</small><b>{link.value}</b></div>)}
          </div>
          <div className="assessment-field"><span>Next action</span><p>{selected.nextAction}</p></div>
          <div className="assessment-field"><span>Closes when</span><p>{selected.closeRule}</p></div>
          {selected.customerVisible && <div className="assessment-field"><span>Customer-facing output</span><p>{selected.customerVisible}</p></div>}
        </aside>
      </div>
    </div>
  );
}

function PortfolioDashboard({ onOpenClient }: { onOpenClient: (framework: Framework) => void }) {
  const actions = (Object.keys(projects) as Framework[]).flatMap((framework) =>
    projects[framework].actions.map((action) => ({ ...action, framework, client: projects[framework].client })),
  );
  return (
    <div className="portfolio-dashboard">
      <header>
        <div><span className="eyebrow">RainTech portfolio</span><h1>Dashboard</h1><p>All client work in one place</p></div>
        <Pill tone="neutral">Internal workspace</Pill>
      </header>
      <div className="portfolio-metrics">
        <div><span>Active clients</span><b>2</b><small>CMMC and HIPAA engagements</small></div>
        <div><span>Open work</span><b>{actions.length}</b><small>Across all client queues</small></div>
        <div><span>Due today</span><b>2</b><small>Both require validation</small></div>
        <div><span>High priority</span><b>4</b><small>Corrective action or risk treatment</small></div>
      </div>
      <div className="active-projects-heading"><span>Current delivery schedule</span><h2>Active projects</h2></div>
      <div className="active-projects">
        {(Object.keys(projects) as Framework[]).map((framework) => {
          const item = projects[framework];
          return (
            <button key={framework} onClick={() => onOpenClient(framework)}>
              <div><span>{item.client}</span><h3>{item.project}</h3></div>
              <Pill tone="warn">{item.phase}</Pill>
              <div className="project-date"><span>Project end</span><b>{item.endDate}</b></div>
              <div className="project-days"><b>{item.daysRemaining}</b><span>days remaining</span></div>
              <div className="project-completion">
                <div><span>Project completed</span><b>{item.completion}%</b></div>
                <div className="completion-bar"><i style={{ width: `${item.completion}%` }} /></div>
              </div>
              <em>›</em>
            </button>
          );
        })}
      </div>
      <div className="section-title portfolio-queue-title">
        <div><span>Every client</span><h2>Unified queue</h2></div>
        <div className="queue-summary"><b>{actions.length} open</b><span>Sorted by priority and due date</span></div>
      </div>
      <div className="rows portfolio-queue">
        {actions.map((action) => (
          <button className="row action-row" key={`${action.framework}-${action.title}`} onClick={() => onOpenClient(action.framework)}>
            <i className={action.tone} />
            <span><b>{action.title}</b><small>{action.client} · {action.context}</small></span>
            <Pill tone={action.framework === "CMMC" ? "neutral" : "good"}>{action.framework}</Pill>
            <Pill tone={action.tone}>{action.kind}</Pill>
            <time>{action.due}</time><em>›</em>
          </button>
        ))}
      </div>
    </div>
  );
}

const phases = ["Onboarding", "Scope", "Gap Analysis", "Remediation", "Validation", "Reporting"];

function Workspace({ project, framework, onProjectChange }: { project: Project; framework: Framework; onProjectChange: (value: Framework) => void }) {
  const nav = ["Overview", "Profile", "Assessments", "Actions / POA&M", "Evidence", "Risks", "Policies", "Reports"];
  const activePhase = project.phase === "Gap Analysis" ? 2 : 3;
  const [activeView, setActiveView] = useState<"Dashboard" | "Overview" | "Profile" | "Assessments" | "Actions / POA&M">("Dashboard");
  const [selectedObjective, setSelectedObjective] = useState(0);
  const openClient = (value: Framework) => {
    onProjectChange(value);
    setSelectedObjective(0);
    setActiveView("Overview");
  };
  const assessmentItems = project.framework === "CMMC" ? [
    {
      id: "AC.L2-3.1.3[a]",
      title: "Authorized CUI flows are defined",
      status: "Pending",
      requirement: "Control CUI flow in accordance with approved authorizations.",
      check: "Determine whether authorized information flows for CUI are defined.",
      guidance: "Identify each approved source, destination, transfer method, and responsible owner. Reconcile the narrative with the current enclave boundary and data-flow diagram.",
      evidence: "CUI data-flow diagram; boundary inventory; flow authorization matrix",
    },
    {
      id: "AC.L2-3.1.3[b]",
      title: "Flow-control enforcement is implemented",
      status: "Not Met",
      requirement: "Control CUI flow in accordance with approved authorizations.",
      check: "Determine whether methods and enforcement mechanisms for controlling CUI flow are defined and implemented.",
      guidance: "Confirm how email, file sharing, printing, removable media, and remote sessions enforce the approved paths. Separate documented policy from technical enforcement.",
      evidence: "DLP policy export; firewall rules; print restrictions; administrator interview",
    },
    {
      id: "AC.L2-3.1.3[c]",
      title: "Approved destinations are identified",
      status: "Pending",
      requirement: "Control CUI flow in accordance with approved authorizations.",
      check: "Determine whether designated sources and destinations for CUI are identified.",
      guidance: "Validate the named systems, service providers, endpoints, and physical outputs against the live project profile.",
      evidence: "System inventory; service-provider list; endpoint inventory; observation",
    },
    {
      id: "IA.L2-3.5.3[a]",
      title: "Privileged access requires MFA",
      status: "Not Met",
      requirement: "Use multifactor authentication for local and network access.",
      check: "Determine whether multifactor authentication is implemented for privileged accounts.",
      guidance: "Review authentication paths for administrators, emergency accounts, and service-provider access. Record exclusions and compensating safeguards explicitly.",
      evidence: "Conditional Access export; privileged-role inventory; sign-in records",
    },
  ] : [
    {
      id: "SRA-01",
      title: "All ePHI systems and locations are identified",
      status: "Pending",
      requirement: "Conduct an accurate and thorough assessment of potential risks and vulnerabilities to ePHI.",
      check: "Confirm that every system, location, device, and vendor that creates, receives, maintains, or transmits ePHI is included or explicitly excluded.",
      guidance: "Resolve the outreach tablet before concluding scope. An exclusion needs a factual rationale and owner confirmation.",
      evidence: "ePHI inventory; data-flow notes; vendor register; location walkthrough",
    },
    {
      id: "SRA-02",
      title: "Threat-vulnerability pairs are documented",
      status: "Pending",
      requirement: "Evaluate risks and vulnerabilities to the confidentiality, integrity, and availability of ePHI.",
      check: "Confirm that credible threats are paired with specific vulnerabilities for each in-scope asset.",
      guidance: "Avoid generic risk statements. Tie each scenario to an asset, existing safeguards, likelihood, impact, and corrective action.",
      evidence: "Risk register; interview notes; vulnerability results; safeguard inventory",
    },
    {
      id: "164.312(a)(2)(ii)-01",
      title: "Emergency access approach is documented",
      status: "Not Met",
      requirement: "Establish procedures for obtaining necessary ePHI during an emergency.",
      check: "Confirm the standard measure or an equivalent alternative is documented and operational.",
      guidance: "Record the addressable decision, responsible roles, activation method, testing history, and why the selected approach is reasonable and appropriate.",
      evidence: "Emergency-access procedure; test record; access logs; workforce interview",
    },
    {
      id: "PRIV-01",
      title: "Minimum-necessary access is reviewed",
      status: "Met",
      requirement: "Limit uses, disclosures, and requests for PHI to the minimum necessary.",
      check: "Confirm role-based access and recurring access review evidence covers the relevant workforce.",
      guidance: "Use the shared Q2 access review, but document why that evidence supports this specific privacy decision.",
      evidence: "Access review; role matrix; termination sample; mapping rationale",
    },
  ];
  const objective = assessmentItems[selectedObjective];
  return (
    <div className="variant-a">
      <aside className="a-sidebar">
        <div className="brand"><span>R</span><b>RainTech</b><small>GRC workspace</small></div>
        <button className={`dashboard-link ${activeView === "Dashboard" ? "active" : ""}`} onClick={() => setActiveView("Dashboard")}><span>⌂</span>Dashboard</button>
        <span className="sidebar-label">Clients</span>
        <ProjectPicker active={activeView === "Dashboard" ? undefined : framework} onChange={openClient} compact />
        <span className="sidebar-label workspace-label">Client workspace</span>
        <nav>{nav.map((item, index) => <button className={item === activeView ? "active" : ""} key={item} onClick={() => {
          if (item === "Overview" || item === "Profile" || item === "Assessments" || item === "Actions / POA&M") setActiveView(item);
        }}><span>{["⌂", "◎", "▤", "✓", "◇", "△", "§", "↗"][index]}</span>{item}{item === "Actions / POA&M" && <i>{project.workRecords.length}</i>}</button>)}</nav>
        <div className="sidebar-foot"><b>Experimental prototype</b><span>Read-only synthetic data</span></div>
      </aside>
      <main className="a-main">
        <UtilityBar />
        {activeView === "Dashboard" ? <PortfolioDashboard onOpenClient={openClient} /> : (
          <>
            <Identity project={project} />
            {activeView === "Overview" ? (
              <>
                <Metrics project={project} />
                <div className="a-phase-rail" aria-label="Engagement phases">
                  {phases.map((phase, index) => (
                    <div className={index === activePhase ? "active" : index < activePhase ? "done" : ""} key={phase}>
                      <i>{index < activePhase ? "✓" : index + 1}</i>
                      <span>{phase}</span>
                      <small>{index === activePhase ? "In focus" : index < activePhase ? "Active work remains" : "Available"}</small>
                    </div>
                  ))}
                </div>
                <div className="a-overview">
                  <div className="a-resume">
                    <div className="a-resume-head">
                      <div><span>Continue where you left off</span><h2>{project.requirements[0].id} — {project.requirements[0].title}</h2></div>
                      <Pill tone="warn">{project.requirements[0].status}</Pill>
                    </div>
                    <div className="a-resume-progress">
                      <div><span>Assessment progress</span><b>{project.metrics[0].value}</b></div>
                      <div className="bar"><i style={{ width: `${project.profile}%` }} /></div>
                    </div>
                    <div className="a-resume-context">
                      <div><span>Implementation</span><b>{project.profileFacts[0].current}</b><small>Target: {project.profileFacts[0].target}</small></div>
                      <div><span>Evidence support</span><b>{project.evidence[0].title}</b><small>{project.evidence[0].mappings}</small></div>
                      <div><span>Linked action</span><b>{project.actions[0].title}</b><small>{project.actions[0].due} · {project.actions[0].kind}</small></div>
                    </div>
                  </div>
                  <div className="section-title queue-title">
                    <div><span>All actionable client work</span><h2>Client queue</h2></div>
                    <div className="queue-summary"><b>{project.actions.length} open</b><span>Sorted by priority and due date</span></div>
                  </div>
                  <ActionRows project={project} limit={project.actions.length} />
                </div>
              </>
            ) : activeView === "Profile" ? (
              <ProfileView project={project} />
            ) : activeView === "Actions / POA&M" ? (
              <ActionsView key={project.framework} project={project} />
            ) : (
              <div className="assessment-view">
                <div className="assessment-view-tabs">
                  {project.frameworkAreas.map((area, index) => <button className={index === 1 || (project.framework === "HIPAA" && index === 0) ? "active" : ""} key={area}>{area}</button>)}
                </div>
                <div className="objective-workspace">
                  <aside className="objective-nav">
                    <div className="objective-nav-head"><span>{project.framework === "CMMC" ? "Assessment objectives" : "Assessment checks"}</span><b>{assessmentItems.length} in current set</b></div>
                    {assessmentItems.map((item, index) => (
                      <button className={index === selectedObjective ? "active" : ""} key={item.id} onClick={() => setSelectedObjective(index)}>
                        <code>{item.id}</code>
                        <b>{item.title}</b>
                        <Pill tone={item.status === "Met" ? "good" : item.status === "Not Met" ? "bad" : "warn"}>{item.status}</Pill>
                      </button>
                    ))}
                  </aside>
                  <section className="objective-main">
                    <div className="objective-heading">
                      <div><span>{project.framework === "CMMC" ? "Current objective" : "Current assessment check"}</span><code>{objective.id}</code><h2>{objective.title}</h2></div>
                      <Pill tone={objective.status === "Met" ? "good" : objective.status === "Not Met" ? "bad" : "warn"}>{objective.status}</Pill>
                    </div>
                    <div className="objective-context-block">
                      <span className="inspector-label">Requirement</span>
                      <h3>{objective.requirement}</h3>
                    </div>
                    <div className="objective-context-block">
                      <span className="inspector-label">What to determine</span>
                      <p>{objective.check}</p>
                    </div>
                    <div className="assessment-field">
                      <span>Assessor determination</span>
                      <div className="status-options">{["Blank", "Met", "Not Met", "Pending"].map(status => <button className={status === objective.status ? "active" : ""} key={status}>{status}</button>)}</div>
                    </div>
                    <div className="objective-context-block">
                      <span className="inspector-label">Implementation guidance</span>
                      <p>{objective.guidance}</p>
                    </div>
                    <div className="objective-context-block">
                      <span className="inspector-label">Expected evidence</span>
                      <p>{objective.evidence}</p>
                    </div>
                    <div className="objective-context-block">
                      <span className="inspector-label">Linked work</span>
                      <div className="inspector-linked"><b>{project.actions[selectedObjective % project.actions.length].title}</b><small>{project.actions[selectedObjective % project.actions.length].kind} · {project.actions[selectedObjective % project.actions.length].due}</small></div>
                    </div>
                  </section>
                  <aside className="assessment-record">
                    <div className="inspector-head"><span>Assessment record</span><Pill tone="neutral">Working context</Pill></div>
                    <div className="assessment-field first">
                      <span>Implementation statement</span>
                      <p>{project.framework === "CMMC" ? project.profileFacts[0].current + ". Approved flow enforcement remains under validation against the target boundary." : project.profileFacts[0].current + ". Scope cannot be concluded until the unresolved system is included or excluded with rationale."}</p>
                    </div>
                    <div className="assessment-field">
                      <span>Mapped evidence</span>
                      {project.evidence.slice(0, 2).map(item => <div className="mapped-evidence" key={item.title}><i className={item.tone} /><div><b>{item.title}</b><small>{item.mappings} · {item.review}</small></div></div>)}
                    </div>
                    <div className="assessment-field">
                      <span>Assessment notes</span>
                      <p className="placeholder-note">Read-only prototype · interview notes, test results, and assessor rationale would be captured here.</p>
                    </div>
                  </aside>
                </div>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}

function App() {
  const [framework, setFramework] = useState<Framework>("CMMC");
  return <Workspace project={projects[framework]} framework={framework} onProjectChange={setFramework} />;
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
