# Competitor UX research: GRC platforms for MSPs, MSSPs and consultants

Research date: 2026-10-08. Track: multi-client, consultant-oriented GRC tools.

**Source labels used throughout**
- **[HELP]**: vendor help center, knowledge base, user guide, or release notes. These are the most reliable for how the product actually behaves.
- **[MKT]**: vendor marketing page, blog, or press release.
- **[REVIEW]**: user reviews (G2, Capterra, vendor community posts by customers). G2 and Capterra pages returned HTTP 403 to direct fetches, so review quotes come from search-result snippets of those pages. They are marked as such and should be spot-checked.
- **[3P]**: third-party analysis such as press reviews or comparison blogs. Many are written by competitors and are flagged where that applies.

**Access limits.** Direct fetches of G2 and Capterra were blocked. Reddit searches for r/msp and r/CMMC turned up no threads about these specific products, so this report has **no verified Reddit quotes**. ControlMap's Zendesk help center blocked page fetches, but its public Help Center API returned the full article bodies, so the ControlMap help-doc coverage is strong.

---

## 1. Kaseya Compliance Manager GRC (formerly RapidFire Tools Compliance Manager)

Sources: the current online help at `www2.rapidfiretools.com/cm-grc/help/...` [HELP], and the older *Compliance Manager for CMMC User Guide* dated 2023-11-03 [HELP, legacy product, but it shows how the lineage approaches CMMC].

### 1.1 Core assessment workflow
- **Setup before assessing:** you create an Organization, then a Site (the client), then select Standards and Controls. The dashboard shows a "Standards Coverage" radial graph for each selected standard. Covered requirements show green and uncovered ones red. [HELP] https://www2.rapidfiretools.com/cm-grc/help/cm-grc-docs/standards-controls-cm-grc.htm
- **Three assessment tiers** [HELP] https://www2.rapidfiretools.com/cm-grc/help/cm-grc-docs/assessments/cm-grc-assessments.htm
  1. **Rapid Baseline Assessment:** a guided survey that can take "under an hour". It does not require answering every question. It is positioned for sales prospecting.
  2. **Controls Assessment:** the "official exam" that follows the baseline "pre-test". Every question must be answered.
  3. **Requirements Assessment:** answers the official requirements of each standard directly. It can be done instead of the Controls Assessment.
- **Unit of work on screen: one control or requirement per screen, wizard style.** Each screen shows overall progress, the question number, the label, the description, implementation guidance, the response options, a comment box on the right, and file attach. "Next" advances to the following item. "View All Questions as List" shows every item with color-coded status, and clicking a row jumps back into the wizard. [HELP] https://www2.rapidfiretools.com/cm-grc/help/cm-grc-docs/cm-grc-begin-controls-assessment.htm
- **Status vocabulary**
  - Controls Assessment: "Yes, Fully" / "Yes, with Technical Issues" / "Yes, Partially" / "No". "Yes, with Technical Issues" is available only after the automated Technical Review scan has run. [HELP, link above]
  - Requirements Assessment: "Addressed by Controls" / "Addressed" / "Not Addressed". "Addressed by Controls" is available **only when every linked control is "Yes, Fully"**. A "Related Controls & Assessments" panel shows the control answers beside the requirement. [HELP] https://www2.rapidfiretools.com/cm-grc/help/cm-grc-docs/cm-grc-begin-requirements-assess.htm
  - Rapid Baseline: full, partial, none, or **"unsure"**. [HELP] https://www2.rapidfiretools.com/cm-grc/help/cm-grc-docs/rapid-baseline-assessment.htm
- **Bulk actions:** in list view, the dropdown beside "Select All" sets one response on many questions. "Change Comment" bulk-sets comments, and the docs warn that it overwrites existing comments. [HELP, both links above]
- **Answer carry-forward:** "Import Baseline Responses" pulls Rapid Baseline answers into the Controls Assessment, with a side-by-side comparison so you choose which to import. [HELP, controls link]
- **Legacy CMMC product (2023 guide).** The assessment was a numbered **To Do list of about 33 tasks**: create users and roles, report preferences, install a scan server, run scans, then complete worksheets for External Port Use, Anti-virus, User Access Review, Asset Inventory, and so on. Next came **one worksheet per CMMC domain** (Access Control, Audit and Accountability, and the rest), an optional "NIST 800-171 Scoring Supplement" worksheet, and finally a Compensating Controls worksheet. Each worksheet entry is a topic with instructions, a response (Text, Multiple Choice, or Checklist), optional notes, and an optional respondent name. [HELP] https://www2.rapidfiretools.com/cm/Compliance_Manager_CMMC_User_Guide.pdf
  - Spreadsheet-like conveniences: drag-select multiple fields, then Ctrl+C / Ctrl+V responses across rows.
  - **Hard lock:** "Once you mark a worksheet as complete, you cannot re-open that worksheet unless you restart the assessment."
  - Progress bar on the Site Dashboard, with the number of remaining To Do items shown on hover.
  - "Show Guidance" opens a sidebar with per-question help.
