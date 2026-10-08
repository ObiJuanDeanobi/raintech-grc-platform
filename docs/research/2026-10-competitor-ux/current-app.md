# RainTech GRC — how a user actually moves through the current app

Research date: October 8, 2026. Repository `main` at `ef22eb0`. Read-only: no repository files were changed.

Sources:
- `docs/specification.md` (Primary Workflow, V1 scope, Navigation, Accepted Interaction Model)
- `docs/OPERATOR_RUNBOOK.md`
- `PROJECT_STATUS.md` (Active ticket)
- GitHub issues #127, #128, #130 and #131, read through the REST API
- `web/src/App.tsx`, `web/src/ProfilePanel.tsx` and `web/src/SraPanel.tsx`
- `api/main.py`, `api/framework.py`, `api/close.py`, `api/ssp.py` and `api/package_review.py`
- Existing screenshots under `docs/evidence/` and `docs/screenshots/`

**The app was run.** I copied it to a scratch directory, ran FastAPI on :8000 and Vite on :5173, and drove it with headless Chromium. I created synthetic CMMC and HIPAA projects and took new screenshots in
`screens/` (a subset is committed next to this file):

| File | What it shows |
|---|---|
| `01-setup.png` | First-run "Create a client project" |
| `02-cmmc-profile-top.png`, `03-cmmc-profile-full.png` | A new CMMC project opens on its Profile |
| `04-cmmc-requirement-page.png` | CMMC requirement page, top of the screen |
| `05-cmmc-requirement-objectives-scrolled.png` | The same page scrolled to the objective list |
| `06-cmmc-objective-page.png` | A single-objective page |
| `07-cmmc-met-without-evidence.png` | Clicking Met with no evidence: "Save failed · Retry", no reason given |
| `08-cmmc-overview.png`, `09-cmmc-overview-package-panel.png` | Overview, and the package panel about 11,000 px down |
| `10-hipaa-profile.png`, `11-hipaa-first-record.png`, `12-hipaa-second-record.png` | HIPAA path |
| `14-hipaa-sra.png` | The SRA tab before Profile approval: one red line on an empty page |
| `15-hipaa-overview.png` | HIPAA Overview |

Measured on a new synthetic CMMC project at 1440×900, with 0 of 320 objectives answered:
- The Overview scrolls to **11,455 px**.
- The close panel shows **323 blocker lines** and **322 "Next actions" link buttons**.
- "Assessment package" starts **11,044 px** down the page.
- On the requirement page, the objective list starts at **y = 850 px**, at the bottom edge of the first screen, below the guidance, SSP and score panels.

A new HIPAA project shows **153** close blockers.

---

## 1. Step-by-step flow, from launch to an issued package

### Shared start (both frameworks)

| # | Screen | What the user does | Clicks / transitions |
|---|---|---|---|
| 1 | **Setup** (`Setup`, App.tsx:482) on first run; otherwise the **"+ Client / project" modal** (`WorkspaceCreator`, App.tsx:567) | Type the client name and project name, pick the framework (HIPAA is the default), then "Create workspace" or "Create and open". | ~4 actions, 1 transition |
| 2 | **Profile view**. A new project opens here (App.tsx:2052, 2492). The page stacks `ProfilePanel` above `ReadinessPanel` (App.tsx:2025-2034). | See the Profile notes below this table. | Long scroll (2,472 px on an empty Profile) |
| 3 | **Assessment readiness**, at the bottom of the Profile page (App.tsx:132-224) | Choose "Next state" = *Intake complete*, type a **Decision note** (required, App.tsx:180; api/main.py:2718), then "Record transition". | 3 actions |
| 4 | Same panel | Click **Start assessment** (App.tsx:155). The view switches to Assessments (App.tsx:2032). | 1 action, 1 transition |
| 5 | Profile page, at any later time | **Approve the Profile version** (see the lifecycle in the Profile notes). Required by the SSP (api/ssp.py:129), the HIPAA SRA (api/main.py:4627) and close (api/close.py:154). | ~3 actions |
| 6 | Profile page, readiness panel | **Record *Profile complete***: decision note, **Named reviewer**, **Review / approval evidence** (App.tsx:195-205; framework.py:57-76), and no unresolved fields. Close needs this as well as the approved version (api/close.py:146-160). | ~5 actions |

