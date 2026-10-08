# HIPAA Security Risk Assessment Tools: Competitor UX Research

Research date: 2026-10-08. Prepared for RainTech GRC (a local-first Windows desktop app for consultants; HIPAA track covers the Security Rule assessment, the SRA with a 5x5 risk model, corrective actions, evidence, and report packages).

## Source labels

- **[DOCS]** means an official user guide, help center, or training syllabus.
- **[GOV]** means a government source.
- **[MKT]** means vendor marketing.
- **[REVIEW]** means a third-party review site. G2, Capterra, GetApp and TrustRadius all returned HTTP 403 to direct fetches, so review quotes come from search-engine snippets of those pages. Each one cites the review page URL.
- **[PRESS]** means trade press, a law firm, or a third-party blog.
- **[OWN ANALYSIS]** means I derived it myself from a downloaded artifact.

## Coverage and what could not be verified

| Tool | Exists? | Depth of evidence |
|---|---|---|
| HHS/ASTP-ONC SRA Tool v3.7 | Yes | **Deep.** I read the full v3.7 User Guide and the Sept 2026 webinar deck, and parsed the v3.7 Excel workbook. |
| Clearwater IRM\|Analysis (in IRM\|Pro suite) | Yes | **Medium.** Official 2025 and 2026 training-lab syllabi describe the workflow phases. There are no public screen-level docs. |
| Accountable (AccountableHQ) | Yes | **Medium.** The public docs site has articles on assessment, remediation, reports and score. |
| HIPAA One (Intraprise Health, now "Intraprise Health by Health Catalyst") | Yes | **Shallow to medium.** I found marketing pages plus Capterra review snippets, but no public user guide. |
| Compliancy Group, The Guard | Yes | **Shallow to medium.** I found marketing pages, vendor-hosted testimonials and G2 snippets, but no public help docs. |
| Medcurity | Yes (extra) | **Shallow.** Marketing only. |
| Abyde | Yes | **Shallow.** Marketing only. Capterra has one rating and no written reviews were found. |
| HIPAA Ready (CloudApper AI) | Yes | **Shallow.** Marketing only. |
| HIPAAtrek, ComplyAssistant | Yes (extra) | **Directory listings only.** |
| **"Intraprise HealthSnap"** | **NOT VERIFIED** | I found no Intraprise product named HealthSnap. "HealthSnap" turns up as an unrelated remote-patient-monitoring company ([hitconsultant](https://hitconsultant.net/2026/08/10/healthsnap-secures-25m-financing-eastward-capital-ai-virtual-care/)). Intraprise's current products are HIPAA One, BluePrint Protect and a NIST assessment platform ([Health Catalyst page](https://www.healthcatalyst.com/products/intraprise-health-by-health-catalyst), [healthcaredive 2021](https://www.healthcaredive.com/press-release/20211007-intraprise-health-announces-nist-assessment-platform-automate-and-accelera)). `intraprisehealth.com/healthsnap/` returns 404. |

**Research gaps:**
- **Reddit:** r/hipaa, r/healthIT and r/msp could not be reached. Reddit blocks this agent's search and fetch user agent, both with `allowed_domains` and with direct requests. **No Reddit quotes are included, and none were invented.**
- **Review sites:** G2, Capterra, GetApp and TrustRadius block direct fetch. Quotes below are short excerpts taken from search-result snippets of those pages.
- **Demo videos:** none were viewed. I had no video access.

---

## 1. HHS / ASTP-ONC + OCR Security Risk Assessment (SRA) Tool v3.7

This is the most relevant comparator. **It is a free, local-first Windows desktop app**, which is the same form factor as RainTech.

**Version facts [GOV]**
- v3.7 is current. The HealthIT.gov page was "Last Updated: September 18, 2026" ([HealthIT.gov SRA page](https://healthit.gov/privacy-security/security-risk-assessment-tool/)), and HIPAA Journal reported the release on Sept 11, 2026 ([HIPAA Journal](https://www.hipaajournal.com/hhs-security-risk-assessment-tool-3-7/)).
- User Guide v3.7 PDF: https://healthit.gov/sra_tool_user_guide_version_3-7/
- Webinar deck: https://healthit.gov/wp-content/uploads/2026/09/SRA-Tool-Overview-2026_FINAL-1.pdf
- The tool also ships as an Excel workbook: https://healthit.gov/sra_tool_3-7_excel-workbook/
- Data stays local in an encrypted `.sra` file, and nothing is transmitted to HHS ([User Guide p.4, p.30](https://healthit.gov/sra_tool_user_guide_version_3-7/)).

### 1.1 Assessment flow [DOCS: User Guide v3.7]
- **Wizard style, one question per screen.** "Each question in the assessment portion requires a single answer from multiple choice options... one answer and only one answer must be selected to continue." Questions are numbered from Q1 within each section (p.18).
- **Structure: question-driven and grouped by safeguard theme.** There are 7 sections:
  1. SRA Basics
  2. Policies, Procedures & Documentation
  3. Workforce
  4. Your Data (technical)
  5. Your Practice (physical)
  6. Vendors
  7. Contingency Planning

  Each question cites the regulation in a Reference panel (HIPAA §, NIST CSF 2.0, HICP, HPH CPG) (pp.4–5, p.18).
- **Size (OWN ANALYSIS of the v3.7 workbook):** roughly 117 base questions before branching (S1 ~11, S2 8, S3 ~10, S4 ~30, S5 ~23, S6 ~15, S7 ~20). That gives 40 vulnerabilities and about 206 vulnerability-to-threat rows if every vulnerability were selected. Counts are from a heuristic parse, so treat them as ±5%.
- **Answer types:** graded multiple choice. Typically there is one "most effective" option plus partial options, "I don't know", sometimes "Other", and always **"Flag this question for later."** In the workbook each option carries a hidden 1/0 "risk indicated" value (OWN ANALYSIS, [workbook](https://healthit.gov/sra_tool_3-7_excel-workbook/)).
- **Skip logic:** branching within each section. For example, answering "No / I don't know / Flag" to "Has your practice completed an SRA before?" skips the follow-ups and jumps to Q5 (p.5).
  - The deck credits usability testing for this. The v3.0 redesign goals were "decoupling the questions from the legislative verbiage" and "Introduce branching logic to cut out unnecessary questions" ([NIST-hosted ONC/Altarum deck, v3.01](https://www.nist.gov/document/2-2-hhs-sra-tool-steffey-callahanpdf)).
- **Flag for later:** a flagged question counts as an Area for Review and appears in a **Flagged Report**. That report is "for reference purposes only and you cannot change your answer from that report" (p.18, p.23).
- **Contextual help:**
  - An **Education panel** shows guidance specific to the *selected* answer and is blank until you choose.
  - A **Reference panel** links citations.
  - A collapsible **Details** free-text box sits on every question.
  - Glossary terms are underlined with hover tooltips (pp.17–18).
- **Section summary** (p.20). After each section's questions and its threat ratings, a "Section Complete" screen shows:
  - "Areas of Success" and "Areas for Review", with expandable tiles holding the response and its education text
  - a percentage bar
  - an Export-to-PDF button
  - a "Jump to section start" button
  - an "Additional Information" text field
  - "+Documents" links
  - a **"Section Reviewed/Confirmed"** attestation button that stamps the username and date into the Detailed Report

### 1.2 Risk analysis [DOCS]
- **Assets and vendors are separate inventory screens** under Practice Info, with CSV bulk import and export. Asset fields are type, status, ePHI access, disposal status and date, encryption, assignment, location and ID (pp.12–16).
  - **Assets are NOT linked to threats or risk ratings.** They appear only in the Detailed Report.
- **How a user avoids rating every combination:** after each section, the user **ticks the vulnerabilities that apply** from a pre-written list. Only the threats under ticked vulnerabilities must be rated (pp.18–19).
  - Each vulnerability carries 2–6 pre-populated threats.
  - Each threat gets Likelihood and Impact rated L/M/H, with color coding: green, yellow, red.
  - Both ratings are required before Next is enabled. A warning makes you scroll back to any missed rows.
- **Matrix (Risk_Logic sheet, OWN ANALYSIS):** 3x3 inputs map to 4 outputs: Low, Moderate, High, Critical. The matrix is **asymmetric**:
  - L-likelihood with H-impact gives High.
  - H-likelihood with L-impact gives Moderate.
  - M with H, and H with H, give Critical.
- **Two different "scores" (a known source of confusion):**
  - "Risk Score" is the % of multiple-choice answers sorted into Areas for Review.
  - "Risk Rating" is likelihood × impact per threat.
  - The FAQ has to explain that the questions "do not affect the rating" (p.30).

### 1.3 Evidence [DOCS]
- Evidence is **linked, not imported**: "No documents are imported into and saved in the SRA tool... the tool allows users to save links to documents stored locally or on a local network" (p.16).
- Links can be added at three levels: the assessment (Practice Info/Documents), the section summary (+Documents), and each remediation item (+Link Documentation) (pp.16, 20, 24).
- Evidence is **never required**. The questions have a "Details" free-text field only.

### 1.4 Remediation [DOCS]
- The **Remediation Report** lists every Area for Review. Each item takes:
  - Remediation Activities (text)
  - Owner (free text)
  - Due Date
  - Date Completed
  - Link Documentation
- You must click "Save Remediation", after which the item becomes read-only until you click "Edit Remediation".
- Navigation is one page per section through a Sections Selector.
- This step is "optional to complete within the tool" (pp.23–24).
- Remediation is driven by question gaps, **not by rated threats/vulnerabilities**.

### 1.5 Reports [DOCS]
- **Gate:** "To access the reports available under the Reports menu, the assessment must be 100% completed" (FAQ p.28). Section PDFs can be exported earlier.
- **Report set:**
  - Summary: overall risk %, Areas for Review count, vulnerability count, and per-section %
  - Risk Report: pie chart of threat ratings, rating key, vulnerabilities with their threats, Areas for Review with education
  - Detailed Report: everything, in PDF or Excel, with a per-answer user and timestamp
  - Flagged Report
  - Remediation Report

  Sources: pp.21–25.
- Detailed Report caveat: the guide says section comments and the documents list are excluded (p.22), while v3.7 release notes say reports now include "all comments, details, and review data" (p.3). **The source contradicts itself.**

### 1.6 Progress and navigation [DOCS]
- A left nav lists the sections. A "white check mark" appears next to each completed section.
- Saving happens when you click Next or Save, and the tool prompts on exit.
- **Painful edit model:**
  - Opening a completed section drops you at its end (the summary), and you must click Back question by question.
  - Moving back removes the completion check mark. "To register as complete, you must navigate to the end of a section."
  - Changing one answer can open new branch questions (pp.29–31).
  - You cannot jump to a question from the Flagged Report.
- **Content versioning:** an SRA file keeps the content version it was created with. To get new questions you must start a new file, and the out-of-date warning "cannot be dismissed" (p.26).
- **Year over year:** the guide recommends Save As on last year's file, which keeps old content (FAQ p.28).

### 1.7 Praise and complaints
- **Vendor criticism [MKT, Compliancy Group, written about v3.0 (~2019)]** ([compliancy-group.com/hhs-sra-tool](https://compliancy-group.com/hhs-sra-tool/)):
  - "The tool essentially requires that the user be an omintasking risk technician."
  - "does not have an option that delegates particular questions to specific employees"
  - "does not save any historical data related to past or previous assessments" (partly outdated, since Save As is now documented)
- **Self-acknowledged limits [GOV]:** "the SRA Tool survey approach may not identify all risks" (User Guide p.3), and the tool "may not be appropriate for larger organizations" (p.4).
- **Usability testing [GOV, ~2019 deck]:** findings drove the move to a wizard, plain language, branching, and a modular flow "focusing on ease of use and time to complete" ([NIST-hosted deck](https://www.nist.gov/document/2-2-hhs-sra-tool-steffey-callahanpdf)).
- **Unverified:** Reddit user sentiment, because I could not access it.

---

## 2. Clearwater: IRM|Analysis (module of IRM|Pro)

Clearwater is the enterprise and health-system leader. Its model is **asset-centric, NIST SP 800-30 style**.

**Evidence:**
- [DOCS] Clearwater "OCR-Quality Risk Analysis Working Lab" syllabi for [2025](https://go.clearwatersecurity.com/hubfs/2025%20Webinars/2025_OCR_Quality-Risk-Analysis-Working-Lab_Program%20Syllabus.pdf) and [2026](https://go.clearwatersecurity.com/hubfs/2026%20Webinars/Risk%20Analysis%20Working%20Lab/2026_OCR_Quality-Risk-Analysis-Working-Lab_Program%20Syllabus.pdf)
- [PRESS] [Help Net Security 2020](https://www.helpnetsecurity.com/2020/03/25/clearwater-irmanalysis/)
- [MKT] [Predictive Risk Rating release, Mar 2021](https://clearwatersecurity.com/company-news/clearwater-extends-healthcare-cyber-risk-management-leadership-with-ai-driven-predictive-risk-rating-peer-to-peer-benchmarking-and-servicenow-integration-capabilities/)

**Workflow phases (from the 2026 syllabus titles):**
1. "Building a Complete ePHI Information Asset Inventory"
2. "Identifying Current Threats, Vulnerabilities, and Component-Level Risks"
3. "Defensible Risk Determination: Likelihood, Impact, and Risk Scoring"
4. "Reports, Dashboards, Risk Register Outputs, and Risk Response Planning"

### 2.1 Flow [DOCS]
- **Safeguard and control driven, not a question wizard.** The user builds Physical Locations, then Information Assets (systems), then the **Components** of each asset (software, hardware, networks, and so on). An "Asset Import Tool" supports bulk entry.
- Controls are answered **"globally (default) and at the Component Group level"**, with "Control Notes" and uploaded supporting documents.
- Quick Filters and a Filter Dialog navigate long lists.
- Screen-level details (items per screen, answer types) were **not verified**.

### 2.2 Risk analysis: the key pattern for scale [DOCS]
- **Component Groups:** "benefits of grouping systems by threat surface". New groups can be created with the "Asset Grouping Expert".
- The syllabus weighs "the pros and cons of using a 'Master Infrastructure' Asset for common Components versus selecting every relevant Component for each Asset", and teaches "Copying Risk Determination Information".
- Risk scenarios (threat × vulnerability combinations) are **pre-generated per Component Group**. "Control Responses and notes can affect Risk Rating", so answering controls once shifts many scenario ratings at the same time.
- **Predictive Risk Rating [MKT]:** ML trained on "more than a million risk ratings". "Risk rating recommendations can be automatically accepted or simply serve as guidance for the user."
- Embedded scenario library [PRESS]: e.g., org-issued laptops and phones, remote-access network components, and cloud/SaaS email and file sharing.
- Risks above the organization's threshold can be "accepted, transferred, avoided, or mitigated" ([Help Net Security](https://www.helpnetsecurity.com/2020/03/25/clearwater-irmanalysis/)).
- Exact likelihood and impact scales were **not verified**. Clearwater's published definition: "A risk rating is a function of the likelihood of a threat exploiting an... asset vulnerability and the impact" (per search snippet of the [Clearwater news page](https://clearwatersecurity.com/company-news/clearwater-extends-healthcare-cyber-risk-management-leadership-with-ai-driven-predictive-risk-rating-peer-to-peer-benchmarking-and-servicenow-integration-capabilities/)).

### 2.3 Evidence [DOCS]
- Control Notes and document upload on control responses. The 2025 syllabus stresses "the importance of documentation during a Risk Analysis".

### 2.4 Remediation [DOCS]
- "OneView" holds **Findings**, which can be created or imported. Activities are assigned to findings and tracked in an "Activities Manager" (2025 syllabus, Session V).

### 2.5 Reports [DOCS/MKT]
- "Reports and Enterprise Extracts", "Version History", and "Cyber-Security Intelligence Dashboards" (syllabus).
- Consulting deliverables include an "OCR-Ready Risk Register" plus an executive presentation (per search snippet of Clearwater materials).

### 2.6 Reviews
- **No product-specific reviews found.** Search results conflate it with Clearwater *Analytics*, an unrelated investment-software company.
- A Clearwater customer case study notes the customer could have self-run IRM|Analysis but lacked bandwidth (search snippet; [Clearwater case study](https://clearwatersecurity.com/case-studies/encompass-health/)). This suggests the tool is analyst-heavy.

---

## 3. Accountable (AccountableHQ)

**Evidence:**
- [DOCS] [Running a risk assessment](https://www.accountablehq.com/docs/running-a-risk-assessment)
- [DOCS] [Remediation plans](https://www.accountablehq.com/docs/remediation-plans)
- [DOCS] [Compliance reports](https://www.accountablehq.com/docs/compliance-reports)
- [DOCS] [Compliance score](https://www.accountablehq.com/docs/compliance-score)
- [DOCS] [Data inventory](https://www.accountablehq.com/docs/data-inventory)

### 3.1 Flow [DOCS]
- **Entry:** Compliance > Assessments. A first-time user starts a new SRA. Returning users see the last assessment and can "start new or continue a draft".
- **Content:** "seven categories of questions aligned with the HIPAA Security Rule".
- **Answer model:** "Each question has an answer, a free-text explanation, and an optional evidence upload." "You don't have to fill in all three on every question," though completeness improves the report and the score.
- **Copilot pre-fill:** "Compliance Copilot" proposes answers with reasoning from existing state (policies, training, BAAs, incident setup). "You confirm or edit before anything is saved."
- **Autosave:** "The assessment saves your progress as you go." Users can hand it to a colleague.
- **Submit:** requires every question answered. Submission "Locks the assessment as that point-in-time record", updates the score, and adds the assessment to reports.
- Items per screen and skip logic were **not documented**.

### 3.2 Risk analysis [DOCS]
- **No likelihood × impact or asset-threat model is documented** for the SRA. It is a compliance-questionnaire model.
- A separate **Data inventory** records where PHI lives: name, physical or digital, location details, estimated records, responsible person. It also supports timestamped attestations.
- The inventory feeds the score, but the docs do not say it feeds the SRA.

### 3.3 Evidence [DOCS]
- Optional per-question upload. Remediation items carry evidence.

### 3.4 Remediation [DOCS]
- Plans can be created from SRA findings, vulnerability scans, pentests or manual entry. Copilot can also build one: it "groups related findings, suggests priorities".
- **Lifecycle:** "draft → open → in progress → completed → verified".
- **Item fields:** priority (critical/high/medium/low), status, owner, target date, evidence.
- **Plan view:** shows % progress plus open, overdue and completed counts.

### 3.5 Reports [DOCS]
- **Steps:** Reports > new > choose **internal** or **external**. The tool snapshots current state, and the report is shared as a **PDF or signed link**.
- **Contents:** score, policies with version dates, training completion, vendor/BAA status, incidents, latest SRA responses, data inventory.

### 3.6 Progress [DOCS]
- **Dashboard gauge:** overall % with a tier (e.g., "Mature", "Achieving").
- **Seven weighted dimensions:** Team 30%, SRA 25%, Policies 15%, BAA 10%, Inventory 10%, IR 5%, Privacy Officer 5%.
- The docs call it "a signal — not a grade".

### 3.7 Reviews [REVIEW] (snippets)
- Capterra: 4.8 from 34 reviews. One reviewer said some areas "feel a bit rigid and less customizable" for complex environments ([Capterra](https://capterra.com/p/135001/Accountable/reviews/)).
- GetApp: "way too expensive" and "Lack of customer service" ([GetApp](https://www.getapp.com/operations-management-software/a/accountable/reviews/)).
- G2 has only a single review ([G2](https://www.g2.com/products/accountable-hq/reviews)).

---

## 4. HIPAA One (Intraprise Health; now marketed as "Intraprise Health by Health Catalyst")

**Evidence:**
- [MKT] [HIPAA One page](https://intraprisehealth.com/hipaa-one/)
- [MKT] [SRA page](https://intraprisehealth.com/hipaa-one/security-risk-assessment/)
- [MKT] [Health Catalyst page](https://www.healthcatalyst.com/products/intraprise-health-by-health-catalyst)
- [MKT/partner] [AdvancedMD marketplace](https://www.advancedmd.com/integrations/marketplace/hipaa-one)

**No public user guide was found.**

### 4.1 Flow [MKT]
- "Answer assessment questions with clear, automated guidance."
- "Import and store previous assessments and **auto-fill information that hasn't changed**."
- "Automate task reminders, team delegation."
- The partner listing claims it "automates over 82% of the tasks" ([AdvancedMD](https://www.advancedmd.com/integrations/marketplace/hipaa-one)). This is **unverified**.
- **Service tiers:** Self-Service, Hybrid ("Your internal team and our security experts work together"), and Managed Services. Enterprise "Parent-child synchronization" can "pre-populate assessments for multiple sub-entities" ([HIPAA One page](https://intraprisehealth.com/hipaa-one/)).

### 4.2 Risk analysis [MKT]
- "Identify threat sources and events", "Identify vulnerabilities", "Determine likelihood", "Determine magnitude of impact", all "based on NIST-methodologies".
- "System-generated risk ratings and remediation recommendations" in the Guided tier ([SRA page](https://intraprisehealth.com/hipaa-one/security-risk-assessment/)).
- Scale and asset linkage were **not verified**.

### 4.3 Evidence, remediation and reports [MKT]
- "Remediation Management module to address gaps and build your **Book of Evidence**."
- "Remediation tracking and action history."
- "Real-time, custom reporting" and a "Customizable report of findings."
- In the Validated tier, "Remediation recommendations reviewed and approved by your Assessor(s)."

### 4.4 Reviews [REVIEW] (Capterra 4.8 from 45 reviews; Ease of use 4.6) ([Capterra](https://www.capterra.com/p/130826/HIPAA-One/reviews/))
- Praise: "HIPAAOne tracks what my remediation is and gives me an area to show the auditor how I'm working on things."
- Praise: "Report was comprehensive and well received by Board."
- Complaint: "I do not come from a HIPPA background, so some help text would have been useful."
- Complaint: "So tedious to begin, can't always get assistance."

---

## 5. Compliancy Group: The Guard

**Evidence:**
- [MKT] [Automated HIPAA compliance](https://compliancy-group.com/automated-hipaa-compliance/)
- [MKT] [Risk assessment software](https://compliancy-group.com/hipaa-risk-assessment-software/)
- [MKT] [Homepage testimonials](https://compliancy-group.com/)
- [REVIEW] [G2](https://www.g2.com/products/compliancy-group-healthcare-compliance/reviews)
- [REVIEW] [TrustRadius](https://trustradius.com/products/compliancy-group-the-guard/reviews)

**No public help docs were found.**

### 5.1 Flow [MKT]
- **Six "self-audits"** for covered entities (five for BAs): Security Risk Assessment, Privacy, Physical Site, Asset & Device, HITECH Subtitle D, and Security Standards.
- "The self-audits are easy to complete, with most structured as yes or no questions."
- A vendor-hosted testimonial says: "The question and answer format... breaks complex regulatory language into manageable size chunks. Each question contains a simplified explanation of the regulation and links to policies" ([homepage](https://compliancy-group.com/)).
- **Human coaching is built into the flow:** "Compliance Coaches will review your gaps with you", and onboarding calls plus a "HIPAA risk assessment playbook" in the portal (testimonial).

### 5.2 Risk analysis [MKT]
- **Gap-based.** "The Guard automatically identifies gaps."
- No likelihood × impact or asset-threat UI is documented in public material, so it is **not verified**.

### 5.3 Evidence and remediation [MKT]
- Remediation plans are created with the coach or "automatically assigns remediation plans... with calendar dates by which gaps need to be remedied" (search snippet of [risk assessment software page](https://compliancy-group.com/hipaa-risk-assessment-software/)).
- Documentation is framed as proof of "good faith effort".

### 5.4 Reports and progress
- "Snapshot" and "risk profile" views are mentioned [MKT]. Details were **not verified**.

### 5.5 Reviews [REVIEW]
- G2 4.7 from 111 reviews. Several are seller-invited (G2 snippets, [G2](https://www.g2.com/products/compliancy-group-healthcare-compliance/reviews)).
- Praise: "easy to open a new assessment and just start ticking off answers".
- Praise: the 2025 portal updates "made the entire system much easier to utilize".
- Complaint: automatic reminder emails are keyed "based on the date that a question was originally answered", which reads as nagging.
- Complaint: "the website lags".
- Complaint: policies are "very long and not necessarily employee friendly".

---

## 6. Medcurity (additional tool)

**Evidence:** [MKT] [SRA software page](https://medcurity.com/hipaa-sra-software/)

- **Flow:** "asks about your infrastructure, staffing, workflows, and data handling" and maps the answers to Security Rule elements. The vendor says it adapts to your environment rather than "a generic checklist".
- **Risk:** scored by likelihood and impact into **three priority tiers**: critical, important, and lower-priority.
- **Remediation:** each risk gets steps, an owner and a deadline. Items are flagged as on track, overdue, or upcoming.
- **Reports:** executive reports show totals, remediation progress, critical items and trends, mapped to rule requirements.
- **Price:** "$499/year" for small practices.
- **Reviews:** none were checked.

## 7. Abyde

**Evidence:**
- [MKT] [abyde.com](https://abyde.com/)
- [MKT] [SRA page](https://abyde.com/sra-for-covered-entities)
- [MKT] Dental-association endorsements, e.g. [ODA](https://www.oda.org/member-center/endorsed-products-and-discounts/practice-management-resources/abyde/)

- **Flow:** "straightforward, tailored assessments" across physical, technical and administrative safeguards. **Per-question delegation:** "send an SRA question to a colleague... or to an external partner such as your IT provider", then review the response, and the scorecard updates.
- **Maintenance:** "Ongoing Compliance" sends monthly notifications to keep the SRA current.
- **Scorecard:** directory listings describe "a scorecard displaying questions, submitted answers, and the associated risk level" ([GetApp listing via search snippet](https://www.getapp.com/healthcare-pharmaceuticals-software/a/abyde/)).
- **Pricing:** from about $115 per location per month (listing).
- **Not verified:** risk model, evidence, remediation UI, report steps.
- **Reviews:** Capterra shows 1 rating and no text found.

## 8. HIPAA Ready (CloudApper AI)

**Evidence:** [MKT] [product page](https://www.cloudapper.ai/hipaa-ready-compliance-software/)

- The product includes a security risk analysis and claims "inbuilt automatic gap analysis".
- A "self-assessment dashboard" helps identify risk areas.
- Corrective actions can be linked to incidents and hazards. Documents are stored with automatic version history.
- Web app for admins, plus native iOS and Android apps for staff.
- **Not verified:** question flow, risk model, report steps. **Reviews:** none found.

## 9. HIPAAtrek and ComplyAssistant (existence verified only)

- **HIPAAtrek:** risk assessment, "automated gap analysis", task manager, and a breach risk assessment ([GetApp](https://www.getapp.com/healthcare-pharmaceuticals-software/a/hipaatrek/)).
- **ComplyAssistant:** healthcare GRC covering HIPAA, HICP, NIST and HITRUST, with a risk register and vendor risk. One 2018 reviewer said "not all components are editable" ([GetApp](https://www.getapp.com/all-software/a/complyassistant/)).

---

## Regulatory note: HIPAA Security Rule NPRM status (verified with 2026-dated sources)

- **Federal agenda [GOV]:** RIN 0945-AA22 is listed under **"Long-Term Actions"** in the agenda edition labeled 2026 (pubId 202510). Its timetable reads "NPRM 01/06/2025 (90 FR 898); Final Action 07/00/2027" ([reginfo.gov](https://www.reginfo.gov/public/do/eAgendaViewRule?pubId=202510&RIN=0945-AA22)).
- **Law firm, July 13, 2026 [PRESS]:** moved to Long-Term Actions with a July 2027 target, and "the existing Security Rule remains enforceable" ([Clark Hill](https://clarkhill.com/news-events/news/hipaa-security-rule-update-delayed-until-2027/)).
- **Vendor blog, Sept 4, 2026 [MKT]:** still a proposed rule, with a target of around July 2027 ([PACT-ONE](https://www.pact-one.com/2026/09/hipaa-security-rule-2026-status/)).
- **Conclusion:** as of 2026-10-08, no final rule has been found. The current Security Rule, including addressable specifications, applies.
- **Caveat:** Clark Hill calls the edition the "Fall 2026" agenda while reginfo labels it "2026". The edition naming is inconsistent, but the July 2027 date agrees across all three sources.

---

## Cross-tool comparison (UX-relevant)

| Dimension | HHS SRA Tool | Clearwater | Accountable | HIPAA One | Compliancy Group | Medcurity / Abyde |
|---|---|---|---|---|---|---|
| Driver | Questions by safeguard theme | Assets, then controls, then scenarios | Questions in 7 categories | Questions plus NIST risk steps | Yes/no self-audits | Questions (adaptive) / questions |
| Per screen | 1 question | Lists with filters | Not documented | Not documented | Not documented | Not documented |
| Skip logic | Yes, branching | N/A (scenarios scoped by component) | Not documented | Not documented | Not documented | "Adaptive" (MKT) |
| Flag for later | Yes, counts as a risk; report is read-only | Not documented | Drafts | Not documented | Not documented | Delegation (Abyde) |
| Avoiding rating explosion | Tick applicable vulnerabilities; threats pre-listed | Component Groups, global controls, copy ratings, ML suggestions | No L×I model | "System-generated risk ratings" | Gap-based, no L×I | 3 tiers (Medcurity) |
| Matrix | 3×3 into 4 levels | Not verified | None | NIST (scale not verified) | None | 3 tiers |
| Evidence | Links only, optional | Upload on control notes | Optional upload per question | "Book of Evidence" | Stored docs | "Automated" (MKT) |
| Remediation | Per gap: owner, due, done, links | Findings and activities | draft→open→in progress→completed→verified | Module plus action history | Coach-built with dates | Owner, deadline, overdue flags |
| Reports | Locked until 100% complete; 5 reports | Reports, extracts, dashboards, register | Internal or external snapshot, PDF or link | Real-time plus final | Not verified | Executive trend report |
| Pre-fill | None (Save As last year) | ML risk ratings | Copilot proposes, user confirms | Auto-fill unchanged from prior year | Coaches | — |

---

## Patterns worth copying

1. **Gate the risk register with "which vulnerabilities apply?"** (HHS SRA). After each domain, show a short checklist of pre-written vulnerabilities with their threats attached. Only the ticked ones generate threat rows to rate. This turns about 200 possible rows into the handful that matter.
   - For RainTech's 5x5 model, derive the default vulnerabilities from failing or partial safeguard answers so the checklist starts pre-ticked.
   - Sources: [User Guide pp.18–19](https://healthit.gov/sra_tool_user_guide_version_3-7/), workbook analysis.
2. **Rate once, apply many** (Clearwater). Group assets by threat surface (Component Groups) and answer controls globally with group-level overrides. Offer "copy risk determination" from one group to another, and a "master infrastructure" asset for shared components. This is the right answer to "don't make me rate hundreds of combinations".
   - Source: [2025 syllabus](https://go.clearwatersecurity.com/hubfs/2025%20Webinars/2025_OCR_Quality-Risk-Analysis-Working-Lab_Program%20Syllabus.pdf).
3. **Suggested ratings the user accepts or overrides, with the reason shown.** Examples: Clearwater's Predictive Risk Rating ("automatically accepted or simply serve as guidance") and Accountable Copilot ("You confirm or edit before anything is saved").
   - For a local-first app, deterministic rule-based defaults work well. For example, a safeguard answer of "Not implemented" with ePHI-bearing assets suggests likelihood 4.
4. **Answer-specific education.** The HHS Education panel changes with the selected answer, so the user immediately sees what this answer means and what to do about it. One question per screen sits beside a citation panel and a collapsible notes field.
5. **Graded answers with "I don't know" and "Flag for later" as first-class choices.** A flag counts as an open item, so it cannot be silently forgotten.
   - Improve on HHS by making the flagged list **clickable** so it jumps straight to the question.
6. **Section close-out screen:**
   - success vs. review split
   - % bar
   - notes field
   - attach evidence
   - an explicit **"Section Reviewed/Confirmed" attestation** stamped with user and date

   This gives the consultant a natural checkpoint, and gives the client an audit trail. Source: User Guide p.20.
7. **One-click "carry forward last year"** with unchanged answers pre-filled and changed content highlighted (HIPAA One "auto-fill information that hasn't changed"). This beats the HHS approach of Save As on an old content version.
8. **Remediation lifecycle that ends in "verified", not "done",** with priority, owner, target date and evidence required to verify, plus an overdue count on the plan header (Accountable). Generate remediation items from findings, grouped by related finding.
9. **Asset and vendor CSV import/export templates** (HHS, Clearwater "Asset Import Tool"). Consultants arrive with a client's spreadsheet.
10. **Report choices that match the audience:** internal vs. external, snapshot-locked at generation (Accountable). HHS's split of Summary, Risk, Detailed, Remediation and Flagged reports maps well to a consultant's report package.
11. **Lock on submit:** submitting "Locks the assessment as that point-in-time record" (Accountable). This matches RainTech's versioning spine.
12. **Per-question delegation to someone else**, such as the client's IT provider, with the consultant reviewing before it counts (Abyde). In a single-user desktop app the equivalent is an exportable question packet or worksheet to import back.

## Patterns to avoid

1. **Gating all reports behind 100% completion** (HHS). Consultants need draft reports mid-engagement. Allow drafts watermarked "DRAFT, X% complete".
2. **Linear Back/Next-only editing** (HHS). Re-opening a completed section drops you at its end, you must page backwards, and editing un-completes the section until you click through to the end again. Allow direct jump to any question, and recompute completion instead of forcing a re-walk.
3. **Two unrelated numbers both called "risk"** (HHS "Risk Score" % vs. "Risk Rating" L×I). Users need an FAQ to tell them apart. RainTech should show one risk concept (the 5x5 rating) and call compliance coverage something else.
4. **Disconnected inventories.** HHS assets and vendors never link to threats or ratings, so the asset list becomes decorative. Either link assets to risk scenarios (Clearwater) or don't ask for detail you won't use.
5. **Forced rating of every row before Next**, with only a warning to "scroll down through each threat". Show an inline "N unrated" counter and let the user move on with the items marked incomplete.
6. **Read-only reports that don't link back** (HHS Flagged Report: "you cannot change your answer from that report"). Every report row in the app should be a link to its source.
7. **Save-button traps:** "if you do not click Save, you may need to click Next twice", "Save Remediation must be clicked", and items going read-only until "Edit" (HHS). Autosave everywhere (Accountable: "saves your progress as you go").
8. **Content-version lock-in with a warning that cannot be dismissed** (HHS). Offer a guided migration that shows which questions changed.
9. **Yes/no-only self-audits** (Compliancy Group: "most structured as yes or no questions"). They are fast but give no partial credit and no basis for likelihood. Keep graded options.
10. **Regulatory jargon without help text.** This is the top HIPAA One complaint ("some help text would have been useful") and the first problem HHS's own usability testing found ("decoupling the questions from the legislative verbiage").
11. **Reminder spam keyed to individual answers** (Compliancy Group G2 complaint). Batch reminders by engagement or due date.
12. **A score that looks like a grade with no explanation of what moves it.** Accountable explicitly labels its score "a signal — not a grade" and shows the weights. If RainTech shows a score, show its composition.