- **Roles:** questions can be assigned to individuals or groups, and each user gets a "My Work" portal of assigned questions. Subject-matter experts (SMEs) and auditors get filtered log-ins. [MKT] https://www.compliancemanagergrc.com/features/

### 1.2 Evidence and status
- Evidence is **optional and attached inline** on each question ("Upload Local File" or attach a previously uploaded file). Nothing in the docs says evidence must exist before a positive answer. [HELP, controls and requirements links]
- Automated scans (LAN, endpoints, M365, external vulnerability) produce **system evidence** that can contradict human answers. The product "highlights exceptions where they do not match". [MKT] https://catalog.appdirect.com/en-US/apps/439604/compliance-manager-grc-a-kaseya-company/features
- Attachments flow automatically into the generated reports as supporting documents. [HELP, 2023 guide p.168]

### 1.3 Progress and dashboard
- Results dashboard: a **radial graph of compliance status** plus a Responses list, with Excel export. [HELP, controls link]
- An "interactive score sheet" applies the DoD methodology to compute the NIST SP 800-171 DoD Assessment Score (the SPRS number). [MKT] https://www.compliancemanagergrc.com/standards/cmmc/
- A Multi Sites View dashboard covers all sites. [MKT, features link]

### 1.4 Output generation
- Path: **Compliance Manager GRC > Results & Evidence > Reports > "Generate Reports"**. Wait for the build, then download individual files or "Download .zip". "Regenerate Reports" rebuilds after changes. You "will be unable to generate reports unless you have performed at least a basic assessment." [HELP] https://www2.rapidfiretools.com/cm-grc/help/cm-grc-docs/cm-grc-generate-reports.htm
- The CMMC 2.13 Level 2 report set is the **Assessment Report (.docx), Assessor Checklist (.xlsx), NIST SP 800-171 DoD Assessment Score Report (.docx), and System Security Plan (.docx)**. Separate POA&M spreadsheet with Technical, Control, Requirement, and VulScan tabs. [HELP] https://www2.rapidfiretools.com/cm-grc/help/cm-grc-docs/cm-grc-all-reports.htm
- Gotcha: if CMMC L2 and NIST 800-171 are both selected, the SSP and score reports reflect only CMMC. To get NIST-based reports you must **deselect CMMC** in the site's standards. [HELP, same link]
- POA&M is a separate lifecycle: **Generate > Review and Remediate** (implementation status, milestones, scheduled completion) **> Export Issues** (to Autotask or myITprocess) **> Regenerate** (archives the prior version). It requires the "entire assessment process" to be complete first. [HELP] https://www2.rapidfiretools.com/cm-grc/help/cm-grc-docs/cm-grc-plan-of-action.htm
- myITprocess imports only issues marked "Not Implemented", and only after a POA&M has been generated. [HELP] https://help.myitprocess.kaseya.com/help/Content/setup-admin/compliance-manager-integration.html
- Step count from finished answers to an SSP: about 3 clicks, but it is gated on the whole process being complete, plus an asynchronous build wait.

### 1.5 Navigation
- Hierarchy is Organization > Site > module, with left-menu sections such as Assessments, Forms, and Reports. The legacy product was driven by its To Do list. The current product uses wizard-per-question plus list view. [HELP, 2023 guide; GRC help links]