Profile notes (step 2):
- The page is a **neutral form with no released template** (ProfilePanel.tsx:740-743). Project metadata holds only "Project name". Every other section is an empty "Add …" list: Environments, Business processes, Locations, External services, People and roles, Exclusions, References, Unknowns.
- Every value has **four inputs**: value, Source, Reviewer and Last reviewed (ProfilePanel.tsx:115-185).
- Saving is **manual** ("Save draft", ProfilePanel.tsx:924-931). There is no autosave here.
- The spec's onboarding questionnaire, CMMC quote, project end date, Stack/Tools fields and flow rows are **not built**. Neither `api/main.py` nor `web/src` contains "quote" or "end_date".
- Version lifecycle (step 5): type a "Lifecycle reviewer", click **Record review** (Draft → Reviewed), then **Approve version** (Reviewed → Approved) (ProfilePanel.tsx:745-782). To edit an approved version you must "Create new version".

Note on step 3: *Intake complete* can be recorded with an entirely empty Profile. The gate is a self-attestation note; no field is checked. I did exactly this when making the screenshots.

### CMMC Level 2 path

The unit is one page per record. The work list holds 430 records: 110 requirements and 320 objectives.

| # | Screen | What the user does |
|---|---|---|
| C1 | **Assessments**, which opens on requirement 001, AC.L2-3.1.1 (App.tsx:1767). The requirement has **no editable determination** ("Rolled up · Derived requirement status"). | Scroll past the RainTech guidance, the **SSP panel** ("Not generated · Generate SSP") and the **Official score** panel to reach "Assessment objectives" (App.tsx:2239-2275). Each objective row is a **button that navigates to another page** (App.tsx:2266). The status pills are read-only. |
| C2 | **Objective page** (for example AC.L2-3.1.1[a]) | Requirement context card at the top. A Determination panel on the right with Met / Not Met / Pending (no N/A). An **empty "Questions to work through — 0 questions"** panel, because CMMC has 0 assessor prompts (Overview metric). Notes, then the evidence form. |
| C3 | Objective page, evidence (right rail) | **Before Met is allowed:** "Add evidence file" (upload) or choose an "Existing artifact", type a **Support rationale** (required), click **Map to this record** (App.tsx:1417-1449). Alternatively, expand "Document an interview or observation" and type there (App.tsx:833-843). Each mapping is per objective, so reusing one file across 6 objectives means 6 dropdown + rationale + map cycles. |
| C4 | Objective page | Click **Met**. It saves immediately (App.tsx:780-781). Without evidence the API refuses with "Met requires mapped evidence or a documented interview/observation" (api/main.py:3078-3092). **The UI shows only "Save failed · Retry" and the pill still says Met** (screenshot 07; App.tsx:339-348, 420-431). |
| C5 | Move on | Use **Next** (sequential through all 430 records, requirements included) or "Open requirement and all objectives" (App.tsx:2204), then click the next objective. |
| — | Repeat | C2-C5 runs **320 times**, at least 320 page transitions, plus about 110 requirement-page visits. With evidence attached the way the gate requires, that is roughly 4-6 actions per objective, about **1,300-2,000 actions** for fieldwork. |
| C6 | **Requirement page → "Scoring and finding" panel** (right rail, App.tsx:878-995) | When a requirement derives Not Met, one finding is created automatically. The user adds **POA&M items** (title and description, then "Add POA&M item"). For IA.L2-3.5.3 and SC.L2-3.13.11 the user must also record the partial or none implementation level with a rationale (App.tsx:951-957). |
| C7 | Remediate | Flip every failed objective to Met, with evidence. Then, on the requirement page, click **Close item** on each POA&M item and answer a browser **`window.prompt`**: "How was the remediation verified?" (App.tsx:921). |
| C8 | **SSP panel** (shown on every requirement *and* objective page, App.tsx:2239-2246) | "Generate SSP" is refused until **all 110 requirements are Met or Not Met** and a Profile version is approved (api/ssp.py:128-151). Before that, the button is live and clicking it only shows an error. After generating: write the System description and Environment narrative, then **visit each of the 110 requirement pages** to write that requirement's implementation statement. Statements are prefilled from notes where they exist. "Save new version" creates one SSP version per save (App.tsx:1080-1123). **Approve and freeze** is disabled until nothing is missing. |
| C9 | **Overview → Close readiness** (App.tsx:1486-1508, 2391) | Blocked until **every objective is Met** (`final_statuses: ["Met"]`, framework.py:338), no POA&M item is open, the SSP is approved, evidence hashes verify, and the Profile is complete and approved (api/close.py:146-160, 377-417). **A CMMC project with any Not Met cannot produce a package at all.** No gap report, score report or POA&M is issuable mid-engagement. |
| C10 | **Overview → Package generation** (App.tsx:1510-1580), about 11,000 px down | "Generate package": assessment report, SSP, POA&M history and evidence index. The copy still says "report and POA&M", the HIPAA wording. |
| C11 | Package review (same card) | Fill in **Reviewer name**, **Reviewer role** and **Review note**. Tick **one checkbox per component** (4) plus "Confirm source snapshot and template version". Then **Start review → Mark reviewed → Sign off: Ready to issue**: three clicks by the same person (App.tsx:1577; api/package_review.py:196-211). |
| C12 | **Issue final deliverables** (App.tsx:1582-1618) | **Create and validate backup**, then **Issue final deliverables**. |

