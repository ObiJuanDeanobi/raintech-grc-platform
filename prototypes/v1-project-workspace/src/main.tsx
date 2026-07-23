import { StrictMode, useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./styles.css";

// Three variants of a project workspace, switchable via ?variant=, on one throwaway route.
type VariantKey = "A" | "B" | "C";
type Framework = "CMMC" | "HIPAA";
type Tone = "good" | "warn" | "bad" | "neutral";

type Project = {
  framework: Framework;
  client: string;
  project: string;
  assessment: string;
  phase: string;
  owner: string;
  profile: number;
  frameworkAreas: string[];
  metrics: { label: string; value: string; tone: Tone }[];
  actions: { kind: string; title: string; context: string; due: string; tone: Tone }[];
  requirements: { id: string; title: string; status: string; evidence: string; finding: string }[];
  profileFacts: { label: string; current: string; target: string }[];
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
    owner: "Johnathan · RainTech",
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
    ],
    requirements: [
      { id: "AC.L2-3.1.3", title: "Control CUI flow in accordance with authorizations", status: "Pending", evidence: "3 mapped", finding: "1 open" },
      { id: "IA.L2-3.5.3", title: "Use multifactor authentication", status: "Not Met", evidence: "2 mapped", finding: "POA&M-014" },
      { id: "MP.L2-3.8.7", title: "Control removable media use", status: "Pending", evidence: "1 stale", finding: "POA&M-011" },
      { id: "SC.L2-3.13.8", title: "Implement cryptographic mechanisms for CUI in transit", status: "Met", evidence: "4 mapped", finding: "—" },
      { id: "SI.L2-3.14.1", title: "Identify and correct system flaws", status: "Blank", evidence: "0 mapped", finding: "—" },
    ],
    profileFacts: [
      { label: "CUI boundary", current: "GCC enclave; 38 named users", target: "Validated enclave with controlled print" },
      { label: "Endpoints", current: "Windows 11 + 6 engineering workstations", target: "Intune-managed compliant endpoints" },
      { label: "Remote access", current: "Windows 365 Government pilot", target: "KVM-only workflow; no redirection" },
      { label: "Email & files", current: "Microsoft 365 GCC", target: "GCC with DLP and retention baseline" },
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
    owner: "Johnathan · RainTech",
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
    ],
    requirements: [
      { id: "164.308(a)(1)(ii)(A)", title: "Conduct an accurate and thorough risk analysis", status: "Pending", evidence: "5 mapped", finding: "SRA incomplete" },
      { id: "164.312(a)(2)(ii)", title: "Establish emergency access procedure", status: "Not Met", evidence: "1 mapped", finding: "CA-009" },
      { id: "164.312(e)(1)", title: "Guard against unauthorized access in transmission", status: "Met", evidence: "3 mapped", finding: "—" },
      { id: "164.530(j)", title: "Retain required documentation", status: "Met", evidence: "2 mapped", finding: "—" },
      { id: "164.404(a)(2)", title: "Breach discovery and notification timing", status: "N/A", evidence: "Rationale recorded", finding: "Test scenario only" },
    ],
    profileFacts: [
      { label: "ePHI systems", current: "23 confirmed; outreach tablet unresolved", target: "24 reviewed with explicit inclusion/exclusion" },
      { label: "Clinical platform", current: "Hosted EHR + e-prescribing", target: "Same vendors; validated BAAs and access logs" },
      { label: "Locations", current: "4 clinics + mobile outreach", target: "Unified facility and device inventory" },
      { label: "Third parties", current: "18 vendors with ePHI touchpoints", target: "Current BAA and review owner for each" },
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

const variantNames: Record<VariantKey, string> = {
  A: "Project Command Center",
  B: "Guided Engagement Flow",
  C: "Work Queue First",
};

function Pill({ children, tone = "neutral" }: { children: React.ReactNode; tone?: Tone }) {
  return <span className={`pill ${tone}`}>{children}</span>;
}

function ProjectPicker({ active, onChange, compact = false }: { active: Framework; onChange: (value: Framework) => void; compact?: boolean }) {
  return (
    <div className={`project-picker ${compact ? "compact" : ""}`} aria-label="Synthetic project selector">
      {(Object.keys(projects) as Framework[]).map((key) => (
        <button className={active === key ? "active" : ""} key={key} onClick={() => onChange(key)}>
          <span>{key === "CMMC" ? "AF" : "CV"}</span>
          <span><b>{projects[key].client}</b><small>{projects[key].project}</small></span>
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
        <span>{project.owner}</span>
      </div>
    </div>
  );
}

function Metrics({ project }: { project: Project }) {
  return <div className="metric-strip">{project.metrics.map((metric) => <div key={metric.label}><span>{metric.label}</span><b>{metric.value}</b><i className={metric.tone} /></div>)}</div>;
}

function ActionRows({ project, limit = 4 }: { project: Project; limit?: number }) {
  return <div className="rows">{project.actions.slice(0, limit).map((action) => <button className="row action-row" key={action.title}><i className={action.tone} /><span><b>{action.title}</b><small>{action.context}</small></span><Pill tone={action.tone}>{action.kind}</Pill><time>{action.due}</time><em>›</em></button>)}</div>;
}

function RequirementRows({ project, limit = 5 }: { project: Project; limit?: number }) {
  return <div className="rows requirement-rows">{project.requirements.slice(0, limit).map((req, index) => <button className={`row ${index === 0 ? "selected" : ""}`} key={req.id}><code>{req.id}</code><span><b>{req.title}</b><small>{req.evidence} · {req.finding}</small></span><Pill tone={req.status === "Met" ? "good" : req.status === "Not Met" ? "bad" : req.status === "Pending" ? "warn" : "neutral"}>{req.status}</Pill></button>)}</div>;
}

function ProfileTable({ project }: { project: Project }) {
  return <div className="profile-table"><div className="profile-head"><span>Profile fact</span><span>Current environment</span><span>Target / required delta</span></div>{project.profileFacts.map((fact) => <div key={fact.label}><b>{fact.label}</b><span>{fact.current}</span><span>{fact.target}</span></div>)}</div>;
}

const phases = ["Onboarding", "Scope", "Gap Analysis", "Remediation", "Validation", "Reporting"];

function VariantA({ project, framework, onProjectChange }: { project: Project; framework: Framework; onProjectChange: (value: Framework) => void }) {
  const nav = ["Overview", "Profile", "Assessments", "Actions / POA&M", "Evidence", "Risks", "Policies", "Reports"];
  const activePhase = project.phase === "Gap Analysis" ? 2 : 3;
  const [activeView, setActiveView] = useState<"Overview" | "Assessments">("Overview");
  const [selectedObjective, setSelectedObjective] = useState(0);
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
        <ProjectPicker active={framework} onChange={onProjectChange} compact />
        <nav>{nav.map((item, index) => <button className={item === activeView ? "active" : ""} key={item} onClick={() => {
          if (item === "Overview" || item === "Assessments") setActiveView(item);
        }}><span>{["⌂", "◎", "▤", "✓", "◇", "△", "§", "↗"][index]}</span>{item}{item === "Actions / POA&M" && <i>14</i>}</button>)}</nav>
        <div className="sidebar-foot"><b>Experimental prototype</b><span>Read-only synthetic data</span></div>
      </aside>
      <main className="a-main">
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
              <div className="section-title"><div><span>Priority work</span><h2>Next actions</h2></div><button>View unified queue →</button></div>
              <ActionRows project={project} />
              <div className="overview-registers">
                <div><span>Evidence attention</span><b>{project.evidence[1].title}</b><small>{project.evidence[1].review}</small></div>
                <div><span>Highest residual risk</span><b>{project.risks[0].title}</b><small>{project.risks[0].residual} · {project.risks[0].owner}</small></div>
                <div><span>Report gate</span><b>{project.reports[0].title}</b><small>{project.reports[0].readiness}</small></div>
              </div>
            </div>
          </>
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
                <div className="assessment-field">
                  <span>Assessor determination</span>
                  <div className="status-options">{["Blank", "Met", "Not Met", "Pending"].map(status => <button className={status === objective.status ? "active" : ""} key={status}>{status}</button>)}</div>
                </div>
                <div className="assessment-field">
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
              </section>
              <aside className="objective-inspector">
                <div className="inspector-head"><span>Objective context</span><Pill tone="neutral">Guidance</Pill></div>
                <span className="inspector-label">Requirement</span>
                <h3>{objective.requirement}</h3>
                <span className="inspector-label">What to determine</span>
                <p>{objective.check}</p>
                <span className="inspector-label">Implementation guidance</span>
                <p>{objective.guidance}</p>
                <span className="inspector-label">Expected evidence</span>
                <p>{objective.evidence}</p>
                <span className="inspector-label">Linked work</span>
                <div className="inspector-linked"><b>{project.actions[selectedObjective % project.actions.length].title}</b><small>{project.actions[selectedObjective % project.actions.length].kind} · {project.actions[selectedObjective % project.actions.length].due}</small></div>
              </aside>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function VariantB({ project, framework, onProjectChange }: { project: Project; framework: Framework; onProjectChange: (value: Framework) => void }) {
  const activePhase = project.phase === "Gap Analysis" ? 2 : 3;
  return (
    <div className="variant-b">
      <header className="b-header">
        <div className="brand light"><span>R</span><b>RainTech</b><small>Engagement workspace</small></div>
        <ProjectPicker active={framework} onChange={onProjectChange} compact />
        <div className="user-chip"><span>JD</span><b>Johnathan</b><small>Internal workspace</small></div>
      </header>
      <div className="b-body">
        <Identity project={project} />
        <div className="phase-rail">{phases.map((phase, index) => <button className={index === activePhase ? "active" : index < activePhase ? "done" : ""} key={phase}><i>{index < activePhase ? "✓" : index + 1}</i><span>{phase}</span><small>{index === activePhase ? "In focus" : index < activePhase ? "Active work remains" : "Available"}</small></button>)}</div>
        <div className="b-contextbar"><span><b>{project.phase} focus</b> · {project.framework === "CMMC" ? "Review requirements while remediation continues in parallel." : "Close program decisions while completing the ePHI scope."}</span><div>{project.frameworkAreas.map((area, i) => <button className={i === 0 ? "active" : ""} key={area}>{area}</button>)}</div></div>
        <main className="b-flow">
          <section className="focus-lane">
            <div className="lane-title"><span>01 · Continue where you left off</span><h2>{project.requirements[0].id} — {project.requirements[0].title}</h2></div>
            <div className="focus-progress"><div><span>Assessment progress</span><b>{project.metrics[0].value}</b></div><div className="bar"><i style={{ width: `${project.profile}%` }} /></div><Pill tone="warn">{project.requirements[0].status}</Pill></div>
            <div className="decision-grid">
              <div><span>Implementation</span><b>{project.profileFacts[0].current}</b><small>Target: {project.profileFacts[0].target}</small></div>
              <div><span>Evidence support</span><b>{project.evidence[0].title}</b><small>{project.evidence[0].mappings}</small></div>
              <div><span>Linked action</span><b>{project.actions[0].title}</b><small>{project.actions[0].due} · {project.actions[0].kind}</small></div>
            </div>
            <div className="section-title tight"><div><span>Upcoming in this phase</span><h2>Assessment sequence</h2></div><button>Open full assessment →</button></div>
            <RequirementRows project={project} limit={4} />
          </section>
          <aside className="parallel-lane">
            <div className="lane-title"><span>Parallel work</span><h2>Keep moving</h2></div>
            {project.actions.slice(0, 3).map((action) => <button className="parallel-item" key={action.title}><div><Pill tone={action.tone}>{action.kind}</Pill><time>{action.due}</time></div><b>{action.title}</b><small>{action.context}</small></button>)}
            <div className="profile-pulse"><div><span>Progressive profile</span><b>{project.profile}%</b></div><p>{project.profileFacts[0].label}: {project.profileFacts[0].current}</p><button>Review {project.profileFacts.length} changed facts →</button></div>
            <div className="issue-gate"><span>Reporting gate</span><b>{project.reports[0].title}</b><p>{project.reports[0].readiness}</p></div>
          </aside>
        </main>
      </div>
      <div className="experimental-tag">EXPERIMENTAL · READ ONLY</div>
    </div>
  );
}

function VariantC({ project, framework, onProjectChange }: { project: Project; framework: Framework; onProjectChange: (value: Framework) => void }) {
  const allActions = useMemo(() => [...projects.CMMC.actions.map((x) => ({ ...x, framework: "CMMC" as Framework })), ...projects.HIPAA.actions.map((x) => ({ ...x, framework: "HIPAA" as Framework }))], []);
  return (
    <div className="variant-c">
      <header className="c-header">
        <div className="brand light"><span>R</span><b>RainTech</b><small>Daily work queue</small></div>
        <div className="queue-title"><span>My work</span><h1>8 items need attention</h1></div>
        <div className="queue-filters"><button className="active">Priority</button><button>Due soon</button><button>Validation</button><button>Reviews</button></div>
        <div className="user-chip"><span>JD</span><b>Johnathan</b></div>
      </header>
      <main className="c-workspace">
        <aside className="queue-pane">
          <div className="queue-summary"><span>Unified queue · all projects</span><b>2 overdue · 4 due this week</b></div>
          <div className="queue-list">{allActions.map((action, index) => <button className={framework === action.framework && index % 4 === 0 ? "selected" : ""} key={`${action.framework}-${action.title}`} onClick={() => onProjectChange(action.framework)}><i className={action.tone} /><div><span><Pill tone={action.framework === "CMMC" ? "neutral" : "good"}>{action.framework}</Pill><time>{action.due}</time></span><b>{action.title}</b><small>{projects[action.framework].client}</small><em>{action.kind} · {action.context}</em></div></button>)}</div>
        </aside>
        <section className="context-pane">
          <div className="context-top">
            <ProjectPicker active={framework} onChange={onProjectChange} compact />
            <div className="context-links"><button>Project overview</button><button>Open full record ↗</button></div>
          </div>
          <Identity project={project} />
          <div className="record-header">
            <div><Pill tone={project.actions[0].tone}>{project.actions[0].kind}</Pill><span>Due {project.actions[0].due}</span></div>
            <h2>{project.actions[0].title}</h2>
            <p>{project.actions[0].context}. Resolve the work here with the assessment, profile, evidence, and risk context kept visible.</p>
          </div>
          <div className="context-grid">
            <div className="work-detail">
              <div className="section-title tight"><div><span>Assessment context</span><h2>{project.requirements[0].id}</h2></div><Pill tone="warn">{project.requirements[0].status}</Pill></div>
              <h3>{project.requirements[0].title}</h3>
              <div className="objective-list">
                <div><i className="good">✓</i><span><b>Objective [a]</b><small>Implementation statement is present.</small></span></div>
                <div><i className="warn">!</i><span><b>Objective [b]</b><small>{project.framework === "CMMC" ? "Confirm technical enforcement against the enclave flow." : "Complete the addressable implementation decision."}</small></span></div>
                <div><i className="neutral">○</i><span><b>Validation</b><small>Evidence review and owner confirmation still required.</small></span></div>
              </div>
              <div className="section-title tight"><div><span>Progressive profile</span><h2>Relevant environment facts</h2></div><button>Open profile →</button></div>
              <ProfileTable project={project} />
            </div>
            <aside className="evidence-rail">
              <h3>Supporting context</h3>
              <span className="rail-label">Evidence mappings</span>
              {project.evidence.map((item) => <div className="rail-item" key={item.title}><i className={item.tone} /><span><b>{item.title}</b><small>{item.mappings}</small><em>{item.review}</em></span></div>)}
              <span className="rail-label">Risk</span>
              <div className="risk-block"><b>{project.risks[0].title}</b><div><Pill tone="bad">{project.risks[0].inherent}</Pill><span>→</span><Pill tone="warn">{project.risks[0].residual}</Pill></div><small>Owner · {project.risks[0].owner}</small></div>
              <span className="rail-label">Policy & review</span>
              <div className="policy-line"><b>{project.policies[0].title}</b><span>{project.policies[0].state}</span><small>Review {project.policies[0].review}</small></div>
              <span className="rail-label">Issue gate</span>
              <div className="issue-gate"><b>{project.reports[0].title}</b><p>{project.reports[0].readiness}</p></div>
            </aside>
          </div>
        </section>
      </main>
      <div className="experimental-tag">EXPERIMENTAL · SYNTHETIC DATA</div>
    </div>
  );
}

function PrototypeSwitcher({ current, onChange }: { current: VariantKey; onChange: (key: VariantKey) => void }) {
  const variants: VariantKey[] = ["A", "B", "C"];
  const cycle = (direction: number) => {
    const next = (variants.indexOf(current) + direction + variants.length) % variants.length;
    onChange(variants[next]);
  };
  useEffect(() => {
    const handleKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (["INPUT", "TEXTAREA"].includes(target.tagName) || target.isContentEditable) return;
      if (event.key === "ArrowLeft") cycle(-1);
      if (event.key === "ArrowRight") cycle(1);
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  });
  return (
    <div className="prototype-switcher" aria-label="Prototype variant switcher">
      <button onClick={() => cycle(-1)} aria-label="Previous variant">←</button>
      <div><small>PROTOTYPE VARIANT</small><b>{current} — {variantNames[current]}</b></div>
      <button onClick={() => cycle(1)} aria-label="Next variant">→</button>
    </div>
  );
}

function getVariant(): VariantKey {
  const value = new URLSearchParams(window.location.search).get("variant")?.toUpperCase();
  return value === "B" || value === "C" ? value : "A";
}

function App() {
  const [variant, setVariant] = useState<VariantKey>(getVariant);
  const [framework, setFramework] = useState<Framework>("CMMC");
  const changeVariant = (next: VariantKey) => {
    const url = new URL(window.location.href);
    url.searchParams.set("variant", next);
    window.history.replaceState({}, "", url);
    setVariant(next);
  };
  const props = { project: projects[framework], framework, onProjectChange: setFramework };
  return (
    <>
      {variant === "A" && <VariantA {...props} />}
      {variant === "B" && <VariantB {...props} />}
      {variant === "C" && <VariantC {...props} />}
      <PrototypeSwitcher current={variant} onChange={changeVariant} />
    </>
  );
}

createRoot(document.getElementById("root")!).render(<StrictMode><App /></StrictMode>);