### 1.6 User praise and complaints
- [REVIEW, Capterra via search snippet] "It's not at all intuitive and not easily navigable", said of setting up a HIPAA risk assessment. https://www.capterra.com/p/194233/Compliance-Manager/reviews/
- [REVIEW, Capterra snippet] One reviewer said the move away from a **question-driven interface** means more time spent reviewing the standard to work out what counts as compliant. https://www.capterra.ca/reviews/194233/compliance-manager
- [REVIEW, Capterra snippet] "Yet another exceptionally adequate kaseya product… really expensive for what it is." Others note that new releases break things and a "Sev-1" went unanswered for days. Another said the product "lacked a lot in the CMMC realm". Users asked for mapping of control areas between domains and "integrated evidence cataloging". https://www.capterra.com/p/194233/Compliance-Manager/reviews/
- [REVIEW, Capterra snippet] Praise: the "prompted questionnaire approach" simplifies the work, and being able to bundle HIPAA and PCI assessments that used to be separate efforts. Same Capterra links.
- [REVIEW, G2 aggregate via comparison-page snippets] Ease of Use 7.8 vs a category average of about 8.9. The top con themes are "Lack of Guidance" and "Difficult Setup". https://www.g2.com/compare/compliance-manager-grc-vs-vanta

### 1.7 Multi-framework and answer reuse
- Controls are the shared layer: "your controls can meet the requirements of multiple standards", so the Controls Assessment produces evidence for several standards at once. [HELP, standards-controls link]
- **Re-use Previous Responses** for annual reassessments: a "Use Previous Response" button under each field, "View Previous Responses" for tables, and "Use All Previous Responses" for a whole form. [HELP, 2023 guide p.176–177]

---

## 2. ScalePad ControlMap

Sources: help center articles (bodies pulled from the public Zendesk Help Center API at `help.controlmap.io/api/v2/help_center/en-us/articles.json`, article URLs cited individually) [HELP], plus ScalePad product updates [MKT].

### 2.1 Core assessment workflow
- **Navigation:** an MSP Dashboard lists client tenants in Card or List view. Each card has "Launch" and "Overview" buttons and Progress, Framework, and Details tabs. "Prospect tenants" can run a **Pre-Assessment and Pre-Assessment Report without consuming a license**, which is a sales funnel built into the product. [HELP] https://help.controlmap.io/hc/en-us/articles/28209652130331-MSP-Multi-Tenant-Dashboard
- **Inside a tenant:** go to Frameworks, click "New Framework", then "Import Content" (which brings in the framework, its mappings, and the task work). [HELP] https://help.controlmap.io/hc/en-us/articles/18161192714651-Frameworks
- **Unit of work: the assessment question.** Questions are global and crosswalked: "Assessment questions in ControlMap are global and often crosswalk to or are mapped between multiple frameworks so that a single question answered once is answered across multiple frameworks." [HELP] https://help.controlmap.io/hc/en-us/articles/41951021929115-Working-with-Framework-Assessment-Snapshots
- **Answer vocabulary: Yes / No / Partially / Not Applicable.** [HELP] https://help.controlmap.io/hc/en-us/articles/52228236674715-Assessment-questions-missing-or-unexpectedly-appearing-in-the-Assessment-list
- **Scoping drives the question list.** Marking an objective out of scope hides the questions that map only to it. A question stays visible if any of its mapped objectives is in scope. Users have been confused by questions "unexpectedly appearing", which needed a dedicated help article. [HELP, same link]
- **CMMC specifics:** "Assessment by requirement/objective, and sub-objectives", and NIST SP 800-171A questions mapped to framework objectives. [HELP] https://help.controlmap.io/hc/en-us/articles/29270822904091-CMMC-Specific-Features
- **Audit mode is a separate module.** Since June 2026, new CMMC audits can be worked at the sub-objective or control level, with outcomes **Met / Met with exceptions / Not Met** and methods **Examine / Interview / Test**. Each sub-objective is "its own auditable item" that rolls up to the parent control. [MKT] https://www.scalepad.com/updates/controlmap-adds-sub-objective-level-cmmc-auditing-with-emass-ready-reporting
- **Answering "No" can spawn a risk directly** (January 2025 release). [HELP] https://help.controlmap.io/hc/en-us/articles/33693378706843-2025-Release-Notes

### 2.2 Evidence and status
- Evidence is driven by **Evidence Requests**: placeholders that carry an assignee, due date, and recurrence. Files are dragged onto a request, and the request maps to objectives. For CMMC, ControlMap ships sample CSVs from C3PAOs to **bulk-create 320 sub-objective evidence placeholders**. If no date is set, "overdue will be shown". [HELP] https://help.controlmap.io/hc/en-us/articles/51597016708891-Importing-Evidence-Requests-Bulk-CSV-CMMC-GTIA-Examples
- Evidence is a separate track from assessment answers. Answering an assessment question does not require evidence. Evidence status (Completed / In progress / Review / Not started / N/A) feeds the health score independently. [HELP] https://help.controlmap.io/hc/en-us/articles/35547294075803-Client-Dashboard
- **Pain point:** files a client attaches to an assessment answer land in a Documents tab and do not become evidence. A community post asking how to fix this had no answer. [REVIEW / community] https://community.scalepad.com/controlmap-59/how-to-attach-assessment-supporting-artifact-as-evidence-directly-in-controlmap-4641
- "Refresh Evidence" creates new requests with a new due date for the next audit while keeping history. [HELP] https://help.controlmap.io/hc/en-us/articles/18164819008539-Working-with-Evidence
- CUI guidance: "Do not upload CUI… link to it from ControlMap." Evidence can be a link to an external location. [HELP, CMMC Specific Features]