**Governance acts to issue a CMMC package (count):**
1. Intake complete
2. Record review
3. Approve version
4. Profile complete, with reviewer and approval evidence
5. SSP Approve and freeze
6. Start review
7. Mark reviewed
8. Sign off
9. Backup
10. Issue

That is 10, matching #131. On top of these: one `window.prompt` rationale per POA&M item and one rationale per evidence mapping.

### HIPAA path

The unit is one implementation specification, or a standard that has none, per page. The list holds 194 records, 149 of which carry a determination.

| # | Screen | What the user does |
|---|---|---|
| H1 | **Assessments** opens on record 001, "Security management process", a **derived standard with no editable determination** (screenshot 11). The first screen is not actionable. | Click Next. |
| H2 | **Record page** (screenshot 12) | Standard context card. "Questions to work through": NIST 800-66 / OCR prompts, each with its own autosaving textarea. The checkbox is a read-only "answered" indicator (App.tsx:676-709). On the right: Determination (Met, Not Met, Pending, N/A), notes and evidence. |
| H3 | Determination | **Met** needs evidence or an interview record (same silent "Save failed" as CMMC). **N/A** needs a rationale. **Addressable** specifications need a Disposition, plus Reasoning for anything other than the standard measure (App.tsx:789-832; api/main.py:3049-3068). |
| H4 | **Not Met → Reconciliation** panel (App.tsx:1125-1200) | Choose a disposition (create a prefilled finding and corrective action, link existing IDs by typing raw IDs, or Not needed with a rationale), then "Save reconciliation". To get back to Met later: **Mark Ready for Validation**, then **Record validation** (outcome and notes), then set Met. Met is refused while a linked corrective action is unvalidated (api/main.py:3065-3077). |
| — | Repeat | H2-H4 runs for 149 determination records, with about 45 extra page turns through the derived standards. |
| H5 | **Security Risk Analysis tab** (top nav, appears only once an assessment exists, App.tsx:2072) | Until a Profile version is approved it shows **only a red line, "Approve a Profile version before completing the SRA", on an empty page** (screenshot 14). Afterwards: Include or Exclude every approved-Profile system, location, vendor and flow, with a rationale for each exclusion. Then the risk form: 15+ fields, likelihood and impact as 1-5 number boxes, and an approver plus timestamp for High or Critical acceptance (SraPanel.tsx:242-318). |
| H6 | **Overview → Close readiness** | Blocked until the Profile is complete and approved, all 149 determinations are final (Met, Not Met or N/A), every Not Met is reconciled, and the SRA scope and at least one complete risk exist (api/close.py:146-374; framework.py:162-173). A new project starts with **153 blockers**. |
| H7-H9 | Package, review, issue | Same as C10-C12, with 2 components (DOCX report and XLSX POA&M). |

HIPAA governance acts: the same list without the SSP, so **9**.

---

## 2. Navigation structure and unit of work

**Top bar** (App.tsx:2063-2087):
- `Assessments | Overview | Profile | [Security Risk Analysis — HIPAA only] | Actions (always disabled)`.
- Right side: save state, "Back up now", and "Johnathan".

**Left rail** (always visible in the Assessments, Overview and Profile views once an assessment exists, App.tsx:2089-2142):
- Client-project `<select>` and "+ Client / project".
- "GAP ANALYSIS · Work list" with search and a work-area filter.
- CMMC: the 110 requirements, plus the 6 or so objectives of the active requirement nested under it (116 rows when on AC.L2-3.1.1). The row numbers are re-indexed on the filtered list (App.tsx:2136), so they are not stable.
- HIPAA: all 194 records.

