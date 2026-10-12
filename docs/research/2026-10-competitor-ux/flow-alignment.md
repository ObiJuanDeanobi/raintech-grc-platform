# Flow alignment: how shipped GRC tools run the end-to-end flow, and what we change

Date: October 12, 2026. Status: **research and plan, for Johnathan's decision.** It changes
no code and no specification text. Section (f) lists the spec decisions it asks for.

Inputs: the earlier passes in this folder (README, current-app, the five track files and
`validation/`), ADRs 0019 to 0021, `docs/specification.md`, the current `main`
(`web/src/App.tsx`, `web/src/views/*`, `api/close.py`, `api/overview.py`), screenshots in
`docs/evidence/issue-144/` and `issue-145/`, and new web research done today.

Source labels: **[D]** vendor documentation or help centre, **[M]** vendor marketing,
**[R]** third-party review or press, **[P]** a citation already verified in an earlier
track file and not re-fetched today (the file is named). A help centre that blocked this
environment today is marked *(403 today)*. Nobody used any product hands-on.

**About the trigger.** The flat "Close readiness" list Johnathan saw is the old
`CloseReadinessPanel` (`ClosePanels.tsx`, present through commit `34d8bd8`). It was replaced
on `main` today (PR #165) by grouped counts. Those grouped counts break his new rule too, and
so does the rest of the blocker framing that is still on screen (see c).

**Design principle (Johnathan, October 12):** *"The blockers should only be there when
trying to close the assessment and generate the deliverables."* While someone is working,
the screens show progress and the next piece of work. Reasons something cannot be finished
appear only when he asks to finish it. Hard gates stay enforced at that moment, and drafts
stay available at all times.

---

## (a) Comparison table

| Platform | 1. Nav and first screens | 2. "What's left" | 3. Deliverables | 4. Status and evidence vocabulary | 5. Multi-client | 6. What it lacks that we built |
|---|---|---|---|---|---|---|
| **Vanta** | Left nav: Home, Tests, Documents, Reports, Compliance (frameworks), Manage, Settings [P leading-grc-ux; [M](https://www.vanta.com/resources/vantas-new-look-a-customer-based-redesign)]. A dismissible Compliance Roadmap walks setup [P; [D](https://help.vanta.com/en/articles/11345375-getting-started-resources-in-vanta)]. Scoping is a Scope tab on each framework ([D](https://help.vanta.com/en/articles/11345359-adaptive-framework-scoping)). | Home shows "Compliance Progress" for up to three frameworks, Monitoring cards with a hover breakdown, and "View Tasks" (SLA items due or overdue) ([D](https://help.vanta.com/hc/en-us/articles/7238685176468-Home-Page)). Not a blocker list. | Framework > More: Export controls (CSV), **gap assessment (PDF)**, all framework evidence (ZIP). The doc names no approval step ([D](https://help.vanta.com/en/articles/14998654-exporting-your-data-from-vanta)). Reports can be shared or scheduled ([D](https://help.vanta.com/en/articles/11345500-vanta-reports)). The pre-audit "readiness checklist" is a guidance article and blocks nothing in the product ([D](https://help.vanta.com/en/articles/11345845-audit-readiness-checklist)). | Controls: **OK / Needs evidence**, derived. Audit requests: Not ready, Internal review, Audit ready, Flagged/Accepted [P; [D](https://help.vanta.com/en/articles/12293647-information-request-list-irl-in-vanta)]. | MSP Console: "Add Customers" (name, domain, package, framework). Partners co-manage client instances ([D](https://help.vanta.com/en/articles/11346127)). I could not confirm a cross-client progress view. | No sign-off before export. No profile approval. "Audit" is a separate object, run with the auditor. |
| **Drata** | Dashboard, Controls, Frameworks, Tasks, Audits [P]. | Per-framework **readiness %**, a bar and "remaining controls". A card opens Controls filtered to **Not Ready**. Frameworks at 0% stay hidden. Task list shows upcoming and overdue items ([D](https://help.drata.com/en/articles/13259515-dashboard-overview-new-experience)). | An audit generates ZIP packages (pre-audit package, control evidence). "Past downloads" keeps earlier ones ([D](https://help.drata.com/en/articles/13606029-download-audit-evidence-new-experience)). | **Ready / Not ready**, derived from evidence, tests, policies and approvals. A pending control approval blocks readiness [P; [D](https://help.drata.com/en/articles/13372784-assess-and-manage-individual-controls-new-experience)]. | Workspaces split products inside one company, not separate clients ([D](https://help.drata.com/en/articles/13604282-create-and-manage-workspaces)). No public MSP console found. | No gate on exports. The gate lives inside the audit. |
| **Secureframe** | Home charts, Monitoring > Controls, Frameworks, Data Room [P]. Defense Navigator starts with **scoping questions** (contracts, CUI flow, vendors), then shows only the applicable controls ([M](https://secureframe.com/blog/secureframe-navigator.md)). | Homepage: Testing %, Control Health, and "Action Items" (owner, due date) for upcoming work ([D](https://support.secureframe.com/en/articles/15111099-homepage-charts-action-items-and-frameworks)). Navigator: "what's complete, what's in progress, what's at risk, and what needs attention next" ([M](https://secureframe.com/blog/secureframe-navigator.md)). | SSP: Exports tab, **"Generate export"** with a short description, listed in an exports table, Word output ([D](https://support.secureframe.com/en/articles/15111385-building-and-managing-a-system-security-plan-ssp)). Framework export goes to the Data Room ([D](https://support.secureframe.com/en/articles/15111055-faqs-reports-and-exports-downloads-csvs-and-reporting-workflows)). No approval documented. | Objectives: **Implemented / Not Implemented / Not Applicable**, rolling up to the control ([D](https://support.secureframe.com/en/articles/15111385-building-and-managing-a-system-security-plan-ssp)). Health: Healthy, At risk, Unhealthy, Draft. Manual override needs a reason, and "restore" puts it back [P]. | Not verified. | Export history is a plain list. No issue act. |
| **Hyperproof** | Programs > Requirements > Controls > Proof; Work items; Audits [P]. | The program widget shows % and count of requirements **Completed / In progress / Not started / N/A** ([D](https://docs.hyperproof.io/cm/en/getting-started/understanding-the-program-dashboard/program-dashboard-widgets)). Health comes from five dimensions [P]. | Proof export as ZIP from a program or audit ([D](https://docs.hyperproof.io/audits/exporting-proof-from-audits)). Issue export to Excel "approximate[s]" a POA&M ([R](https://intercom.help/hyperproofio/en/articles/14303716-release-notes-2024-jul-08)). | Freshness: Fresh / Expired. One proof item links to many controls [P]. | Partner programme exists ([M](https://hyperproof.io/partner-program)). No multi-client UI documented. | No approval before export. |
| **ControlMap** (ScalePad) | MSP dashboard of client tenants (Launch, Overview, Progress tab). Inside a tenant: Frameworks > New Framework > Import Content [P msp-grc; help centre *(403 today)*]. | Domain readiness with yes/partial/no counts, e.g. "IR 42%, 5 gaps", and "142 of 320 questions answered" ([M](https://www.scalepad.com/controlmap/cmmc)). | A Reports tab. SSP generated "per DoD guidelines" and exported ([M](https://www.scalepad.com/updates/automate-system-security-plans-ssp-directly-in-controlmap)). Users report gaps in the CMMC audit report ([R](https://community.scalepad.com/controlmap-59/controlmap-audit-report-missing-info-4842)). | Answers: **Yes / No / Partially / N/A**. Evidence status runs on its own track [P]. | Multi-tenant dashboard. Prospect tenants run a pre-assessment report [P]. | No profile approval. No issue act. |
| **Cynomi** (vCISO) | Per-client sub-accounts and an admin panel. Starts with an **onboarding questionnaire**, which generates follow-up questionnaires ([R](https://thehackernews.com/2024/04/hands-on-review-cynomi-ai-powered-vciso.html)). | Sections show **In Progress / Completed** and "18/24, 75%" ([M](https://cynomi.com/platform/assessments/)). A prioritised task list by severity, with short, medium and long-term plans and due dates ([R](https://thehackernews.com/2024/04/hands-on-review-cynomi-ai-powered-vciso.html)). | Full, Risk Findings and Compliance reports, "at the click of a button with your own branding". No approval described ([R](https://thehackernews.com/2024/04/hands-on-review-cynomi-ai-powered-vciso.html)). | Task status. Questionnaires can be revised at any time and policies update with them. | Multi-tenant home ([M](https://cynomi.com/?p=9471)). Branded reports support QBRs ([M](https://cynomi.com/platform/assessments/)). | No sign-off. Reports are available at any stage. |
| **Kaseya Compliance Manager GRC** | Organization > Site > modules (Assessments, Reports). Wizard per question plus a list view [P]. | Radial status graph, a to-do list, a progress bar [P]. | Results & Evidence > Reports > **Generate Reports**, then Regenerate. Download one file or a .zip. **Archive** keeps the report set as a record. No sign-off ([D](https://www2.rapidfiretools.com/cm-grc/help/cm-grc-docs/cm-grc-generate-reports.htm)). POA&M: Generate > Review and Remediate > Export Issues > Regenerate, and "an archived copy… is saved" ([D](https://www2.rapidfiretools.com/cm-grc/help/cm-grc-docs/cm-grc-plan-of-action.htm)). | Yes Fully, Yes with Technical Issues, Partially, No. "Unsure" in the baseline [P]. | Multi Sites view [P]. | Has **no** sign-off. Reports want a finished assessment, which reviewers criticise [P]. |
| **HHS SRA Tool v3.7** | Practice info, assets and vendors, then seven sections, each ending in a Section Complete summary (user guide pp. 8–21; [D](https://healthit.gov/sra_tool_user_guide_version_3-7/)). | A white check mark per section. The summary shows **Areas of Success / Areas for Review**. "Section Reviewed/Confirmed" stamps the user and date ([D](https://healthit.gov/sra_tool_user_guide_version_3-7/), p. 20). | "To access the reports… the assessment must be **100% completed**". Section PDFs export earlier ([D](https://healthit.gov/sra_tool_user_guide_version_3-7/), FAQ p. 28). | Graded answers, "I don't know", "Flag for later" [P]. | None. | The one tool that gates reports, and it is criticised for it [P hipaa-tools]. |
| **CMMC specialists** | FutureFeed's "subway": Company Profile > Technology > **Assess** > SSP > **Deliverables** ([D](https://support.futurefeed.co/knowledge-base/how-tos)). Totem: Controls, Artifacts, CAPs, Dashboard [P cmmc-tools]. | Totem dashboard: status distribution, Not Met by family, SSP progress, score [P]. Exostar: live SPRS and POA&M status on a dashboard ([M](https://exostar.com/certification-assistant)). | FutureFeed: Deliverables > Compliance Reports > Generate SSP > **"Review and Approve it"**. Exports have no approval ([D](https://support.futurefeed.co/knowledge-base/how-to-export-your-assessment-for-customers)). It keeps an "inventory history of deliverables" ([D](https://support.futurefeed.co/knowledge-base/how-tos)). Exostar: SSP "with a click" ([M](https://exostar.com/certification-assistant)). | MET / NOT MET / N/A. Totem adds "Trending Met" [P]. | Totem CMMC Expert tier lets an MSP run all clients in one place [P]. | FutureFeed approves the SSP only. Not verified: CyberSaint (no public docs found), Intelligent Waves (no product found), Summit 7 (a services firm, [M](https://www.summit7.us/solutions/managed-services/vigilance)). |

**Did any tool print a flat blocker list?** No. The nearest is the HHS "Areas for Review"
list, and that is a *finding* inside a report, not a to-do. Work left is shown in four ways:
a percentage per framework, a remaining count that opens a filtered list (Drata), section
checkmarks (HHS), or an owner-and-due-date task list (Secureframe, Drata, Cynomi). It is
grouped by framework, family or domain, owner and due date.

---

## (b) The convergent pattern (the "standard flow")

1. **Home lists clients or frameworks, each with one progress figure.** Vanta, Drata,
   ControlMap and Cynomi all do this. Nobody's home page is a module menu.
2. **Onboarding is a short scoping step, then straight into the control list.** Cynomi's
   onboarding questionnaire, Secureframe's scoping questions, Vanta's "Add customer +
   framework" and ControlMap's "New Framework > Import". Scope can be revised later and is
   never approved up front.
3. **The working view is a list of controls or requirements.** Each row carries a status,
   and there are filters. Progress reads as "x% / n remaining", and clicking the number
   opens the rows behind it, pre-filtered (Drata).
4. **A to-do list carries owners and due dates**: tasks, action items, POA&M. It is kept
   separate from the control list.
5. **Evidence is a library.** Files are uploaded once, linked to many controls, and marked
   fresh or expired.
6. **Deliverables are a "Generate / Export" button on the framework or on a Reports or
   Deliverables page, available at any time.** Regenerating is normal. Earlier versions
   survive as an export history, archive or past downloads (Secureframe, Kaseya, Drata,
   FutureFeed).
7. **A gate appears only at the finishing moment, and only for the item being finished.**
   Examples: the audit request status in Vanta and Drata, the SSP "Review and Approve" in
   FutureFeed, HHS's 100% rule. No tool keeps a standing "blockers" panel while you work.
   This is Johnathan's principle, and the market follows it.

---

## (c) Our app today, mapped to the standard flow

| Step | Ours (`main`, Oct 12) | Deviation, and why it hurts a consultant |
|---|---|---|
| Home | None. There is a project `<select>` in the rail (`App.tsx:569`) and "Other client projects" at the foot of Overview. | No cross-client view, so he cannot see which client needs him today. |
| Onboarding | Setup, then "Create and start", which lands on requirement 1 (ADR 0020). | **Aligned**, apart from the readiness pill ("Intake complete") on every requirement toolbar (`App.tsx:649, 681`). That pill is internal state shown as if it were progress. |
| Profile | "Versioned project profile" with lifecycle and "Approve version" (`ProfilePanel.tsx:697,764`). The step rail reads "Scope · **Profile not approved**". | No shipped tool approves a profile. "Not approved" reads as a failure on day 1, and the page gives no measure of how complete the profile is. |
| Assess | Requirement list with status dots and decided/total counts. A score line in the toolbar. | **Aligned.** The HIPAA list has no status markers (screenshot 144/03). |
| Overview | Step rail. SPRS **−203** with three red **FAIL** boxes on a blank project. Family table. NOT MET list. A **"Left before issue"** block of grouped counts with "Show every item". The Deliver step reads "323 items left before issue" (`OverviewView.tsx:195-220`, `overview.py:185-195`; screenshot 144/01). | This is a standing blocker panel, which breaks the principle. A blank project opens on a wall of red. The labels are also wrong: HIPAA says "Objectives not decided", and "2 · Profile not approved" counts one Profile twice (screenshot 145/07). |
| To-do / POA&M | None. POA&M lives inside each requirement. | Every tool in the table has a task or POA&M list with owners and due dates. |
| Evidence | Library with Current / Due soon / Stale filters and a lead-time setting. | **Aligned.** It lacks a "used by N" count and a coverage filter. |
| Reports | "Reports and packages", with "Download draft" and "Review and issue…". Below that, "Issued versions" with Reissue and Reopen forms (`ReportsView.tsx`). | The words are ours ("issue", "package", "reissue", "superseded"). One draft ZIP has no per-document choice. **For CMMC, issuing still requires 110/110 Met** (`close.py` and `framework.py`), because the gap-assessment package (#146) is not built. A readiness client therefore always sees blockers that can never clear. |
| Finish act | One modal with "Must be fixed before issue" (grouped) and "Worth checking" (`ReviewAndIssue.tsx`). | **This is the right place for blockers.** It needs plainer words. |

---

## (d) Recommended target flow and navigation (consultant first)

**Top nav (inside a client):** `Overview | Assess | Profile | POA&M | Evidence | Deliverables`,
plus the SRA tab for HIPAA. A **Clients** home sits above it, reached from the logo. Every
item uses a noun the tools in the table already use.

**Rule for every working screen:** show progress ("x of y decided"), the next item to
work on, and to-dos. Never show "blockers", "left before issue", "not approved" or
"FAIL" before someone asks to finish.

What to do with each concept:

1. **The "Close readiness" panel.** It is already gone from `main` (`App.tsx:32` now
   imports only `BackupControl` and `RevalidationPanel`). Do not bring it back. Build a
   fresh Windows package so Johnathan stops testing the old one.
2. **Overview "Left before issue" counts and "Show every item".** Remove both from Overview.
   Their information becomes progress and next work:
   - "Assess: 10 of 149 decided"
   - "Remediate: 10 gaps need a POA&M · 3 POA&M items due this month"
   - "Evidence: 12 Met awaiting evidence"
   Each figure stays clickable and opens the filtered list (the existing `openGroup`).
   Keep `close.fieldwork_ready` and its `groups`. Stop calling it from `api/overview.py`
   for the page body. Either drop `left_before_issue` from the response or keep it unused
   for one release.
3. **Step-rail figures.**
   - Scope: "Profile: 14 of 20 facts known · 2 to follow up". Never "not approved".
   - Assess: unchanged.
   - Remediate: as above.
   - Deliver: "Draft available" or "Final v2 · 12 Oct 2026". Never an item count.
4. **Score panel on a new project.** Before the first decision, show "Not started", not
   −203. Keep the 32 CFR 170.21 checks visible, as the spec requires, but neutral grey
   ("evaluated once every requirement is decided") until then. Mark one red only when it is
   actually evaluated and fails. The verified score stays the headline, and the projected
   score stays secondary and labelled.
5. **"Review and issue" dialog.** Rename it **"Finalize deliverables"** and keep it as the
   only place gates appear. Sections:
   - "Fix before finalizing": the hard gates, grouped, each link opening the filtered list.
   - "Worth a look": warnings.
   - "What will be locked": Profile version N, the assessment and the documents.
   - "Finalize".
   Keep the automatic backup, the reviewer, the date, the optional note and the immutable
   record exactly as built in ADR 0021.
6. **Profile approval and readiness states.** Approve inside the Finalize act. When the
   Profile has no unknowns, finalizing approves the current version in the same transaction.
   Unknowns stay a hard gate and are listed in the dialog. The Profile page shows
   completeness and an optional "Approve now". The readiness pill leaves the working
   toolbar, and readiness history stays under "advanced".
7. **Reports tab → "Deliverables".** One row per document type:
   - HIPAA: report, POA&M workbook.
   - CMMC: gap report, SPRS worksheet, POA&M, SSP, evidence index.
   Each row has **Download draft**. One **Finalize…** button covers the set. Below that
   sits **"Final versions"**, a history list (Secureframe and FutureFeed pattern): "Final
   v2 · 12 Oct 2026 · Johnathan · replaced v1". "Reissue" becomes "Correct wording (same
   findings)…" and "Reopen" becomes "Change findings (new version)…", both in a row menu.
   The engine's Draft / Issued / Superseded stay as stored states and in the audit trail.
8. **Evidence tab.** Keep it. Add "Used by N objectives" and a "Requirements with no
   evidence" coverage filter, and rename "Stale" to "Expired" (Hyperproof's word).
9. **CMMC gap clients.** Finalize must produce the gap-assessment package (#146).
   Otherwise the gate can never clear. Move the 110/110 internal readiness close behind a
   second option, "Final self-assessment (all requirements Met)".
10. **CaaS later.** The Clients home grows a "this month" column (meeting focus points,
    POA&M due, evidence expiring). The yearly assessment is a reassessment, and
    "Final versions" doubles as year-over-year history (Kaseya archive pattern).

The spec requirements keep their substance and change only in how they are shown: verified
vs projected SPRS, immutable issued versions, audit trail, Profile complete before issue,
pre-issuance backup, and HIPAA's no-blank rule. All are still enforced inside Finalize.

---

## (e) Prioritised change list (first-time tester's experience first)

| # | Change | Files likely touched | Size | Risk to tests or spec |
|---|---|---|---|---|
| 1 | **Overview becomes progress-only.** Remove "Left before issue" and "Show every item". Recast the step-rail figures as progress or next work. Keep the clickable figures. | `api/overview.py`, `web/src/views/overview/OverviewView.tsx`, `web/src/types.ts`, `App.tsx` (openGroup reuse) | M | Updates `api/tests/test_issue_144_overview.py` and `web/src/Overview.test.tsx`. **Contradicts the spec's Accepted Interaction Model amendment** ("what is left before issue as grouped counts"), so it needs Q1. |
| 2 | **Neutral blank state.** Score shows "Not started" until the first decision. 170.21 checks grey until evaluated. Drop the bullet list `score.blockers` from Overview. | `web/src/views/assessment/CmmcScore.tsx`, possibly `api/cmmc.py` (a `started` flag) | S | `test_issue_141_verified_score.py` unaffected if the API is unchanged. Spec unchanged (the checks stay shown), but see Q4. |
| 3 | **Label bugs.** HIPAA group says "Specifications not decided", not "Objectives". The Profile group is counted once (dedupe `profile_not_complete` + `profile_not_approved`). | `api/close.py` (`_GROUPS`, `_groups`) | S | `test_issue_144_grouped_blockers.py` string updates. No spec change. |
| 4 | **Finalize dialog wording and "What will be locked".** Rename the actions and states in the UI only. | `web/src/views/reports/ReviewAndIssue.tsx`, `ReportsView.tsx` | S | String asserts in `ReviewAndIssue.test.tsx` and `App.test.tsx`. UI words only; see Q3. |
| 5 | **Gap-assessment package (#146)** as the default CMMC finalize. | `api/issuance.py`, `api/close.py` (a CMMC gap gate set), renderers, `ReportsView.tsx` | L | Already in the spec (AC-025). Touches the issuance tests. Q5 confirms it is the default. |
| 6 | **Profile approval inside Finalize.** Remove the standing "not approved" text and show completeness. The readiness pill leaves the toolbar. | `api/issuance.py` (`review_and_issue` approves the current version when unknowns = 0), `api/main.py` profile lifecycle, `ProfilePanel.tsx`, `App.tsx:649, 681` | M | `test_issue_145_profile_once.py` and `test_issue_145_issue_act.py`. Needs Q2. |
| 7 | **Reports → Deliverables.** Per-document draft rows, a "Final versions" history, row-menu corrections. | `ReportsView.tsx`, `ClosePanels.tsx`, draft endpoint (a per-component option) | M | `ReviewAndIssue.test.tsx` and draft tests. The ADR 0021 behaviour is unchanged. |
| 8 | **POA&M view.** All items across requirements, with owner, due date, status and 170.21 eligibility filters. | new `web/src/views/poam/`, read API over existing POA&M rows | M | The spec's nav already lists Actions/POA&M. Low risk. |
| 9 | **Clients home.** One card per client project: framework, % decided, verified SPRS or HIPAA counts, last final, next due. | `App.tsx` shell, new `views/home/`, a small `api` read endpoint | M | The spec already calls for a Dashboard. Low risk. |
| 10 | **Evidence coverage.** "Used by N", a "no evidence" filter, "Expired" label. | `EvidenceLibraryView.tsx`, `api/evidence_library.py` | S | `EvidenceLibrary.test.tsx` labels. |
| 11 | CaaS service year, monthly meeting and change log (later). | new record types (migration 0023+) | L | Spec'd; schedule after Johnathan's re-test. |

Order rationale: 1 to 4 remove what a new tester sees in the first two minutes (red wall,
"not approved", wrong nouns). Item 5 removes the dead end for every CMMC readiness client.
Items 6 and 7 remove the remaining invented concepts. Items 8 to 10 add the standard views
he will look for.

---

## (f) Decisions for Johnathan (yes/no, with my recommendation)

1. **Overview stops showing "what is left before issue".** Blocker reasons appear only in
   the Finalize dialog, and Overview shows progress and next work. This amends the spec's
   *Overview shows where the engagement stands* paragraph. **Recommend: yes.** It is your
   October 12 rule, and no shipped tool keeps a standing blocker panel.
2. **The Profile is approved as part of Finalize**, with no separate approval needed
   beforehand (optional "Approve now" kept). It is still one approval per version, and
   unknowns still block. **Recommend: yes.** No shipped tool approves a profile up front;
   FutureFeed approves the SSP at generation time.
3. **Screen words change; stored states do not.** "Review and issue" becomes "Finalize",
   "Issued" becomes "Final", "Superseded" becomes "Replaced", and "Reports/packages" becomes
   "Deliverables". The audit trail and stored states keep Draft / Issued / Superseded.
   **Recommend: yes.**
4. **The 170.21 checks show as "not yet evaluated" (grey) until every requirement is
   decided**, instead of red FAIL on a blank project. **Recommend: yes.** The spec says
   "show alongside the score", and this still shows them.
5. **For CMMC, Finalize defaults to the gap-assessment package.** The 110/110 internal
   readiness close becomes a second, explicit option. **Recommend: yes.** It matches
   ADR 0019 item 5 and is what readiness clients buy.
6. **Confirm ADR 0020** (the Start click records Intake complete; the spec sentence on
   Intake complete is relaxed). **Recommend: yes.** It is still marked pending.
7. **Add a Clients home and a POA&M view before more CaaS features.** **Recommend: yes.**
   Both are already in the spec's navigation, and every comparable tool has them.

What was not verified: ControlMap's help centre returned 403 today, so its rows rely on the
October 8 track. Drata and Vanta partner multi-client progress views have no public docs.
For Totem only the support home page was readable today. CyberSaint, Intelligent Waves and
Summit 7 software: no public product documentation was found.