### 2.3 Progress and dashboard
- **SPRS score sits on the CMMC / NIST 800-171 framework card.** Clicking it opens a side panel with a per-objective point breakdown. A help article exists because users thought the score was wrong: answered objectives display "+1" for readability but count as 0. [HELP] https://help.controlmap.io/hc/en-us/articles/52340739755803-SPRS-score-appears-incorrect
- The CMMC marketing page shows a domain readiness view (AC, AT, AU and so on, with yes/partial/no counts and gaps per family, e.g. "IR 42%, 5 gaps"), "142 of 320 questions answered", and a progress-history trend line. [MKT] https://www.scalepad.com/controlmap/cmmc
- **Client Dashboard** (Q1 2025) with tabs Summary, ToDo, and Comparison. A **Compliance Health Score** blends documents, evidence, objectives, assessment, risk, action items, and scans, scored as Yes=1, Partial=0.5, No=0, N/A out of scope. The ToDo tab has Kanban boards for action items, policies, and evidence. [HELP, Client Dashboard link]

### 2.4 Output generation
- CMMC outputs: SPRS calculator, **SSP report builder**, POA&M management, Shared Responsibility Matrix, and an "Evidence exporter with evidence grouped by objective". [HELP, CMMC Specific Features]
- An eMASS-ready assessment results report: "More than 90% of report fields can now be populated from data already captured." [MKT, June 2026 link]
- The July 2026 release notes fixed "SSP report formatting" and "Word formatting on exported documents". The December 2025 notes mention "clearer failed states" for report generation. Report generation has evidently been a reliability pain point. [HELP] https://help.controlmap.io/hc/en-us/articles/46514811423771-2026-Release-Notes and the 2025 notes link above.
- Not verified: the exact number of clicks from a finished assessment to an SSP document.

### 2.5 Navigation
- MSP portal (top nav: Tech Stacks, Frameworks, Documents, Assessments, Integrations) > Launch tenant > tenant top-level modules (Frameworks, Controls, Evidence, Policies, Risks, Audits, Assets, Vendors). [HELP, MSP Dashboard; Tech Stacks; Custom Frameworks]
- The MSP portal holds central libraries of custom assessments and policy templates, which you push to tenants with "Share". [HELP, MSP Dashboard link]

### 2.6 Praise and complaints
- [REVIEW, G2 AI summary via snippet] Reviewers find it "centralized and easy to navigate". Complaints include a "learning curve… especially with loading times and locating features", "setup… overly complex", SSO friction between the MSP portal and a tenant, and slowness on large data. https://www.g2.com/products/scalepad-controlmap/reviews?qs=pros-and-cons
- [REVIEW, ScalePad community] Unanswered requests to export assessment questions with guidance, to attach risks to assessment questions, and to auto-populate mapped policies (one user: "I connected them manually"). https://community.scalepad.com/controlmap-59/export-include-guidance-with-assessment-questions-in-controlmap-4570 and https://community.scalepad.com/controlmap-59/how-to-attach-risks-to-assessment-questions-4927
- [MKT] Annual reassessment pain was what drove the Snapshot feature: "MSPs told us that refreshing assessments each year was repetitive and time-consuming." [HELP, Snapshots link]

### 2.7 Multi-framework and reuse (the strongest of the tools reviewed)
- Global crosswalked questions: answer once, counted everywhere. [HELP, Snapshots]
- **Assessment Snapshots:** "Take a Snapshot". Then choose "Clear all answers" or "Keep all answers", and the previous answer stays visible on screen for reference. Snapshots can be restored, and scores and reports update instantly. [HELP, Snapshots]
- **Tech Stacks** (June 2026): the MSP builds a product library once, and each product maps to the controls it satisfies. Sharing a stack **pre-answers matching assessment questions**, "with a review step before any auto-answer is accepted". [HELP] https://help.controlmap.io/hc/en-us/articles/52057842170523-Tech-Stacks and [HELP, 2026 Release Notes]
- Tenant cloning and Custom Frameworks (domains > levels > objectives, mapped to the question library). [HELP] https://help.controlmap.io/hc/en-us/articles/53446650160155-Custom-Frameworks