**Centre plus right rail** on Assessments: the record brief, guidance, objectives (CMMC) and questions, then the right "Working record" (determination, finding or reconciliation, notes, evidence). Overview and Profile **replace the centre and hide the right rail**, but the work list stays on screen.

**Before an assessment exists**, a different shell is used (App.tsx:1989-2059). It has no left rail, and the project selector sits in the page body.

**Not present**, although the spec's navigation lists them:
- Dashboard / Unified Queue.
- Client Queue.
- Actions/POA&M: the button is disabled at App.tsx:2001 and 2075.
- Evidence: the library and recycle bin are a collapsed `<details>` inside *each record's* evidence panel (App.tsx:1450-1481).
- Risks: HIPAA's are under the SRA; CMMC has none.
- Policies and Reports.
- The assessment sub-tabs Scope | Gap Analysis | Findings | Validation | History.

**Unit of work:**
- **CMMC:** one *assessment objective* per page (determination-bearing). The requirement page is a read-only roll-up with the finding, POA&M, SSP and score panels. Objective statuses cannot be set from it.
- **HIPAA:** one *implementation specification*, or one standard that has none, per page. Each page carries 0 to 18+ *questions* with free-text answers. The questions do not set status.

---

## 3. What gates or blocks the user

| Gate | Rule | Where |
|---|---|---|
| Start assessment | Readiness must be *Intake complete* or *Profile complete*, and a decision note is required. | framework.py:46-56; api/main.py:2718, 2795-2802 |
| Profile complete | No unresolved fields (free-text comma list), a named reviewer, and approval evidence. | framework.py:57-76; api/main.py:2722-2738 |
| Profile approval | Record review, then Approve version, with a reviewer name; unsaved edits must be saved first. | ProfilePanel.tsx:456-522; api/main.py:2159 |
| Met | Mapped evidence **or** an interview/observation text, at the moment Met is clicked. | api/main.py:3078-3092 |
| Met after Not Met (HIPAA) | The linked corrective action must be Validated. | api/main.py:3065-3077 |
| N/A (HIPAA only) | Rationale. CMMC has no N/A. | api/main.py:3049; framework.py:326 |
| Addressable (HIPAA) | Disposition, plus reasoning for an alternative or non-implementation. | api/main.py:3051-3064 |
| CMMC partial credit | Implementation level and rationale for 3.5.3 and 3.13.11. | App.tsx:951-957; api/main.py:3321-3325 |
| POA&M close (CMMC) | Requirement derives Met, plus a verification rationale entered in a browser prompt. | App.tsx:921, 976; api/main.py:3160-3170 |
| SSP generate | Approved Profile, and all 110 requirements Met or Not Met (no Blank or Pending). | api/ssp.py:128-151 |
| SSP approve | System description, environment narrative and all 110 implementation statements non-empty. | api/ssp.py:274-283, 343-350 |
| HIPAA SRA | Approved Profile; every scope fact reviewed; exclusion rationale; at least one complete risk; approver for High or Critical acceptance. | api/close.py:261-357; SraPanel.tsx:310 |
| Close: CMMC | Every objective **Met**, no open POA&M, SSP approved, evidence hashes verified, Profile complete and approved. | framework.py:336-346; api/close.py:146-160, 377-417 |
| Close: HIPAA | Profile complete and approved; every determination Met, Not Met or N/A; N/A rationale; Not Met reconciled; SRA complete. | framework.py:162-173; api/close.py |
| Package review | Reviewer name, role and note on **every** transition; all component checkboxes plus the source checkbox for Reviewed and for Ready to issue; no drift. | api/package_review.py:196-211 |
| Issue | Signed off, a current source, a successful pre-issuance backup, and verified evidence. | api/issuance.py:173-216 |
| Leaving a record | `window.confirm` if any autosave is still saving or failed. A stuck "Save failed" from a refused Met therefore keeps triggering the prompt. | App.tsx:1922-1931 |

---

## 4. What the user sees about progress at each stage

