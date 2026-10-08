# CMMC / NIST SP 800-171 assessment tools: UX research

Research date: 2026-10-08. Track: tools built specifically for CMMC / 800-171 readiness and assessment, plus how RPO consultants and C3PAO assessors actually run an assessment.

**Source labels:** [DOCS] = vendor help/support documentation. [MKT] = vendor marketing, press release or sponsored content. [REG] = regulation or government. [REVIEW] = user or third-party review. [PRAC] = practitioner or consultant blog. [RESEARCH] = academic. [ARCHIVE] = Wayback Machine snapshot.

**Method limits:** Reddit (r/CMMC, r/NISTControls) returned HTTP 403 to direct fetch, and the search engine indexed no Reddit threads, so this report has **no Reddit quotes**. G2 and Capterra review pages also returned 403. Review content below comes from search-engine extracts of those pages or from third-party review sites. I watched no demo videos and read no transcripts. dodcio.defense.gov and war.gov returned 403, so the official CMMC PDFs (eMASS, Scoping Guide, Assessment Guide) are cited from eCFR/Cornell LII text or secondary summaries, and labeled that way.

---

## 0. Regulatory status (verified, as of 2026-10-08)

- **32 CFR Part 170 (CMMC Program rule):** effective 2024-12-16. [Guernsey summary](https://guernsey.us/?p=423) [secondary]
- **48 CFR / DFARS rule:** finalized 2025-09-10. It took effect 2025-11-10, which started Phase 1 (self-assessments as a condition of award). [Arnold & Porter](https://arnoldporter.com/en/perspectives/advisories/2025/09/cmmc-final-rule-key-takeaways-for-defense-contractors), [McDermott](https://www.mcdermottlaw.com/insights/are-we-there-yet-dod-issues-final-rule-establishing-cmmc-program/) [secondary/legal]
- **Phase 2 (C3PAO Level 2 at award, originally 2026-11-10) is SUSPENDED.** The Department of War suspended Phase 2 and "all pending and future CMMC milestones until further notice" on **2026-07-13**. It also launched a 60-day "CMMC Reform Task Force" review. Phase 1 self-assessment requirements "remain in force." [Federal News Network, 2026-07-13](https://federalnewsnetwork.com/cybersecurity/2026/07/pentagon-suspends-cmmc-phase-two-requirements-launches-review-of-program/), [Greenberg Traurig](https://www.gtlaw.com/en/insights/2026/7/dod-suspends-cmmc-deadlines-and-seeks-to-reassess-requirements), [Latham](https://www.lw.com/en/insights/what-defense-contractors-should-know-about-dod-suspension-of-cmmc-phase-2), [DoW release (403 to fetch)](https://www.war.gov/News/Releases/Release/Article/4542329/forging-the-arsenal-of-freedom-department-of-war-suspends-cmmc-phase-ii-require/)
- **Class Deviation 2026-O0025 Rev 3 (2026-09-03):** contracting officers accept L1/L2 self-assessments and remove third-party assessment requirements at the next modification. The review period closed 2026-09-11. As of the latest entry (2026-10-01), the **Task Force report has not been released**. DFARS 252.204-7012, NIST 800-171 **Rev 2**, SPRS scores and annual affirmations remain in effect. [Secureframe CMMC news tracker](https://secureframe.com/hub/cmmc/news-updates-2026.md) [vendor-maintained tracker; single source for the deviation detail, so not independently verified]
- **Product implication:** the SPRS self-assessment (110 to -203) and the SSP/POA&M are the **live, contractually required deliverables right now**. C3PAO certification is paused. A consultant tool should treat "self-assessment + SPRS + SSP + POA&M" as the main path and C3PAO prep as secondary. The rules could change again once the Task Force reports.

### Rules that constrain the UX (primary text)
- **32 CFR 170.24**, eCFR/Cornell [REG] ([Cornell](https://www.law.cornell.edu/cfr/text/32/170.24)):
  - A requirement is **MET** when "All applicable objectives for the security requirement are satisfied based on evidence. All evidence must be in final form and not draft."
  - For each objective NOT MET, the assessor documents why.
  - An N/A objective is "equivalent to the same assessment objective being assessed as MET."
  - The score starts at 110 and subtracts 1, 3 or 5 for each NOT MET requirement.
  - **Scoring is per requirement and binary.** Objectives decide the requirement, but there is no partial credit per objective (the only exceptions are the 3.5.3 and 3.13.11 variable deductions in the DoD Assessment Methodology).
- **32 CFR 170.21**, POA&M rules [REG] ([Cornell](https://www.law.cornell.edu/cfr/text/32/170.21)):
  - Score / 110 must be ≥ 0.8 (88).
  - No POA&M item may be worth more than 1 point, except 3.13.11 when encryption is used but not FIPS-validated.
  - Six requirements can never be on a POA&M: 3.1.20, 3.1.22, 3.12.4 (SSP), 3.10.3, 3.10.4, 3.10.5.
  - POA&Ms must be closed out within 180 days.
- **32 CFR 170.19**, scoping [REG] ([Cornell](https://www.law.cornell.edu/cfr/text/32/170.19)):
  - **CUI Assets:** assessed against all L2 requirements.
  - **Security Protection Assets:** assessed against relevant requirements.
  - **Contractor Risk Managed Assets:** SSP review, with a limited check if questions arise.
  - **Specialized Assets:** SSP review only.
  - **Out-of-Scope Assets:** "Prepare to justify."
  - The first four categories must appear in the asset inventory, the SSP and the network diagram.

> Note on our build's "evidence before MET" rule: the regulation ties MET to evidence for **assessment findings**. That supports an evidence gate in a *certification-assessment* mode. Every readiness tool below lets consultants set status first and attach evidence later; Totem even has a "Trending Met" status for exactly that. See Patterns.

---

## 1. Tool-by-tool findings

### 1.1 Totem™ CMMC Compliance Software (Totem Technologies, Utah). VERIFIED, best-documented

Product page: [totem.tech/cybersecurity-compliance-software](https://www.totem.tech/cybersecurity-compliance-software/) [MKT]. Support center: [support.totem.tech](https://support.totem.tech/guides/) [DOCS].

**1. Unit of work.**
- The primary workflow is the **Control Status module**. It lists "the full list of security controls," and each control has "relevant **Organization Actions (assessment objectives)**." [DOCS: Control Status module](https://support.totem.tech/the-control-status-module/)
- The UI groups objectives under controls and expands each control in a list: "Expand each control. New controls start as 'Not yet assessed.'" [DOCS: Building an SSP](https://support.totem.tech/building-a-system-security-plan-ssp/)
- There are saved filters, global search, find-and-replace, and **bulk update** of many Organization Actions at once (status, implementation text, type, comments, shared responsibility, artifact links). [DOCS: Bulk-updating controls](https://support.totem.tech/bulk-updating-controls/), [Control Status guide index](https://support.totem.tech/control-status/)
- I could not verify how many items appear per screen. It is a list with expandable rows, not one page per objective.

**2. Status and SPRS.**
- Status is set **per objective**, with four values: Met / **Trending Met** / Not Met / Not Applicable. "A control is Met when all its Organization Actions are Met." [DOCS](https://support.totem.tech/building-a-system-security-plan-ssp/)
- A **Questionnaire** gives a fast first pass. It shows "layperson interpretations for all relevant security controls, formulated as a question."
  - "Answering Yes to a question will immediately mark all Organization Actions (assessment objectives) as **Trending Met**."
  - "No" marks them all Not Met.
  - Warning from the docs: "using the Questionnaire will overwrite whatever assessment status you have in Controls." [DOCS: Using the Questionnaire](https://support.totem.tech/using-the-questionnaire/)
- The score starts at 110/110 and "updates any time a control's assessment status changes." It is shown on the Dashboard and **at the top of the Control Status page**. Trending Met and N/A cost no points.
- IA.L2-3.5.3 and SC.L2-3.13.11 are "variable" point controls. Marking either Not Met opens a modal that asks for the implementation level. [DOCS: Reviewing your self-assessment score](https://support.totem.tech/reviewing-your-self-assessment-score/)

**3. Evidence.**
- Artifacts are uploaded once to an Artifacts library. Each one can be linked to "as many security requirements as you'd like."
- Artifacts are **versioned**: when v2 is uploaded, "All Organization Actions that were linked to v1 of the Artifact are now linked to v2." Totem rejects an upload whose hash matches the current version. [DOCS: Creating Artifacts](https://support.totem.tech/creating-artifacts/)
- The docs I read do not say evidence is required before Met. The "Comments" field is for noting "compelling evidence" such as people to interview.

**4. SSP and POA&M.**
- **SSP:** the SSP builds up as you set status. Each Organization Action has the fields Status, **Implementation Details** ("the core of your SSP"), Comments, Shared Responsibilities (from the ESP's SRM/CRM) and Artifacts. You can also import an SSP template. [DOCS](https://support.totem.tech/building-a-system-security-plan-ssp/)
- **POA&M:** made of "Corrective Action Plans" (CAPs). You select Not Met Organization Actions in Control Status and click **Add to POA&M**, or create a CAP in the POA&M module.
  - A CAP holds up to 30 actions.
  - Templates are available.
  - CAP types: Non-Conformance / Operational: Temporary Deficiency / Enduring Exception.
  - Each step has dates and a responsible entity.
  - CAPs are **not auto-created**. Totem advises that every Not Met action appear on at least one CAP.
  - There is a Gantt view. [DOCS: Building a POA&M](https://support.totem.tech/building-a-poam/), [POA&M index](https://support.totem.tech/poam/)

**5. Scoping.**
- The Inventory module has hardware, software baseline and CUI inventory, plus import and export. [DOCS index](https://support.totem.tech/inventory/)
- Hardware assets carry a **"CMMC Asset Category"** field taken from the L2 Scoping Guide. [DOCS: Inventorying hardware](https://support.totem.tech/inventorying-hardware-assets/)
- The CUI inventory records each CUI type with NARA Index and Category, Media Type and Dissemination Controls, plus a six-phase **handling lifecycle** (Receival/Generation, Storage, Access, Marking, Dissemination, Disposal) with ghost-text boilerplate. [DOCS: Using the CUI inventory](https://support.totem.tech/using-the-cui-inventory/)

**6. Dashboard.** Seven widgets [DOCS: Dashboard widgets](https://support.totem.tech/dashboard-widgets/):
- Control Status distribution
- **Security Plan Progress** (count of objectives with Implementation Details filled)
- Organization Status (framework, level, CMMC score)
- Control Type (Policy/Technical/Hybrid)
- Upcoming POA&M items (5 nearest due)
- **Not Met by family**
- My Tasks

**MSP/consultant mode:** the "CMMC Expert" tier lets an MSP run its own Totem instance "to manage all clients in one place." [MKT](https://www.totem.tech/cybersecurity-compliance-software/)

**7. Reviews.**
- G2 says there are "not enough reviews… to provide buying insight." [REVIEW: G2 via search](https://www.g2.com/products/totem-cybersecurity-compliance-planning-tool/pricing)
- A Geekflare editorial calls it "very fluid, affordable and convenient" for small businesses. [REVIEW-editorial](https://geekflare.com/es/best-cybersecurity-compliance-software/)
- The Defense Compliance Report did not test it hands-on. It describes Totem as "A lightweight, CMMC-specific GRC tool" and notes the review page is marked "DRAFT PREVIEW". [REVIEW-third party](https://thedefensecompliancereport.com/totem-cmmc-review/)
- Totem also runs a Reddit knowledge base, r/TotemKnowledgeBase, which I could not fetch.

### 1.2 FutureFeed (FutureFeed.co). VERIFIED

Site: [futurefeed.co](https://futurefeed.co/futurefeed/) [MKT]. KB: [support.futurefeed.co](https://support.futurefeed.co/knowledge-base/how-tos) [DOCS]. Deltek has a partnership listing, not an acquisition I could verify. [MKT: Deltek](https://www.deltek.com/en/partners/futurefeed)

**1. Unit of work and navigation.**
- Navigation is a **"Subway Map"** that sits "at the top of every page." Read left to right, it shows "a path from start to finish for the assessment," beginning at Company Profile. [DOCS: Subway Map](https://support.futurefeed.co/knowledge-base/hc/en-us/articles/360042547032-general-navigation-the-subway-map)
- Named stops: Company Profile, Technology, **Assess**, SSP, Deliverables, Your FutureFeed. The KB has sections titled "Work in the Assess Subway Stop" and "Complete the SSP". [DOCS index](https://support.futurefeed.co/knowledge-base/how-tos)
- Units are controls with **"Summary Notes"** plus objective-level **"Objective Statements"** that "appear on the live SSP and the SSP Report." [DOCS: Add Objective Statements](https://support.futurefeed.co/knowledge-base/hc/en-us/articles/27046731840276-how-to-add-objective-statements)
- The flyer lists "Objective-level Documentation **(as required)**". In other words, objective detail is optional, and the control is the main unit. [MKT flyer via Coalfire Federal](https://coalfirefederal.com/images/FutureFeed-Features.pdf)
- Objective statuses include Not Yet Assessed, Implemented and **Inherited**. [DOCS: SSP interactive](https://support.futurefeed.co/knowledge-base/hc/en-us/articles/7006693937300-how-to-interactively-address-ssp-requirements)
- An objective marked Inherited without a linked Shared Responsibility Matrix shows a **yellow warning**. [DOCS](https://support.futurefeed.co/knowledge-base/hc/en-us/articles/34734070131988-resolving-the-yellow-warning-for-inheritance-in-objectives)
- I could not verify the item count per screen.

**2. SPRS.**
- Follows DoD Assessment Methodology v1.2 with partial deductions for 3.5.3 (3 points if MFA covers only remote and privileged users) and 3.13.11 (3 points if encryption is used but not FIPS-validated). The SSP and POA&M are "built automatically as the assessment is completed." [DOCS: SPRS scoring](https://support.futurefeed.co/knowledge-base/hc/en-us/articles/360059232032-sprs-nist-800-171-scoring)
- Marketing: changing a control answer "automatically updates your SPRS score and our other numerous reports." [MKT](https://futurefeed.co/futurefeed/)

**3. Evidence.**
- **"WRITE ONCE, USE EVERYWHERE — Our platform is designed for bulk operations. Once defined, an item can be applied across multiple controls."** [MKT flyer](https://coalfirefederal.com/images/FutureFeed-Features.pdf)
- Tools, services and documents are **tagged to controls**. [DOCS index: "Tag Tools and Documents to Controls"](https://support.futurefeed.co/knowledge-base/how-tos)
- The evidence workflow: an admin assigns a task on a Document or Tool → the assignee adds evidence, signs and completes it → a reviewer signs and approves. Statuses run In Progress → Completed → Reviewed. Recurring tasks are supported. [DOCS: Evidence workflow](https://support.futurefeed.co/knowledge-base/evidence-workflow-quick-guide)
- Export quality "depends on how well you've linked your artifacts to your requirements." There is no hashing inside the tool: users follow the DoD Hashing Guide outside it. An optional **read-only Assessor role** can see the Compliance Dashboard and the SSP. [DOCS: Using FutureFeed during a CMMC assessment](https://support.futurefeed.co/knowledge-base/using-futurefeed-during-a-cmmc-assessment-and-evidence-export-guidance)
- Not stated as required before "Implemented".

**4. SSP and POA&M.**
- SSP: Deliverables → Compliance Reports → select SSP → **Generate** → **Review and approve**.
- Data Files Export: a separate step. [DOCS](https://support.futurefeed.co/knowledge-base/how-to-export-your-assessment-for-customers)
- The flyer advertises "One-click Reporting (presentation/docx)" and a "Dynamic, Automated SSP". [MKT](https://coalfirefederal.com/images/FutureFeed-Features.pdf)
- POA&M items have due dates (quarter or exact date) and statuses such as "In Progress". [DOCS index](https://support.futurefeed.co/knowledge-base/how-tos)

**5. Scoping.**
- The **Sensitive Data Inventory**: tick checkboxes for the information types you hold. Each ticked box becomes a counter that drills down into the Tools and Services that store, process or transmit that data.
- Items can be flagged as a **CUI Asset** to "direct the auditor's attention to the right places."
- You can also build the tool list first, and the inventory fills in from it. Categories here are Electronic Data Locations and Tools and Services. Explicit CMMC 5-category labels were not verified. [DOCS: CUI inventory](https://support.futurefeed.co/knowledge-base/hc/en-us/articles/31335278509204-how-to-create-the-cui-sensitive-data-inventory)

**6. Dashboards.** Personal and team accountability dashboards, a Compliance Dashboard, and a "Cyber-Readiness Presentation" generator. [DOCS index](https://support.futurefeed.co/knowledge-base/how-tos)

**7. Reviews.**
- **Vendor-selected testimonials** [MKT]: "you'd have to rip FutureFeed out of my cold dead hands" (Leia Shilobod, CompliancyIT, which is a FutureFeed marketplace add-on partner), and "the gold standard for us" (Simpatico Systems). [flyer](https://coalfirefederal.com/images/FutureFeed-Features.pdf)
- **E-N Computers (RPO)**. This reviewer has a conflict of interest: the firm bundles FutureFeed with its consulting.
  - "the best GRC app for CMMC because it engages business leaders first"
  - "presents all the information you need in a visually pleasing and data-heavy way"
  - templates are "good, but not great"
  - [PRAC/REVIEW](https://www.encomputers.com/2024/02/best-grc-cmmc/)
- Capterra showed 0 user reviews. [REVIEW](https://www.capterra.co.uk/software/1083169/FutureFeed)
- The Defense Compliance Report (no hands-on test) could not verify workflow quality. [REVIEW](https://thedefensecompliancereport.com/futurefeed-cmmc-review/)

### 1.3 Exostar Certification Assistant (and ComplyUp, acquired Dec 2024). VERIFIED to exist; UI detail NOT verifiable

- **Certification Assistant:** a "guided self-assessment" that "calculates SPRS scores, and generates SSPs and POA&Ms." [MKT: Exostar bundle](https://www.exostar.com/bundle-suite/)
- It "breaks NIST SP 800-171 and CMMC Level 2 requirements into clear, manageable steps" with "guided inputs and built-in explanations" and calculates SPRS "as users answer each requirement." [MKT via search: exostar.com](https://www.exostar.com/?p=180)
- It assigns and tracks action items and stores "documents, evidence and evaluation criteria." Tiers were Lite (free L1), Standard and Premium in CMMC 1.0 terms. [PRAC/partner: Pivot Point, 2020, updated 2025](https://www.pivotpointsecurity.com/exostar-certification-assistant-simplifies-cmmc-certification/)
- I found **no public help docs**. The objective-vs-requirement unit, the evidence gate and the screen layout are **unverified**.
- Capterra lists Exostar platform-wide at 1.5/5 from 4 users. That rating covers the whole platform, not Certification Assistant. [REVIEW via search](https://www.capterra.com/p/147823/Exostar/)
- **ComplyUp** (Tampa; acquired by Exostar 2024-12-17). [cbinsights](https://www.cbinsights.com/company/complyup), [techleap](https://finder.techleap.nl/news/feed/exostar-acquires-robot-morning-complyup)
  - **Multi-tenant**, MSP-oriented.
  - Its "new Assessment Platform" added a dashboard that "shows your status on each individual requirement as well as the ability to assign requirements to team members."
  - The SSP can be generated as a **Major or Minor revision**, or downloaded "as an untracked working copy". All documents download as Word.
  - Evidence is searchable and downloadable as a .zip. [ARCHIVE: migration guide, snapshot 2025-11-08](https://web.archive.org/web/20251108055631/https://complyup.com/migration-guide/)
  - Pricing: NIST 800-171 tier $1,800/yr; features include "SSP Revision History", "Progress Visualization", "Task Assignment" and "14 800-171 Family-Specific Policies". [ARCHIVE pricing](https://web.archive.org/web/20260118080828/https://complyup.com/pricing/)
  - **Free DoD Assessment Methodology Scoring Tool:** all 110 requirements on **one page**, each with its point value and a two-way toggle (Fully Implemented / Not Fully Implemented). 3.5.3 has a third option, "Implemented for Remote", and 3.12.4 is marked N/A. The tool shows a live score and "Remaining Requirements" and generates a ready-to-send SPRS email. [ARCHIVE](https://web.archive.org/web/20260118064927/https://complyup.com/800-171-dod-assessment-methodology-scoring-tool/)
  - **"Assessor Field Sheet"**: a spreadsheet of the full L2 Assessment Guide with fields for findings, sortable by level, practice or domain. [ARCHIVE](https://web.archive.org/web/20260118082839/https://complyup.com/assessor-field-sheet/)
  - **Observation:** complyup.com failed DNS resolution on 2026-10-08 from this environment, so the product may have been folded into Exostar. Unverified.

### 1.4 PreVeil Compliance Accelerator. VERIFIED, but it is a documentation package, not an assessment tool
- "Assessment-Ready Documentation + Videos" plus expert support. It includes a "Fully-developed SSP addressing all 110 controls and 320 objectives" built around a fictional 20-person "ACME Corporation" reference model, SOPs for 14 families, a pre-filled SRM, diagram templates and checklists. [MKT](https://www.preveil.com/compliance-package), [MKT exec summary](https://www.preveil.com/resources/compliance-accelerator-your-fast-track-to-cmmc-level-2-certification/)
- **No SPRS calculator, self-assessment workflow or POA&M tooling** is described. PreVeil claims to support 102 of 110 controls. [MKT](https://www.preveil.com/manufacturing-cnc/)
- **Relevance:** a pre-written SSP with inheritance (an SRM) is the competing model to "build the SSP from answers." Consultants buying for clients will compare against it.

### 1.5 Ignyte Assurance Platform. VERIFIED (vendor is also a C3PAO); thin CMMC UI detail
- **SSP:** generated from network hardware and software inventory; it defines CUI/CDI. **POA&M:** "automatically creates real-time POA&Ms". Dashboard images are labeled "System View" and "Current Score Trends". [MKT](https://www.ignyteplatform.com/?p=18166)
- Offers a free "Get Your Free SPRS Score" tool; its format is unverified. [MKT](https://www.ignyteplatform.com/?p=10408)
- **Customer story:** Joslyn finished the SSP, POA&M and SPRS in 30 days, with Ignyte staff drafting the control responses. [MKT](https://www.ignyteplatform.com/?p=20190)
- **Reviews:**
  - G2's one listed complaint concerns "the artifact management workflow with respect to how uploads are performed." [REVIEW via search](https://www.g2.com/products/ignyte/reviews)
  - Capterra reviews skew toward FedRAMP and RMF work. [REVIEW via search](https://www.capterra.co.il/reviews/175537/ignyte-assurance-platform)
- C3PAO status. [MKT](https://www.ignyteplatform.com/cybersecurity-awards-and-certifications/)

### 1.6 Cyber AB CMMC Readiness Tool (CRT), built on Cyturus. VERIFIED; this is the closest thing to official RPO tooling
- Cyturus is the "designated provider of the Cyber AB's CMMC Readiness Tool for the CMMC RPO Community." It is included with RPO membership at no extra cost, with limited access for up to 5 client accounts. [MKT: Carahsoft PR](https://www.carahsoft.com/news/carahsoft-and-cyturus-announce-partnership-with-the-cyber-ab-to-offer-cmmc-compliance-readiness-tool), [Cyber AB](https://cyberab.org/Resources/Platforms-and-Tools)
- It "ingests existing spreadsheet-based risk data and generates outputs in predefined, CMMC-compliant formats." There is permission-based sharing with C3PAOs and OSC members. [Cyber AB](https://cyberab.org/Resources/Platforms-and-Tools)
- **Workflow:** the OSC runs a "Self-Guided Assessment module" → produces an SPRS score, POA&M and SSP. An affiliated RP/RPA logs in via SSO "to review the OSC's self-guided assessment and **drill into the specific objectives** and implementation solutions." [MKT: Carahsoft sponsored PDF, 2024](https://static.carahsoft.com/concrete/files/3717/0920/7665/Carahsoft_IIG_2024_JanFeb_Cyturus.pdf)
- **Practitioner review:** "the tool itself is fairly clunky" (E-N Computers, an RPO with a FutureFeed conflict of interest). [PRAC](https://www.encomputers.com/2024/02/best-grc-cmmc/)

### 1.7 Assessor-side (government and C3PAO) tooling
- **DIBCAC "Public 800-171 Self-Assessment Database (v1)":** an MS Access (.accdb) database that DIBCAC says is "the same as what their assessors use."
  - Tables: Family Names, **Objectives**, Requirements, plus link tables.
  - Columns for **documents examined, persons interviewed**, Validation_Text (test/observation), notes, and a "Standard" column giving the desired evidence type (document, screen share, artifact).
  - The workflow is presumed to start by marking each objective true or false. [PRAC: Etactics recap of Cyber AB Town Hall, 2022-10-14](https://etactics.com/blog/cyberab-september-town-hall)
  - This is secondary, and I could not download the DCMA file.
  - **This is the strongest available evidence of how government assessors structure their work:** one row per objective, with examine / interview / test columns.
- **CMMC eMASS** (summarized from search; the DoD PDF returned 403):
  - C3PAOs upload pre-assessment data and assessment results that conform to a **two-part JSON data standard** (pre-assessment and results).
  - C3PAOs may "build or buy their own tools" if those tools match the standard.
  - A CCA outside the team does QA before upload. eMASS feeds results to SPRS. [DoD CMMC eMASS PDF (URL; not fetched)](https://dodcio.defense.gov/Portals/0/Documents/CMMC/CMMC-eMASS.pdf)
  - Secureframe Defense advertises generating "a pre-assessment eMASS template" and exporting the SSP as JSON. [MKT](https://secureframe.com/blog/secureframe-defense-for-c3pao-assessment.md)
- **Kieri Solutions:** **a C3PAO, not a software vendor.** Its CEO is Amira Armond. [isc2 speaker bio](https://events.isc2.org/b/sp/amira-armond-5408). **No Kieri software product could be verified.**

### 1.8 Named in the brief but NOT verified as CMMC assessment software
- **"Intelligent Systems' CyberAssist":** not found. The real **CyberAssist** is the **DIB SCC / ND-ISAC free resource website**, not software. Its content groups requirements "by level and by domain" and links each requirement to resources, sample policies and example tools. [ND-ISAC](https://ndisac.org/blog/cyber-assist-website-cmmc-updates/), [Lockheed Martin training notice](https://lockheedmartin.com/en-us/suppliers/news/features/2023/cybersecurity-cyberassist-training.html). I found no company called "Intelligent Systems" connected to it.
- **Securicy (Nova Scotia):** a real company with an SMB infosec program, policy generator and "Audit Connect" for sharing control progress. [BetaKit](https://betakit.com/nova-scotias-securicy-raises-1-8-million-from-public-private-investors/), [GoodFirms](https://www.goodfirms.co/software/securicy)
  - **No CMMC-specific features were verified.** Owler hints at a rebrand to "Carbide" (unverified). [Owler](https://www.owler.com/company/securicy)
- **IntelliGRC:** exists and is marketed as "Cyber GRC (CMMC/DIB)". [vendor directory](https://guptadeepak.com/grc-compass/vendors/intelligrc/)
  - No docs found. One RPO described its reports as "generic, overly broad… fairly useless." [PRAC](https://www.encomputers.com/2024/02/best-grc-cmmc/)

---

## 2. How assessors and consultants actually work

1. **They start from the document, not the questionnaire.**
   - C3PAO Phase 1 reviews the SSP, validates scope and makes a readiness determination before Phase 2. [summary of CAP](https://madsecurity.com/madsecurity-blog/the-cmmc-assessment-process-cap-what-every-dod-contractor-should-know), [IBSS](https://ibsscorp.com/understanding-the-c3pao-assessment-process-for-cmmc-level-2/)
   - "Long before interviews start, the assessor reviews your foundational documentation." The SSP "sets the tone." [PRAC: 2W Tech, 2026-06-01](https://2wtech.com/what-a-cmmc-2-0-assessment-actually-looks-like/)
2. **Interviews are organized by people and process, not by objective number.**
   - Interviews are "the heart of a CMMC 2.0 assessment." Assessors ask staff to walk through "provisioning a new user, enforcing MFA, detecting unauthorized devices, or managing employee departures," and cross-check answers between roles. [PRAC: 2W Tech](https://2wtech.com/what-a-cmmc-2-0-assessment-actually-looks-like/), [PRAC: Planet Technologies](https://go-planet.com/perspectives-blog/inside-the-mind-of-a-c3pao-how-assessors-evaluate-cmmc-compliance/)
   - DeepSeas's gap-assessment SOW sends the client "a template with an overview of **control families and suggested roles** to attend." In practice that means one interview session per family or role group. [PRAC](https://www.deepseas.com/services/cmmc-gap-assessment/)
   - The same 2W Tech article claims "no POA&M path to certification." That is **wrong** under 170.21, so treat that source with caution.
3. **The working artifact is a row-per-objective worksheet.**
   - DIBCAC's own database has one row per objective with examine, interview and test columns (§1.7).
   - ComplyUp's "Assessor Field Sheet" is a spreadsheet of the Assessment Guide (§1.3).
   - Consultants recommend an evidence matrix "for each of the 110 CMMC practices" that "might take the form of a spreadsheet." It should have the fields practice ID, title, implementation description, **responsible role**, artifacts, with **one artifact supporting several controls** (e.g., the access control policy across AC/IA/AU). [PRAC: Elevate, 2026-05-06](https://elevateconsult.com/insights/cmmc-audit-evidence-organizing-documentation-by-practice-artifact-and-owner/)
   - The Cyber AB CRT explicitly *ingests spreadsheets*, which suggests RPOs start from spreadsheets (§1.6).
   - "If you don't want to juggle dozens of Excel spreadsheets…" [PRAC](https://www.encomputers.com/2024/02/best-grc-cmmc/)
4. **Sampling is judgment-based.** A survey of 17 CCAs/LCCAs found:
   - 71% said their C3PAO provides no sampling methodology.
   - Decision factors: environment complexity 82%, judgment 76%, risk 71%, statistical model 12%.
   - 53% see inconsistency "occasionally" and 18% "very frequently." [RESEARCH: Therrien & Hastings, arXiv 2602.09905, 2026-02-10](https://arxiv.org/html/2602.09905v1)
5. **Evidence is judged for adequacy and sufficiency, and drafts don't count.** FutureFeed's KB defines adequacy ("Am I showing the right thing?") vs sufficiency ("enough… across all in-scope assets"). [DOCS](https://support.futurefeed.co/knowledge-base/using-futurefeed-during-a-cmmc-assessment-and-evidence-export-guidance) Rule text: "final form and not draft." [REG 170.24](https://www.law.cornell.edu/cfr/text/32/170.24)
6. **Assessors like to see a drafted POA&M at assessment time.** [PRAC: Planet Technologies](https://go-planet.com/perspectives-blog/inside-the-mind-of-a-c3pao-how-assessors-evaluate-cmmc-compliance/)
7. **The CAP has four phases:** Plan/Prepare (SSP review, scope, readiness) → Conduct (in-brief, daily checkpoints, examine/interview/test) → Report (QA by an independent CCA, out-brief) → Certificate / POA&M close-out. [summaries: Mad Security](https://madsecurity.com/madsecurity-blog/the-cmmc-assessment-process-cap-what-every-dod-contractor-should-know), [A-LIGN](https://www.a-lign.com/?p=14130). I did not read the official CAP document.

**Implication for "what flow feels natural to an assessor":**
- Work **requirement by requirement within a family**, with all of a requirement's objectives visible together.
- Capture **examine / interview / test notes and the people interviewed** against each objective.
- Link **one artifact to many objectives**.
- Keep a running score.
- Then produce the SSP and POA&M as by-products.
- No tool or practitioner source described one objective per page.

---

## 3. Cross-tool comparison

| Dimension | Totem | FutureFeed | Exostar CA / ComplyUp | Cyber AB CRT (Cyturus) | DIBCAC DB |
|---|---|---|---|---|---|
| Primary unit on screen | Control list, expandable to objectives ("Organization Actions") [DOCS] | Control with optional objective statements; Subway-map stages [DOCS] | Requirement ("each requirement") [MKT/ARCHIVE] | Self-guided assessment; RP drills into objectives [MKT] | Objective rows [PRAC] |
| Status granularity | Per objective; 4 states incl. **Trending Met**; roll-up = all Met [DOCS] | Per objective (Not Yet Assessed / Implemented / Inherited) [DOCS] | Per requirement (free tool: binary toggle) [ARCHIVE] | Unverified | True/False per objective [PRAC] |
| Fast first pass | Yes/No Questionnaire sets all objectives (overwrites) [DOCS] | "Bulk operations… applied across multiple controls" [MKT] | One-page 110 toggles (free tool) [ARCHIVE] | Spreadsheet ingest [MKT] | n/a |
| Bulk edit | Yes, many fields [DOCS] | Yes (claimed) [MKT] | Unverified | Unverified | n/a |
| Live SPRS | Yes, top of Control Status + dashboard; variable-point modal [DOCS] | Yes (claimed); partial 3.5.3/3.13.11 [DOCS/MKT] | Yes, as you answer [MKT] | Yes (claimed) [MKT] | n/a |
| Evidence required before Met | Not stated | Not stated | Unverified | Unverified | n/a |
| Evidence reuse | Artifact library, link to many, versioned with auto-relink [DOCS] | Tag tools/docs to controls; task → sign → review [DOCS] | Evidence storage, zip download [ARCHIVE] | Unverified | Columns per objective |
| SSP | Emerges from per-objective Implementation Details [DOCS] | Generate → review/approve [DOCS] | Generate Major/Minor revision or untracked working copy; .docx [ARCHIVE] | Generated [MKT] | n/a |
| POA&M | Manual CAPs from selected Not Met; templates; Gantt [DOCS] | Auto-built (claimed); due dates and statuses [DOCS] | Generated [MKT] | Generated [MKT] | n/a |
| Scoping | Asset inventory with CMMC Asset Category field; CUI lifecycle [DOCS] | Sensitive Data Inventory checkboxes → tools; CUI Asset flag [DOCS] | Unverified | Unverified | n/a |
| Multi-client (consultant) | MSP "instance" tier [MKT] | Multi-tenant, unlimited users [MKT] | Multi-tenant [ARCHIVE] | RPO up to 5 clients [Cyber AB] | n/a |

---

## 4. What I could not verify
- Any Reddit, LinkedIn or podcast user quotes (blocked or not indexed). G2 and Capterra review text was seen only through search extracts.
- Exostar Certification Assistant's actual screens, units and evidence rules (no public docs).
- Whether any tool **requires** evidence before Met. None of the docs read state such a gate.
- Items per screen for Totem and FutureFeed (the screenshots were not readable).
- The official CMMC Scoping Guide, Assessment Guide, CAP and eMASS PDFs (403). I relied on eCFR/Cornell text and secondary summaries.
- "Intelligent Systems CyberAssist" as a product, Kieri software, and Securicy CMMC features: **not verified; do not cite as competitors.**
- Task Force report content (not released as of 2026-10-01 per the Secureframe tracker).

---

## Patterns worth copying

1. **Requirement-level list with objectives inline** (Totem Control Status; DIBCAC rows). Show a family's requirements in one scrolling view. Each requirement expands to its 2–6 objectives, and status is set per objective with one click each. The requirement result is derived: all Met or N/A → MET. That replaces about 320 page turns with 14 family views.
2. **A fast first pass that is explicitly provisional.** Totem's Yes/No Questionnaire marks objectives **"Trending Met"**, which scores like Met but shows as unverified. ComplyUp's one-page 110-toggle scorer does something similar. Let the consultant rough in the whole posture in under an hour, then verify. This resolves our "evidence before MET" friction: allow "Met (pending evidence)" and enforce evidence only for the final/assessment state. 170.24's "final form" rule applies to assessment findings.
3. **A live SPRS score pinned at the top of the assessment screen**, updating on every status change, with the 3.5.3/3.13.11 partial-credit modal shown only when those are marked Not Met (Totem). Add the 170.21 checks inline: ≥88, POA&M-eligible only if worth 1 point (or the 3.13.11 exception), and the six never-POA&M requirements flagged.
4. **Write once, link many evidence.** A central artifact library, each artifact linkable to many objectives, **versioned with automatic relink** (Totem), plus tags for tools and services (FutureFeed). Consultants reuse one policy across AC/IA/AU (Elevate).
5. **Implementation text is the SSP.** Per-objective Implementation Details feeds the SSP directly. A "Security Plan Progress" meter counts objectives with text filled in (Totem dashboard). SSP output is a regenerate button with **working copy vs. issued revision** (ComplyUp Major/Minor/untracked). That is one step, not ten sign-offs.
6. **POA&M from selection.** Multi-select Not Met objectives → "Add to POA&M" → CAP template with dates and owner (Totem). Show a nudge for Not Met items not yet on any POA&M.
7. **Capture examine / interview / test and interviewee names per objective** (DIBCAC DB columns), plus an "interview by family/role" session mode where the consultant walks a family with a person and records answers across several requirements (DeepSeas family-and-roles template).
8. **A visible journey map** (FutureFeed Subway Map: Company Profile → Technology → Assess → SSP → Deliverables) so the user always knows where they are in client → scope → assess → package.
9. **Scoping by asset category with a CUI lifecycle.** An asset inventory with the five 170.19 categories as a field (Totem). A CUI inventory by NARA category with Receive / Store / Access / Mark / Disseminate / Dispose (Totem). A "data type → where it lives" drill-down (FutureFeed).
10. **Inheritance with a warning.** An objective marked Inherited needs a linked ESP/SRM, otherwise it shows a yellow flag (FutureFeed). This is a soft validation, not a hard block.
11. **Dashboard essentials:** status distribution, Not Met by family, SSP completeness, next 5 POA&M due dates, score (Totem).

## Patterns to avoid

1. **One objective per page.** No competitor or practitioner workflow does this. Assessors think in requirements and families, and interview by role. It also hides the requirement roll-up that decides the score.
2. **Hard gates that block recording what you observed.** None of the documented readiness tools require evidence before Met. Gating early status forces fake evidence or abandoned sessions. Keep the gate for the final assessment state and signal missing evidence softly (badge, count, export warning).
3. **Destructive bulk shortcuts.** Totem's Questionnaire "will overwrite whatever assessment status you have in Controls," and bulk update "overwrite[s] ALL existing text." Provide a preview/diff and undo, or only fill blanks.
4. **Long sign-off chains to produce a document.** Competitors use generate → review/approve (FutureFeed) or a one-click working copy vs revision (ComplyUp). About 10 sign-offs is far heavier than any documented competitor. Collapse to draft → issue, with an optional reviewer.
5. **Generic, framework-agnostic reports.** IntelliGRC drew "generic, overly broad reports… fairly useless," and "many GRC tools are clunky and unintuitive" (E-N Computers). Outputs must read like a real L2 SSP and POA&M, not a GRC dump.
6. **Upload friction for artifacts.** Ignyte's only G2 complaint concerned the artifact upload workflow. Support drag-and-drop of many files at once, linking to existing files on disk (FutureFeed supports links to server or cloud files), and versioning.
7. **Mixing marketing "auto-generated POA&M" with no ownership.** Auto-creating POA&M items is fine, but each needs an owner, a date and 170.21 eligibility checks. Otherwise the output is unusable for the 180-day closeout.
8. **Unclear evidence-export completeness.** FutureFeed warns that export quality depends on linking discipline and that hashing is done outside the tool. Show coverage ("objectives with no linked evidence") before export, and consider built-in SHA-256 hashing per the DoD Hashing Guide, since a desktop app can do it locally.