---

## 3. Cynomi (AI vCISO platform)

Sources are mostly marketing and a sponsored hands-on review. **No public help center was found**, so the UX detail is thinner than for the tools above.

### 3.1 Core assessment workflow
- An **infrastructure onboarding questionnaire** first. Its answers generate "a tailored set of short follow-up questionnaires". Questionnaires "can be revised at any time… Policies will be automatically updated accordingly." [3P, sponsored hands-on review] https://thehackernews.com/2024/04/hands-on-review-cynomi-ai-powered-vciso.html
- **Unit of work: topical sections** (e.g. "Network Security", "Data Protection"), each with a status (In Progress / Completed), a counter such as "18 of 24 answered", and a "Continue" or "View Questionnaire" action. Sections are tagged "Mapped to action". [MKT] https://cynomi.com/platform/assessments/
- **AI-suggested answers:** "suggests answers wherever it has relevant information, with confidence, reasoning and sources", and the team confirms them. [MKT, same link]
- Exact answer types (yes/no, maturity scale) are **not verified**.
- Vendor claim: "Onboard, assess and start proving value in under 60 minutes." [MKT, same link]

### 3.2 Evidence and status
- The model is task-centric rather than evidence-centric. Each policy requirement becomes a **task** with severity and status. Tasks can be deferred "without affecting policy status or severity". [3P, Hacker News review]
- How evidence attaches to tasks or controls is **not verified**.

### 3.3 Progress and dashboard
- "Overall security posture score", a risk score per threat vector, and compliance status per framework, "updated continuously". [3P, Hacker News review]
- Compliance module: a per-framework dashboard, a drill-down to controls showing implementation state and linked tasks, and "Switch between security and compliance views". [MKT] https://cynomi.com/blog/compliance-module-sep2023/
- **No SPRS score, SSP, or POA&M feature is documented for CMMC.** CMMC L1/L2 and NIST 800-171 are listed as frameworks only. [3P / MKT links above]

### 3.4 Output generation
- Three branded reports per client: Full, Risk Findings, and Compliance. [3P, Hacker News review] Generated policies are editable. Report-generation steps are not documented publicly.

### 3.5 Navigation
- A partner account holds one sub-account per client, with "admin-level cross-account visibility". [3P, Hacker News review]

### 3.6 Praise and complaints
- [REVIEW, G2 via snippet] "room for improvement in customization and report branding". Another reviewer said CMMC gets "very expensive for organizations with multiple locations". https://www.g2.com/products/cynomi-vciso-platform/reviews
- [REVIEW, Capterra via snippet] Questionnaires described as a valuable part of the product. https://capterra.com/p/10005060/Cynomi/reviews/
- [3P, competitor-written] Frameworks are fixed, and the inability to upload regional regulations was called a "major showstopper". https://fortifydata.com/blog/cynomi-competitors-and-alternatives/

### 3.7 Multi-framework
- "One assessment maps to 40+ frameworks." Every task is mapped to frameworks. [MKT] https://cynomi.com/platform/assessments/

---

## 4. Apptega

Sources: the Apptega community (Vanilla forum, read through its public API), vendor news, and third-party reviews.