| Stage | Progress signal |
|---|---|
| Setup | None. |
| Profile | The version status pill ("Version 1 · Draft") and the readiness state pill. There is no field-completeness count and no list of required facts. The "Profile completion still needs" list shows only readiness-form items such as "Record a named reviewer". |
| Assessment | The toolbar shows the readiness pill, "**n of 430**" (position) and "**x of 320 resolved**", or "x of 149" for HIPAA (App.tsx:2156-2161). The work list has **no status per row**: no colour, no pill, no per-family count. CMMC adds the Official score panel ("110 of 110 · provisional", Unscored 110). That number starts at the maximum and falls as Not Met objectives come in. |
| Requirement / standard | The derived status pill. CMMC also shows the objective pills on the requirement page. |
| HIPAA SRA | "x% complete" plus a list of what is missing. |
| Overview | Three static catalog counts (determinations, cited records, prompts), which say nothing about progress. Then the profile-readiness line. Then the **flat blocker list**: 323 lines for CMMC, 153 for HIPAA, each like "Final determination required: SI.L2-3.14.7b", followed by the same number of link buttons. Nothing is grouped by family, by gate or by type. |
| Package | State pills: Complete candidate, In Review, Reviewed, Ready to issue, Issued · Current. |

There is no dashboard, no per-family progress, no project completion figure and no "what to do next" summary, although the spec's Accepted Interaction Model calls for a phase rail, a work-resumption panel and a queue.

---

## 5. Where the spec and the build differ

1. **The spec contradicts itself on the CMMC unit of work.**
   - V1 scope (specification.md:104-105): "CMMC uses a **requirement-centered workspace with its assessment objectives visible together**."
   - Accepted Interaction Model (specification.md:493-497): "**Assessments is objective-by-objective.** An objective navigator on the left, a central decision surface…"
   - The build follows the second statement literally: one objective per page, with the objectives on the requirement page as navigation buttons only. The runbook (OPERATOR_RUNBOOK.md:66-68) describes the build accurately.
   - PROJECT_STATUS and #128 call this drift. More precisely, the build matches one half of an internally inconsistent spec. #128 resolves it towards "requirement page, inline objective status".