### 4.1 Core assessment workflow
- Two layers. The **Assessment Manager** is questionnaire-based gap analysis. The **framework program** is Control > Sub-control, scored continuously. A **"Score Program" button syncs assessment data into a framework program**, and "Question responses can be setup to auto score framework subcontrols. Notes, Recommendations, Documentation, and Risks will sync." [HELP / community, Oct 2024] https://community.apptega.com/discussion/127/tip-tuesday-understanding-custom-assessments-in-apptega
- **Response-type menu** (from the custom assessment guide): Yes/No/Partially/Not Applicable; Met/Not Met/Partially Met/Not Applicable; Implemented/Partially Implemented/Alternative Implementation/Not Implemented/Not Applicable; a 0–5 scale; vendor-defined multiple choice; free text. [HELP / community, same link]
- Assessments are split into categories and subcategories that can be **assigned to different people or departments**. [same link] The CMMC Assessment Manager (2020) let "topics" be split across SMEs. [MKT] https://www.apptega.com/news/cmmc-assessments-now-supported-in-the-apptega-assessment-manager
- The **new Assessment Manager (2025-10-16)** promised a "modern, streamlined UI… complete assessments up to 50% faster", "Improved visibility into sub-controls", and "Bulk-upload and drag-and-drop options to easily ingest evidence". [MKT / community] https://community.apptega.com/discussion/200/introducing-apptega-s-new-assessment-manager
- **Focused control view (proposed June 2024):** one control per page, breadcrumbs to upper layers, a dropdown to sibling controls, and a "control finder" for deep layers. This replaced "scrolling for several miles to get to the section you need". [MKT / community, PM post] https://community.apptega.com/discussion/56/proposed-update-focused-control-view-and-new-navigation-tools
- CMMC v2.13 (final rule) framework, assessment, and task packs for L1 and L2 were released 2025-04-23. [community] https://community.apptega.com/discussion/174/cmmc-v2-13-the-cmmc-final-rule-is-now-available
- The KB articles "How does the assessment manager work" (#207) and "FAQs" (#203) return 404 publicly. Screen-level detail is **not verified**.

### 4.2 Evidence and status
- Evidence, notes, recommendations, and risks attach per question and sync to sub-controls on "Score Program". [community, #127] Whether evidence is required for a positive score is **not verified**.

### 4.3 Progress and dashboard
- A "progress" percentage in the page header. A customer critiqued it in the June 2024 mockup thread (see 4.6).

### 4.4 Output generation
- SSP and POA&M reports for CMMC. [MKT, 2020 news link] The current export format is not public and was untested by a third-party reviewer. [3P] https://thedefensecompliancereport.com/apptega-cmmc-review/
- That reviewer also could not confirm how the CMMC score is calculated. They noted Apptega's guide says Level 1 has 17 controls (the rule has 15) and cites a 90-day POA&M window (the rule says 180). [3P, same link]

### 4.5 Navigation
- Top-level areas named "Assess, Build, Manage, VRM". [REVIEW, customer comment in #56] Partner Command Center for cross-client metrics and bulk actions "rather than logging into each client individually". [3P] https://soc2-auditors.com/insights/apptega-review

### 4.6 Praise and complaints
- [REVIEW, customer comment on the vendor's mockup thread, 2024-06-24] "Love the breadcrumbs. Put them everywhere. But where am I? Assess, Build, Manage, VRM?… Why 3 representations of a 22% metric?… How is 'progress' measured? the control was touched? the control was scored?… can we really leave all this white space unused?" https://community.apptega.com/discussion/56/proposed-update-focused-control-view-and-new-navigation-tools
- [REVIEW, G2 / Capterra via snippets] "very slow when moving between controls on the same page"; interface "unintuitive and overly cluttered"; support suggested exporting to a spreadsheet to search; "somewhat complex for users who are new". https://www.capterra.com/p/180590/Apptega/reviews/ and https://www.g2.com/products/apptega/reviews
- [3P summary of G2 and Capterra] Praised for ease of use, multi-framework management, and the central dashboard. Criticized for "scoring clarity", report formatting, and slow pages. https://thedefensecompliancereport.com/apptega-cmmc-review/

### 4.7 Multi-framework
- **Harmony** crosswalks a single control set across frameworks, CMMC and NIST 800-171 included. [MKT] https://www.apptega.com/compliance-guides/cmmc-compliance-guide/ The crosswalk is on the Plus and Premium tiers. [3P, Defense Compliance Report]

---

## 5. Vanta and Drata: MSP and partner offerings

### Vanta
- An MSP Partner Program has existed since 2022–2023, advertising a "Multi-tenant management console for easy client management". [MKT] https://www.businesswire.com/news/home/20230301005504/en/Vanta-Accelerates-Global-Growth-With-New-Managed-Service-Provider-Partner-Program-Launch and https://www.vanta.com/resources/how-msps-unlock-growth-with-vantas-service-partner-program
- **No public help documentation of the console UX was found**, so there is nothing verified on how partners switch clients or what the cross-client view shows. The core product is built around continuous automated tests and evidence, not a consultant-run interview assessment. It is a poor analog for RainTech's assessor workflow.

### Drata
- **Multi-Instance Management (MIM)** dates from 2023. The dashboard has Account, Workspace, and Framework sections. Per account it shows active and failing connections, approved policies, % passing and failing tests, % personnel onboarded, and risk assessment completion. Per framework it shows a readiness %, with frameworks under 100% in a "red badge" and complete ones in blue. Search is by account name or domain only. The article does not explain how to switch into an account. [HELP] https://help.drata.com/en/articles/9677750-mim-dashboard
- For CMMC, a third-party review found **no documented SPRS scoring, SSP generation, or assessor-facing UI**. Drata organizes controls and evidence, and the customer writes the SSP and enters SPRS. [3P] https://thedefensecompliancereport.com/drata-cmmc-review/
- Takeaway: neither tool is built for a consultant running interview-style assessments across many small clients. Both are continuous-monitoring products with a portfolio roll-up added on top.

---

## 6. Other consultant-oriented tools: verification

| Name asked about | Verified? | Notes |
|---|---|---|
| **Blacksmith InfoSec** | Real | Multi-tenant compliance-as-a-service platform for MSPs, with ConnectWise and HaloPSA integrations, white-labeling, and policy templates. CMMC support is claimed only by a third-party review. "Minimal online presence and user reviews". [3P] https://www.toolsforhumans.ai/ai-tools/blacksmith-infosec ; [MKT] https://marketplace.connectwise.com/blacksmith-infosec |
| **CyberSierra** | Real company (Singapore), **not consultant-oriented** | Positions itself as a *replacement* for consultants for mid-market companies. No multi-tenant or partner licensing found. [MKT] https://www.cybersierra.co/blog/cost-effective-grc-alternatives |
| **"Galaxy"** | **Could not verify** | No GRC, MSP, or CMMC product by that name was found. Treat it as nonexistent unless someone provides a URL. |
| **Compliance Scorecard** | Real, MSP-native | "Governance-as-a-service" built around the 4A policy model. Assessment results become a "Compliance Control Assessment" PDF, risks go to the risk register "with a single click", and POA&M responses are Accept / Mitigate / Transfer / Avoid / Defer. Available on Pax8. [3P press] https://www.helpnetsecurity.com/2024/06/10/compliance-scorecard-msps-cybersecurity/ ; https://www.channele2e.com/news/compliance-scorecard-joins-pax8-marketplace-to-streamline-compliance-for-msps |
| **IntelliGRC** | Real, CMMC-focused, MSP / MSSP | Seed round of $3.5M (2026). Advertises SSP and POA&M creation and assessment reporting. No public help docs. [3P] https://fintech.global/2026/03/05/grc-platform-intelligrc-bags-3-5m-to-scale-compliance-tech/ |
| **FutureFeed** | Real, CMMC-specific | Gap assessment, SPRS score calculation, automatic SSP and POA&M generation, evidence, audit packages, and GovCloud storage. A competitor claims its multi-client management is weak (unverified). [MKT] https://www.deltek.com/en/partners/futurefeed ; [3P, competitor] https://www.motherbearsecurity.com/blog/futurefeed-alternatives |

Category framing: the MSPAlliance taxonomy (written by a competitor that sells Cyber Verify) puts ControlMap, Compliance Scorecard, Apptega, Kaseya CM GRC, and Cynomi in "MSP-native GRC", and Vanta, Drata, and Secureframe in "SaaS compliance automation". https://mspalliance.com/msp-compliance-platforms

---

## 7. Cross-tool comparison

| | Unit of work | Items per screen | Status vocabulary | Evidence required for "met"? | SPRS shown | SSP / POA&M path |
|---|---|---|---|---|---|---|
| Kaseya CM GRC | Control or requirement (legacy: domain worksheet) | 1 (wizard) + list view | Yes Fully / Yes w/ Tech Issues / Yes Partially / No; Addressed by Controls / Addressed / Not Addressed | No, optional inline | Score report + interactive score sheet | Generate Reports (gated on completion) > .docx / .xlsx; POA&M separate Generate step |
| ControlMap | Crosswalked question; objective / sub-objective in Audit | List per framework (exact layout not verified) | Yes / No / Partially / N/A; Audit: Met / Met w/ exceptions / Not Met | No, separate evidence-request track | On framework card, click for breakdown | SSP builder, POA&M, eMASS export |
| Cynomi | Questionnaire section ("18 of 24") | Section | Not verified; AI-suggested answers | Task-centric | Not documented | Not documented for CMMC |
| Apptega | Question (assessment) > sub-control (program) | 1 control per page (focused view) | Configurable (Y/N/P/NA, Met/Not Met, 0–5, ...) | Not verified | Unverified | SSP / POA&M reports (format not public) |

---

## Patterns worth copying

1. **Wizard and list are two views of the same assessment, with one click between them** (Kaseya). A focused one-item screen showing the label, the guidance, the answer, a comment, and attach, with "Next". Next to it, a color-coded list of every item where clicking a row jumps back into the wizard. Bulk-set status and bulk-comment from the list. This is the most consistently documented assessor flow in this space.
2. **Answer at the 320-objective level, roll up to the 110 requirements automatically, and show the requirement and family roll-up live** (ControlMap audit mode: each sub-objective is "its own auditable item" that rolls up). Use the assessor vocabulary Met / Not Met / N/A, plus the method used (Examine / Interview / Test) as optional metadata.
3. **Keep the SPRS score always visible, with a click-through breakdown that shows the arithmetic** (ControlMap's framework-card score and side panel). Show "starts at 110, minus the weights of unmet requirements" explicitly. ControlMap needed a help article because its "+1" display didn't add up.
4. **Show progress as answered/total per family and overall** ("142 of 320 answered"; IR 42%, 5 gaps). Give a single, clearly defined metric, not three unexplained percentages (see the Apptega customer critique).
5. **Carry forward and reassess without re-keying.** Kaseya's "Use Previous Response" / "Use All Previous Responses" and ControlMap's Snapshots ("Keep all" vs "Clear all", with the previous answer shown beside the field). Version every snapshot so the assessment record is immutable.
6. **Let one answer feed many frameworks and one standard environment pre-answer many clients.** ControlMap's crosswalked questions and Tech Stacks (MSP builds the stack once, which pre-answers mapped questions, then a **review step before acceptance**). For a single consultant: reusable "client environment templates" whose suggested answers are always marked as unconfirmed.
7. **Give status-setting real follow-through.** ControlMap's "No" > create a risk, and Compliance Scorecard's one-click gap > risk register. In RainTech terms: Not Met > a POA&M or finding draft prefilled from the objective, in one action, without leaving the assessment screen.
8. **Keep a cheap first pass that is distinct from the formal assessment.** Kaseya's Rapid Baseline (under an hour, "unsure" allowed, not every question required) with import into the formal assessment. ControlMap's license-free prospect pre-assessment. This maps to RainTech's progressive profile.
9. **Make outputs a single action from the assessment and regenerable.** Kaseya's "Generate Reports > Download .zip > Regenerate" and POA&M "Regenerate (archives prior)". Bundle SSP + POA&M + SPRS score + assessor checklist as one package.
10. **Treat evidence placeholders as first-class.** ControlMap bulk-creates 320 evidence requests from C3PAO request lists, and evidence can be a *link* to where the CUI lives rather than an upload.

## Patterns to avoid

- **Irreversible completion steps.** Kaseya's legacy flow: "Once you mark a worksheet as complete, you cannot re-open that worksheet unless you restart the assessment." Reports are also gated on the "entire assessment process" being complete. Consultants need to iterate and produce draft outputs at any time.
- **Long serial To Do chains of about 33 numbered tasks** that mix infrastructure setup (scan servers, credentials) with assessment content. Keep setup separate and optional, and let the assessor go straight to answering.
- **Hidden scope effects.** ControlMap questions appear or disappear when objective scope changes, which needed a troubleshooting article. When scope changes the item set, say so on screen ("12 objectives hidden by scope; show").
- **Framework selection silently changing outputs.** Kaseya builds the SSP and score from CMMC only when both CMMC and 800-171 are selected, and the fix is to deselect a standard. Outputs must state their basis and never require un-selecting data.
- **Evidence split across disconnected places.** ControlMap client attachments land in "Documents" and don't count as evidence. Have one evidence store, and link attachments to the objective they were added on.
- **Ambiguous progress metrics and clutter.** Apptega's "3 representations of a 22% metric" and "where am I?". Also avoid slow transitions between items ("very slow when moving between controls"). In a local desktop app, item-to-item navigation must be instant.
- **Destructive bulk tools.** Kaseya's "Change Comment" overwrites existing comments. Bulk actions should append or preview, and be undoable.
- **AI or auto-answers without explicit confirmation state.** Cynomi's and ControlMap's suggestions are useful only because they carry confidence or sources and a review step. Never let a suggested answer count toward SPRS until confirmed.
- **Monitoring-first products as the UX model** (Vanta, Drata). Their portfolio dashboards (pass/fail test %, connections) do not fit an interview-and-examine assessor workflow, and neither documents SPRS or SSP generation for CMMC.