2. **Navigation.** The spec lists `Overview | Profile | Assessments | Actions/POA&M | Evidence | Risks | Policies | Reports`, with assessment sub-tabs `Scope | Gap Analysis | Findings | Validation | History` (specification.md:465-478). The build has Assessments, Overview and Profile, plus SRA for HIPAA and a disabled Actions button.
3. **Dashboard and queues.** The spec's cross-client Dashboard with a Unified Queue, and the Client Queue on Overview (specification.md:486-492), are absent. Overview instead hosts the close and package panels, which the spec calls orientation-only.
4. **Overview content.** The spec says Overview "does not contain … a separate evidence/risk/report summary strip"; it should be a phase rail, work resumption and the Client Queue. The build puts static metric tiles, the readiness card, a 300-line blocker list, the package workflow and a client-project list on it.
5. **Progressive Profile.** The spec calls for an onboarding questionnaire, baseline / current / target with Confirmed, Changed and Missing statuses, Stack/Tools, an end date and flow rows. The build has a neutral generic form with per-field provenance and no template (ProfilePanel.tsx:740-743). "Intake complete" is a free-text attestation, not a check of required fields.
6. **CMMC quote.** The spec's Primary Workflow step 2 and Slice 2 call for a preliminary quote. It is not built.
7. **Met evidence.** The spec says "A **final** Met determination requires mapped evidence…". The build enforces this at every click, not at close (#130).
8. **CMMC deliverables.** The spec lists CMMC gap/score and POA&M reports. The build can only issue a package at 110/110 Met (internal readiness close). No gap-assessment deliverable exists for a client with gaps.
9. **Autosave.** The spec requires visible "Save failed" with retained edits; that is built. But the Profile is manual-save, and the reason for a failed save is never displayed.

---

## 6. Top 10 friction points, ranked

1. **CMMC is 320 objective pages, not 110 requirement pages.** The objective rows on the requirement page are navigation buttons (App.tsx:2264-2272) with read-only pills. Status is set only on each objective's own page (App.tsx:2309-2320). Next walks all 430 records. See `screens/05-cmmc-requirement-objectives-scrolled.png`, `screens/06-cmmc-objective-page.png` and `docs/evidence/issue-104/CHROMIUM_REQUIREMENT_OBJECTIVES_DESKTOP.png`.
2. **Met is blocked until evidence is mapped, and the reason is hidden.** The API rule is at api/main.py:3078-3092. The autosave hook drops the error message (App.tsx:339-348). The panel shows only "Save failed · Retry" (App.tsx:420-431) while the pill shows the unsaved "Met" (App.tsx:771, 780). The failure then makes every later navigation ask "Changes are still saving or failed to save" (App.tsx:1924) until it is retried or cleared. See `screens/07-cmmc-met-without-evidence.png`.
3. **The Overview is a 300-line wall.** The close panel prints every blocker and every link with no grouping (App.tsx:1503-1505). The package panel sits about 11,000 px below the top. See `screens/08-cmmc-overview.png`, `screens/09-cmmc-overview-package-panel.png`, `docs/screenshots/intake-flow/5-overview.png` and `docs/evidence/issue-108/CHROMIUM_CLOSE_BLOCKED_DESKTOP.png`.
4. **There is no picture of progress.** "x of 320 resolved" is the only meter (App.tsx:2158-2161). Work-list rows carry no status (App.tsx:2130-2140). Overview tiles show catalog constants (App.tsx:2372-2376). The provisional score starts at 110 and goes down.
5. **The sign-off chain is about 10 steps, with the Profile signed off twice.** Profile version Record review and Approve (ProfilePanel.tsx:759-776). Readiness Profile complete, with reviewer and evidence (App.tsx:195-205). Package Start review, Mark reviewed, Sign off, each needing name, role, note and 5 checkboxes (App.tsx:1577; api/package_review.py:196-211). Then backup, then issue (App.tsx:1616).
6. **Evidence mapping is per record and form-heavy.** Each objective needs: choose or upload, type a rationale, click Map (App.tsx:1417-1449). The dropdown labels include the full SHA-256 (App.tsx:1432). The evidence library is hidden in a `<details>` on every record (App.tsx:1450). There is no Evidence view and no bulk mapping across objectives.
7. **The CMMC page is crowded with panels that are not the task.** Guidance, the SSP panel (with a live "Generate SSP" button that cannot succeed until all 110 requirements are decided, App.tsx:1059-1063 and 2239-2246), the score panel and an empty "0 questions" panel (App.tsx:2277-2286) all render on every requirement and objective page. The objective list starts at y = 850 px (`screens/04-cmmc-requirement-page.png`).
8. **The Profile is a blank generic form, and intake is a self-attestation.** There is no questionnaire, template, required-field list, quote or end date. Each value has 4 inputs (ProfilePanel.tsx:115-185) and saving is manual (ProfilePanel.tsx:924-931). "Unresolved required fields" is a free-text comma list (App.tsx:182-185). Intake complete can be recorded on an empty Profile. See `screens/02-cmmc-profile-top.png` and `docs/screenshots/intake-flow/2-readiness-on-profile.png`.
9. **The CMMC end state is all-or-nothing and the remediation loop is clumsy.** Close requires every objective Met (framework.py:338), so there is no deliverable for a client who still has gaps. Closing POA&M items uses a native `window.prompt` (App.tsx:921). SSP implementation statements must be written one requirement page at a time, and each save creates a new SSP version (App.tsx:1099-1117).
10. **Dead ends and confusing entry points.**
    - The disabled "Actions" button is always shown (App.tsx:2001, 2075).
    - The HIPAA SRA tab before Profile approval is an empty page with one red line (`screens/14-hipaa-sra.png`; api/main.py:4627).
    - The assessment opens on a non-actionable derived record: CMMC requirement 001 and HIPAA standard 001 (App.tsx:1767; `screens/04-…`, `screens/11-…`).
    - HIPAA "Link existing finding" asks the user to type raw finding and corrective-action IDs (App.tsx:1196).
    - The CMMC package copy says "report and POA&M" (App.tsx:1576).
    - Blocker labels use bare IDs such as "Final determination required: SI.L2-3.14.7b".

---

## Count summary (minimum path, nothing found wrong)

| | CMMC L2 | HIPAA |
|---|---|---|
| Records in the work list | 430 (110 requirements + 320 objectives) | 194 (149 determination-bearing) |
| Page transitions to decide everything | ≥320 objective pages + ~110 requirement visits; Next walks 430 | ~149-194 |
| Actions per Met with evidence | ~4-6 (pick or upload, rationale, map, Met) | ~4-6, plus answers to 0-18 questions |
| Fieldwork actions (rough) | ~1,300-2,000 | ~700-1,200 plus question answers |
| Extra per-requirement work | 110 SSP implementation statements on 110 pages | SRA scope review per fact, and a risk form |
| Close blockers on a new project | 323 | 153 |
| Governance and sign-off acts to issue | 10 | 9 |
| Package review form | name, role, note, 4+1 checkboxes, 3 transition clicks | name, role, note, 2+1 checkboxes, 3 clicks |
