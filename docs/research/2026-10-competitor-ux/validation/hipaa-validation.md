# HIPAA yearly deliverable: second-pass validation against proven tools and guidance

Research date: 2026-10-08. Read-only on the repo. This builds on
`docs/research/2026-10-competitor-ux/hipaa-tools.md` (first pass; UX and workflow),
`hipaa-poam-reference.md` (Johnathan's two-sheet POA&M) and
`hipaa-report-reference.md` (Johnathan's 09/22/2025 report template). It does not
repeat their findings except where a verdict needs them.

## Source labels

- **[REG]**: statute or regulation text (eCFR, govinfo).
- **[GOV]**: US government guidance or program document (HHS, OCR, CMS, NIST).
- **[STD]**: NIST Special Publication.
- **[DOCS]**: vendor help center or training material.
- **[MKT]**: vendor marketing page or vendor blog.
- **[PRESS]**: law firm, trade press, or third-party summary.
- **[OWN]**: my own analysis of a document listed here.

## Access limits: read before relying on this

- **hhs.gov returned HTTP 403** to both WebFetch and curl, and web.archive.org was
  refused. I could not read OCR's *Guidance on Risk Analysis Requirements under
  the HIPAA Security Rule* (2010), the OCR Audit Protocol, or OCR's
  recognized-security-practices video page first-hand. The OCR guidance's
  nine-element list and its "ongoing" wording below come from vendor and law-firm
  restatements, and are labelled that way.
- **I never saw a full vendor sample report** (Clearwater, HIPAA One, Abyde,
  Medcurity, Compliancy Group). None publishes one. Report contents come from
  docs or marketing. A Clearwater IRM|Analysis manual on Scribd is user-posted,
  so I did not use it.
- **I verified first-hand:**
  - eCFR 45 CFR 164.308 and 164.316
  - Public Law 116-321 (govinfo)
  - NIST SP 800-30r1 and SP 800-66r2 (full PDFs)
  - the 2026 MIPS PI Security Risk Analysis measure spec (CMS document, re-hosted by mdinteractive)
  - reginfo.gov for the NPRM
  - Clearwater's 2026 working-lab syllabus (PDF)
  - Accountable's docs
  - the HIPAA One SRA page
- **No hands-on use of any tool. No Reddit, G2 or Capterra access** (the same limits as the first pass).

---

## 1. What a yearly HIPAA deliverable contains in proven tools

| Tool | Deliverable contents (documented) | Source |
|---|---|---|
| **HHS/ONC SRA Tool v3.7** | Five reports: **Summary** (overall risk %, Areas for Review, vulnerability count, per-section %), **Risk Report** (threat-rating chart, rating key, vulnerabilities with their threats, Areas for Review with education), **Detailed Report** (every answer, threat and vulnerability rating, Practice Info, **Assets, Vendors**, audit log of user and timestamp; PDF or Excel), **Flagged Report**, **Remediation Report** (activity, owner, due, completed, document links). Reports stay locked until the assessment is 100% complete. | [GOV] User Guide v3.7 pp.21–25 via first pass ([guide](https://healthit.gov/sra_tool_user_guide_version_3-7/)); Detailed Report description in the [2023 overview deck](https://www.healthit.gov/sites/default/files/page/2023-09/SRA_Tool_Overview_2023.pdf) |
| **Clearwater IRM\|Analysis** | Phase 3 of the workflow is "Reports, Dashboards, **Risk Register** Outputs, and **Risk Response** Planning": Reports and Enterprise Extracts, **Version History** ("importance of routine re-assessments"), dashboards, and **Findings** with Activities in OneView. The method is per asset: ePHI asset inventory, then components, then threat×vulnerability scenarios, then likelihood, impact and rating. | [DOCS] [2026 syllabus](https://go.clearwatersecurity.com/hubfs/2026%20Webinars/Risk%20Analysis%20Working%20Lab/2026_OCR_Quality-Risk-Analysis-Working-Lab_Program%20Syllabus.pdf) Sessions II–V |
| **Accountable** | Internal and external reports. Each is a point-in-time snapshot of: compliance score with breakdown, **published policies with version dates**, **training completion by employee and module**, **vendors and BAA status**, **incident log and resolutions**, latest SRA responses, and **data inventory** (where PHI is stored). Delivered as a PDF or signed link. | [DOCS] [Compliance reports](https://www.accountablehq.com/docs/compliance-reports) |
| **Accountable (sample-report article)** | Purpose and Scope · Methodology · Risk Rating Model · Findings · Deliverables. Remediation plan fields: owner, resources, due dates, milestones, dependencies, acceptance criteria, status, verification notes. | [MKT] [sample report post](https://www.accountablehq.com/post/hipaa-security-risk-assessment-example-sample-report-controls-mapping-and-remediation-plan) |
| **HIPAA One (Intraprise Health)** | Guided tier: "Customizable report of findings", "System-generated risk ratings and remediation recommendations". Validated tier: "**Assessor signs off on report of findings**" and "**Technical and executive level ROF presentations**". Also "Remediation tracking and action history", "**Year over year import of assessments**", and a policy template library. | [MKT] [HIPAA One SRA page](https://intraprisehealth.com/hipaa-one/security-risk-assessment/) |
| **Medcurity** | A downloadable SRA report that "summarizes your approach, identified risks, responses, and progress". It "documents your work rather than presenting a certificate". Risks flow into remediation with owner and deadline. | [MKT] [BA SRA page](https://medcurity.com/hipaa-compliance-solutions/business-associate-sra/) |
| **Compliancy Group (The Guard)** | Six self-audits: SRA, Privacy, Physical Site, Asset & Device, HITECH Subtitle D, Security Standards. Gap-based remediation plans with dates. The **"HIPAA Seal of Compliance"** is a private verification page, and the vendor itself says there is no government HIPAA certification. | [MKT] first pass; [Seal verification](https://compliancy-group.com/?p=10711) |
| **Abyde** | A scorecard of "questions, submitted answers, and the associated risk level". Directory listings mention PDF generation, history tracking and certificate management. Monthly "Ongoing Compliance" notifications. | [MKT] [SRA page](https://abyde.com/sra-for-covered-entities); [Software Advice listing](https://www.softwareadvice.com/ca/compliance/abyde-profile/) |

**Reference outline (not a vendor).** NIST SP 800-30r1 Appendix K gives the "essential
elements" of a risk assessment report [STD]
([SP 800-30r1](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication800-30r1.pdf), pp. K-1 to K-2):

- **Executive summary:** date, purpose, scope, and whether this is an **initial or a subsequent assessment**. A subsequent assessment states **what prompted the update** and **references the previous report**. It also gives the overall risk level and the **number of risks at each level**.
- **Body:**
  - assumptions and constraints
  - risk tolerance
  - the **risk model and analytic approach**, with "risk factors, value scales, and algorithms for combining values"
  - rationale for decisions, and uncertainties
  - system description and information flows
  - a results summary (counts by likelihood × impact)
  - the **time frame for which the assessment is valid**
  - adversarial and non-adversarial risks
- **Appendices:** references, the assessment team, and detail tables.

NIST SP 800-66r2 points HIPAA-regulated entities to this outline and recommends a
**risk register**, sharing results with leadership, and documenting risk
management "through a risk register that records assessment findings, remediation
plans, timelines, responsible parties" [STD]
([SP 800-66r2](https://nvlpubs.nist.gov/nistpubs/SpecialPublications/NIST.SP.800-66r2.pdf) §3.2 step 7, §4.4).

**OCR's nine elements** of a risk analysis, as restated by Coalfire [PRESS]
([Coalfire OCR-9](https://coalfire.com/healthcare-grc/hipaa/risk-analysis/ocr-9));
the original is unread, see Access limits:

1. Scope
2. Data collection (where ePHI is stored, received, maintained, transmitted)
3. Threats and vulnerabilities
4. Current security measures
5. Likelihood
6. Impact
7. Level of risk
8. Documentation
9. Periodic review and updates

**Common core across tools [OWN]:**

- an asset or ePHI inventory
- a per-scenario risk register
- a findings list against the rule
- a remediation plan with owner and dates
- an executive layer

The program-management tools (Accountable, Compliancy Group, Abyde) add policies,
training, BAAs and incidents. None of the vendors I could read documents a
formal attestation page. HIPAA One's assessor sign-off is the closest.

## 2. Regulatory gaps versus best-practice recommendations

- **HHS SRA Tool:** each question cites HIPAA, plus NIST CSF 2.0, HICP and HPH CPG
  references (first pass, User Guide pp.4–5). Findings are "Areas for Review" with
  education, so the tool does not split *required* from *recommended*. [GOV]
- **OCR itself separates "gap analysis" from "risk analysis".** OCR's April 2018
  newsletter, "Risk Analyses v. Gap Analyses – What is the Difference?", calls a gap
  analysis "typically a narrowed examination", while a risk analysis is "a
  comprehensive evaluation". The point is that a gap list does not satisfy
  164.308(a)(1)(ii)(A). [PRESS restating GOV]
  ([Krieg DeVault, May 2018](https://www.kriegdevault.com/insights/ocr-issues-guidance-performance-hipaa-risk-analyses-v-gap))
- **HHS's own voluntary tiers are the closest public analogue to "Control
  Enhancements".** The HPH Cybersecurity Performance Goals (Jan 2024) have 10
  **Essential** and 10 **Enhanced** goals and are voluntary. Commentators note the
  Essential set overlaps practices expected for Security Rule compliance. [PRESS]
  ([Jones Day](https://www.jonesday.com/en/insights/2024/02/hhs-releases-cybersecurity-performance-goals-for-the-health-care-sector))
- **HICP (405(d)):** 10 practices, with Technical Volume 1 for small and Volume 2 for
  medium/large organizations, first published 2019 and updated 2023. It is voluntary. [PRESS]
  ([HealthITSecurity overview](https://techtarget.com/healthtechsecurity/feature/Exploring-the-Health-Industry-Cybersecurity-Practices-HICP-Publication-How-to-Use-It))
- **Vendors:** Accountable's sample report maps controls only to Security Rule
  families and does not separate required from recommended [MKT, link above].
  Clearwater sells a separate **IRM|405(d) HICP** assessment, so its products keep
  "recognized practice" maturity apart from the HIPAA risk analysis [MKT]
  ([Clearwater IRM|405(d)](https://clearwatersecurity.com/software-solutions/irm405d-hicp/)).
  For HIPAA One, Abyde and Medcurity, I found no documented separation.
- **Verdict on the two-sheet split (HIPAA Controls vs Control Enhancements):
  VALIDATED in principle, and stronger than most tools.** Grounding exists in
  OCR's gap-vs-risk distinction, HHS's Essential/Enhanced CPG tiers and
  Clearwater's separate 405(d) product. No mass-market SRA vendor documents an
  equivalent client-facing split. **Recommendation:** give every Control
  Enhancement a *source* (HICP practice, HPH CPG goal, NIST CSF 2.0 subcategory,
  or "consultant recommendation"). That makes the sheet defensible and feeds the
  recognized-security-practices section (§7).

## 3. Risk scale: what clients see, and how internal scores map

| Source | Internal model | Client-facing levels |
|---|---|---|
| HHS SRA Tool v3.7 | L/M/H likelihood × L/M/H impact | 4 levels: Low, Moderate, High, Critical. Asymmetric: L×H = High (first pass, workbook analysis) [GOV/OWN] |
| NIST SP 800-66r2 Table 6 | 3×3 | Low/Moderate/High. **L likelihood × H impact = Low**, which differs from the HHS tool [STD] |
| NIST SP 800-66r2 Table 7 = SP 800-30r1 Table I-2 | **5×5 qualitative** (Very Low…Very High) | 5 levels via a lookup matrix, not multiplication. Semi-quantitative equivalents (Table I-3): Very High 96–100 / **10**, High 80–95 / **8**, Moderate 21–79 / **5**, Low 5–20 / **2**, Very Low 0–4 / **0** [STD] |
| Accountable sample report | 1–5 × 1–5, L×I | **High 15–25, Medium 8–14, Low 1–7**; inherent, then residual [MKT] |
| Medcurity | likelihood × impact | 3 tiers: critical / important / lower-priority [MKT] |
| Accountable remediation | — | priority critical/high/medium/low [DOCS] |
| Clearwater | likelihood × impact with a risk threshold; scale not public | Not verified |
| RainTech spec | 5×5 product | Low 1–4, Moderate 5–9, High 10–16, Critical 17–25 (`docs/specification.md` §Risk Management) |
| Johnathan's POA&M | — | H / M / L |
| Johnathan's report §5.0 | — | Critical/High/Moderate/Low/Informational = **10/8/5/2/0** |

**Findings:**

- There is **no single industry convention**. Three, four and five bands are all in
  use, and even HHS and NIST disagree on whether low likelihood with high impact is
  Low or High. What OCR asks for, per the restated nine elements, is a
  documented method and a level of risk for each threat/vulnerability pair.
- 800-30r1 Appendix K expects the report to state "value scales, and algorithms
  for combining values".
- **Johnathan's 10/8/5/2/0 values are exactly the SP 800-30r1 semi-quantitative
  representative values.** Keep them, and cite them as such.
- **Mapping problem:** the spec's 4 bands (with Critical) do not fit a 3-value
  H/M/L POA&M column.

**Recommendation:**

- Publish one mapping table in the report's methodology section.
- Either add **Critical** to the POA&M dropdown (the HHS tool and Johnathan's own
  §5.0 already use it), or collapse Critical+High to H, Moderate to M and Low to L,
  and state that collapse in the report.
- Never compute the client level any other way than the published table.

## 4. Remediation status vocabularies and tracking

| Source | Statuses | Owner | Dates | Milestones | Resources | Verification |
|---|---|---|---|---|---|---|
| OMB M-02-01 POA&M (federal origin of the format) | status of efforts | responsible office | scheduled completion | **milestones with dates, and changes to milestones** | **resources/funding** | — | [PRESS restating 38 USC 5727; [NIST glossary](https://csrc.nist.gov/glossary/term/poam); [M-02-01](https://bidenwhitehouse.archives.gov/wp-content/uploads/2017/11/2002-M-02-01-Guidance-for-Preparing-and-Submitting-Security-Plans-of-Action-and-Milestones-1.pdf)] |
| HHS SRA Tool | implicit (due / completed) | free text | due, completed | no | no | document links |
| Accountable | open → in progress → completed → **verified** (plan: draft first) | yes | target | no | no | evidence upload; "verified" undefined | [DOCS] [remediation plans](https://www.accountablehq.com/docs/remediation-plans) |
| Accountable sample article | — | single owner | due | yes | yes, plus acceptance criteria | verification notes | [MKT] |
| Medcurity | on track / overdue / upcoming | yes | deadline | — | — | "document decisions" | [MKT] |
| Clearwater | Findings → Activities (Activities Manager); risk response: accept / transfer / avoid / mitigate | — | — | — | — | — | [DOCS]/[PRESS] |
| Johnathan's POA&M | Pending / Open / Closed / On-Hold / Cancelled | POC | finding, scheduled, actual | yes | yes | Link to Evidence |

**Verdict: VALIDATED.** Johnathan's columns are the federal POA&M field set plus
evidence, which is richer than every HIPAA SRA vendor I could document.

**Gaps against the proven tools:**

1. **There is no "verified/validated" state** between Closed and done. The spec's
   Validated / Validation failed should map to a "Closed (validated)" display, or
   Closed should require validation.
2. **There is no "Risk Accepted" status.** Clearwater and NIST include risk
   acceptance, and the spec already keeps accepted risks with an approver. Today
   it can only show as On-Hold or Cancelled, which misrepresents it.
3. **"Changes to milestones" history** (an OMB element) falls out naturally from
   the tool's audit trail and is worth showing as Status Summary history.

## 5. Year-over-year updates

- **HHS SRA Tool:** Save As last year's file, which keeps the old content version (first pass). [GOV]
- **HIPAA One:** "Year over year import of assessments" [MKT, link above]. The
  first pass also found "auto-fill information that hasn't changed".
- **Clearwater:** "Version History" taught as "importance of routine re-assessments" [DOCS, syllabus].
- **Accountable:** submitted assessments are locked point-in-time snapshots.
  Reports snapshot state, and no comparison view is documented [DOCS].
- **Abyde:** monthly maintenance nudges and "history tracking" [MKT].
- **NIST SP 800-30r1 App. K:** a subsequent assessment states what prompted the update and references the prior report [STD].

**No vendor documents a client-facing "changes since last year" section.** All
the evidence is carry-forward plus history. **Verdict on the planned carry-forward
with revalidation: VALIDATED.** **A year-over-year comparison section in the
report: NOVEL**, but anchored in 800-30r1's "subsequent assessment" element.

## 6. Language: "annual" versus "periodic"

**Regulation [REG]** ([eCFR 164.308](https://www.ecfr.gov/current/title-45/section-164.308), [164.316](https://www.ecfr.gov/current/title-45/section-164.316)):

- 164.308(a)(8): "Perform a **periodic** technical and nontechnical evaluation…"
- 164.316(b)(2)(iii): "Review documentation **periodically**, and update as needed…"
- 164.308(a)(1)(ii)(A) risk analysis sets **no interval**.
- 164.316(b)(2)(i): retain documentation **6 years**.

**OCR guidance:** the restated element 9 is "Periodic Review and Updates to the
Risk Assessment", with "The risk analysis process should be ongoing" and
"continuous risk analysis" [PRESS restating GOV, Coalfire link above].
Secondary sources attribute to HHS that "some covered entities may perform
these processes annually or as needed (e.g., bi-annual or every 3 years)". **I
could not verify that sentence against hhs.gov**, so do not quote it in generated
text until it is checked.

**NIST:**

- SP 800-66r2 says risk assessment is "ongoing" and "updated on a periodic basis"
  (§3.3). It gives "annually" only as an *example* in questions on training and
  contingency testing.
- Its footnote 10: "the Medicare Promoting Interoperability Program, which
  **requires an annual risk assessment**" [STD].

**CMS (a real annual requirement, but not HIPAA's) [GOV]:** the 2026 MIPS PI
measure PI_PPHI_1 requires attesting "I conducted or reviewed a security risk
analysis… **during the year in which the performance period occurs**", plus a
new second attestation on risk management activities under 164.308(a)(1)(ii)(B)
([2026 measure spec, CMS document re-hosted](https://mdinteractive.com/sites/default/files/uploaded/file/mips_pi_2026/2026-MIPS-Promoting-Interoperability-Security-Risk-Analysis-Measure.pdf)).
For a MIPS-participating client, generated text may say this, but only with the
CMS citation and only when a profile fact says the client participates.

**Competitor wording:**

- **HIPAA One:** "conducting a HIPAA risk assessment is **required annually under
  the HIPAA regulations**". This is incorrect under the current rule [MKT, page above].
- **Abyde:** calls the SRA "a foundational requirement", with no interval claimed [MKT].
- **Accountable:** "does not prescribe a fixed calendar schedule", yet recommends
  "at least annually" as a best practice [MKT]
  ([Accountable frequency post](https://www.accountablehq.com/post/hipaa-security-risk-assessments-frequency-requirements-real-world-examples-and-ocr-guidance)).
  This is the model to copy: required = periodic, practice = yearly.
- **Johnathan's own 2025 template** says "The HIPAA law requires that
  organizations annually assess". This is the same error as HIPAA One's, and ADR
  0011 bars it.

**Approved-style wording (proposal):** "The Security Rule requires periodic
evaluation and review (45 CFR 164.308(a)(8), 164.316(b)(2)(iii)). [Client]
engages RainTech for a yearly assessment cycle, with updates in response to
environmental or operational changes."

**NPRM status [GOV, 2026-dated]:** RIN 0945-AA22 (NPRM 01/06/2025, 90 FR 898) is
listed under **Long-Term Actions** with Final Action **07/00/2027** in the agenda
labelled "2026" ([reginfo.gov](https://www.reginfo.gov/public/do/eAgendaViewRule?pubId=202510&RIN=0945-AA22),
read 2026-10-08). A July 2, 2026 vendor post says "OCR has not yet issued a
final rule" [MKT] ([ABT](https://www.myabt.com/blog/hipaa-security-rule-2026-final-changes)).
That post cites 90 FR 800, which conflicts with reginfo's 898; I use reginfo.
The current rule governs.

**OCR enforcement context [PRESS/MKT, 2025–2026]:** OCR's Risk Analysis Initiative
(launched Oct 2024) keeps citing 164.308(a)(1)(ii)(A). 2026 summaries say focus
is widening to risk *management*
([Nixon Peabody 2025](https://nixonpeabody.com/insights/articles/2025/04/09/ocr-publishes-fifth-enforcement-action-under-its-risk-analysis-initiative);
[Medcurity Sept 2026 digest](https://medcurity.com/ocr-breach-enforcement-digest-september-8-2026/)).
Counts differ by source, so they are not verified against OCR.

## 7. What proven tools include that our plan or Johnathan's template lacks

| Item | Who has it | Our state | Verdict |
|---|---|---|---|
| **ePHI asset inventory linked to risk scenarios** | Clearwater (core), HHS (inventory, not linked), Accountable (data inventory) | Spec requires ePHI scope, flows, threat-vulnerability pairs, and issue blocked until every ePHI system, location and vendor is reviewed. **Johnathan's report has no per-asset register** | Plan VALIDATED; template CONTRADICTED by OCR elements 2–7 |
| **Vendor / BA inventory with BAA status** | HHS (Vendors), Accountable, Abyde (BAA management) | Spec says "HIPAA BAA tracking, if added, remains framework-specific" | PARTLY; add it (164.308(b), 164.314(a)) |
| **Policy library with version and review dates** | Accountable, HIPAA One (templates), Compliancy Group | Spec has a policy/review register report | VALIDATED |
| **Training completion** | Accountable, Abyde | Not in the plan as a record type | Gap; at minimum a "training evidence reviewed" row per 164.308(a)(5) |
| **Incident log** | Accountable, HIPAA Ready | Not planned | Gap; a summary table of incidents in the period, without PHI (164.308(a)(6)) |
| **Technical vulnerability findings (scans)** | NIST SP 800-66r2 §3.4 says a questionnaire "cannot identify technical vulnerabilities" and should be paired with scanning [STD] | Johnathan's sheet 3; not in the spec | VALIDATED as a need; new record type |
| **Recognized security practices (PL 116-321)** | Clearwater IRM\|405(d); HHS tool cites HICP and NIST CSF | Not planned | Gap; see below |
| **Assessor sign-off / attestation page** | HIPAA One Validated tier ("Assessor signs off on report of findings") | Spec: named reviewer and issuance | VALIDATED; render it as a signed page in the report |
| **Executive presentation** | HIPAA One ("Technical and executive level ROF presentations"), Clearwater consulting | Spec: executive highlights | VALIDATED |
| **OCR Audit Protocol mapping** | None documented in SRA tools. The protocol (2012, 77 Security Rule performance criteria per secondary sources) exists, but I could not read the hhs.gov copy | Not planned | Optional; do not build it until it is verified |
| **Year-over-year import** | HIPAA One, HHS (Save As) | Planned carry-forward | VALIDATED |

**Recognized security practices: the statute, verified [REG].** Public Law 116-321,
approved **January 5, 2021**, adds HITECH §13412 (42 USC 17941)
([govinfo](https://www.govinfo.gov/content/pkg/PLAW-116publ321/html/PLAW-116publ321.htm)):

- **What HHS must consider:** whether the entity "adequately demonstrated that it had, for not less than the previous **12 months**, recognized security practices in place". This applies when setting fines, ending audits early, or agreeing remedies.
- **What counts:** NIST Act §2(c)(15) material (which covers the **NIST CSF**), **§405(d) approaches (HICP)**, and other statutory programs.
- **No penalty for not adopting them:** non-adoption cannot increase penalties.
- **Date error in NIST:** SP 800-66r2 footnote 9 gives the signing date as "January 5, 2020", which conflicts with govinfo. Use 2021.
- **Evidence OCR expects (secondary):** the 2022 OCR video asks for proof of actual, enterprise-wide implementation over 12 months. A mapping alone is "insufficient". Examples are policies, project plans, training, screenshots and contracts [PRESS]
  ([Locke Lord Dec 2022](https://www.lockelord.com/newsandevents/publications/2022/12/office-of-civil-rights-2021-hitech);
  [AHA Nov 2022](https://www.aha.org/news/headline/2022-11-01-hhs-releases-video-documenting-recognized-hipaa-security-practices)).
- **Consequence for the report:** an optional "Recognized security practices"
  section listing the practices in place and their evidence dates. It must not
  claim that safe-harbor treatment applies; the statute only requires that HHS
  "consider" them.

## 8. Johnathan's yearly report against proven tools and guidance

### What to keep

- **Background and Introduction**, with applicable standards. 800-30r1 App. K expects references.
- **Scope**: system boundary, data types, documentation reviewed, physical sites. This matches 800-30r1 App. K and OCR elements 1–2.
- **Methodology on 800-30r1 steps.** NIST SP 800-66r2 builds its HIPAA guidance on the same steps.
- **Four finding sources** (HIPAA controls / enhancements / technical / site), which are richer than any vendor I could document.
- **Appendix B**, a per-citation table with Remarks giving where the evidence is or what is missing. It mirrors the HHS Detailed Report.
- **The 20-column POA&M.** It is the federal field set.
- **Impact values 10/8/5/2/0**, which match 800-30r1 Table H-3 and I-3.

### What proven tools and guidance include that his lacks

1. **A threat/vulnerability risk register per asset or asset group**, with
   likelihood, impact and level for each pair. OCR elements 3–7 and 800-66r2 §3.2
   step 7 ("document all threat/vulnerability pairs… the likelihood and impact
   calculations, and the overall risk… for the threat/vulnerability pair") call
   for it. This is the largest substantive gap. Without it the report reads as a
   gap analysis, which OCR distinguishes from a risk analysis.
2. **An ePHI asset and data-flow inventory** as an appendix (OCR element 2; Clearwater phase 1).
3. **Counts of risks by level and a likelihood × impact heat map** (800-30r1 App. K).
4. **Initial versus subsequent assessment, what changed since the prior report, and a reference to that report** (800-30r1 App. K). Present nowhere in his template.
5. **A risk-response decision per risk** (mitigate / accept / transfer / avoid), with an approver for acceptance (Clearwater; 800-66r2 §4; the spec already has this).
6. **A BA/vendor inventory with BAA status; a training summary; an incident summary** (Accountable, HHS Vendors).
7. **The valid time frame and the next review trigger** (800-30r1 App. K), worded as periodic or change-driven.
8. **Recognized security practices**, optional (PL 116-321).
9. **A sign-off page**: assessor, client acknowledgement, date (HIPAA One Validated tier).

### What his template does that proven sources treat differently

- **Risk method (Appendix D): CONTRADICTED by 800-30r1 and by its own §2.5.**
  - **NIST's model:** 800-30r1 says "risk is a function of the likelihood of a
    threat event's occurrence and potential adverse impact" (p.12), combined
    through a lookup matrix (Table I-2).
  - **Where control state belongs:** compliance and control gaps are
    *vulnerabilities* or *predisposing conditions*. They raise **likelihood**
    (800-30r1 §2.3.1, p.10). They are not added as separate terms to risk.
  - **Double counting:** summing Criticality + Likelihood + Impact + Compliance +
    Gap counts control weakness twice, once in likelihood and again as
    "Compliance"/"Gap". It also produces one organisation-wide number instead of a
    level for each threat/vulnerability pair, which is what OCR element 7 expects.
  - **The likelihood scale** (crime, terrorism and natural disaster near a
    facility) is a *predisposing-condition* scale for physical threats only. 800-30r1
    likelihood is per threat event, whether adversarial, accidental or
    environmental (Tables G-2 to G-5), so phishing, lost laptops and ransomware get
    no likelihood under his scale.
  - **The impact scale** starts at $1M. 800-30r1 Table H-3 defines impact
    qualitatively, as limited / serious / severe adverse effect on operations,
    assets and **individuals**. Every incident at a small practice would fall
    below $1M, so the scale cannot discriminate.
  - **§2.5 versus Appendix D:** §2.5 says "average of likelihood and impact" while
    Appendix D sums five factors. 800-30r1 App. K requires the published
    "algorithms for combining values" to be the ones actually used.
  - **Fix:** generate Appendix D from the tool's actual 5×5 per-pair method, show
    the NIST-style matrix, and report the organisation's overall level as the
    distribution and maximum of its pair-level risks. An organisational
    "maturity" label can stay, but **separate from "risk"**. The HHS SRA Tool's
    two numbers both called "risk" are a known confusion (first pass).
- **Compliance % by domain in the Executive Summary.** ADR 0011 bars presenting "a
  generic readiness or compliance percentage as an assessment conclusion".
  Accountable labels its score "a signal — not a grade". Show counts
  (Implemented / Not Implemented / N/A). If a % stays, compute it from the same
  rows and label it as coverage, not compliance. His 2025 percentages don't
  reconcile (`hipaa-report-reference.md` item 2).
- **Privacy Rule and Breach Notification Rule rows in the same compliance table.**
  Proven SRA tools scope the risk analysis to the Security Rule. Compliancy Group
  runs Privacy and Subtitle D (breach) as *separate* self-audits. Keep them, but
  label them "Privacy and Breach Notification review", outside the risk analysis.
- **Appendix B at standard level.** The spec records determinations at
  implementation-specification level, as the HHS tool and the OCR protocol do.
  Generate Appendix B at that level and roll up to standards only for summaries.
- **"Annual" claim.** Remove it (§6).

## 9. Verdicts on the planned HIPAA approach

| Planned element | Verdict | Basis |
|---|---|---|
| Two-sheet POA&M (cited gaps vs control enhancements) | **VALIDATED** (stronger than most vendors) | OCR gap-vs-risk distinction; HPH CPG Essential/Enhanced; Clearwater's separate 405(d) product |
| POA&M columns (POC, milestones, resources, dates, evidence) | **VALIDATED** | OMB M-02-01 fields; richer than HHS, Accountable and Medcurity |
| Status list Pending/Open/Closed/On-Hold/Cancelled | **PARTLY** | Missing **Risk Accepted** and **Validated/Verified** (Accountable, Clearwater, the spec's own validation) |
| Internal 5×5 → client H/M/L | **PARTLY** | 5×5 matches 800-30r1/800-66r2 Table 7. The spec has 4 bands with Critical while the POA&M has 3, so a published mapping is needed. NIST combines with a matrix, not multiplication; either is defensible if published |
| SRA with ePHI scope, threat-vulnerability pairs, issue gate on scope completeness | **VALIDATED** | OCR elements 1–7; Clearwater; 800-66r2 |
| Report narrative (Johnathan's template as-is) | **PARTLY / CONTRADICTED on risk method** | Missing the per-pair risk register; Appendix D method conflicts with 800-30r1 |
| Yearly cycle with carry-forward and revalidation | **VALIDATED** | HIPAA One YoY import; HHS Save As; Clearwater version history |
| Year-over-year comparison section | **NOVEL** (well-grounded) | No vendor documents it; 800-30r1 App. K "subsequent assessment" |
| Monthly maintenance cadence | **VALIDATED** | Abyde monthly Ongoing Compliance; Compliancy Group coaching |
| No "annual requirement" wording (ADR 0011) | **VALIDATED** (competitors get it wrong) | 164.308(a)(8), 164.316(b)(2)(iii); HIPAA One and Johnathan's 2025 template both misstate it; MIPS is the CMS exception |
| BA inventory / training / incidents | **Gap** (partly planned) | Accountable report contents; HHS Vendors |
| Recognized security practices section | **Gap, optional** | PL 116-321 |

## 10. Proposed table of contents for the tool's HIPAA yearly report

This starts from Johnathan's structure. *[new]* marks additions grounded above;
*[changed]* marks corrections.

0. **Cover and document control:** client, period covered, report version, issue
   date, framework catalog version, prior report reference *[new: 800-30r1 App. K]*,
   confidentiality notice.
1. **Sign-off** *[new]*: assessor (named reviewer from issuance), client acknowledgement, date. (HIPAA One Validated tier; spec issuance.)
2. **Executive Summary**
   - 2.1 Purpose, scope, and whether this is an initial or subsequent assessment
   - 2.2 Overall risk: count of risks by level, a 5×5 heat map, top risks *[changed from summed score; 800-30r1 App. K]*
   - 2.3 Safeguard status by domain: Implemented / Partially / Not Implemented / N/A **counts** *[changed: counts, not compliance %; ADR 0011]*
   - 2.4 Changes since the prior assessment: closed, new and carried-forward items, and risk-level movement *[new]*
   - 2.5 Priority remediation (top items from the POA&M)
3. **Background**: HIPAA rules in plain language (keep).
4. **Introduction and Scope**: applicable laws and standards; system boundary;
   ePHI data types; physical sites; documentation reviewed; assumptions and
   constraints *[new]*; the period for which the assessment is valid and the
   review triggers *[new]*, worded as periodic or change-driven.
5. **Methodology**: NIST SP 800-30r1 / 800-66r2 steps; the **risk model as
   actually used**: 5×5 scales with definitions, the combining matrix, the band
   table, the mapping to client H/M/L (or Critical) *[changed]*, and the source
   of each finding type (interview, document review, site visit, scan).
6. **ePHI Asset and Data-Flow Inventory**: systems, locations, flows (no PHI content) *[new: OCR element 2]*.
7. **Risk Analysis Results (Risk Register)**: each threat/vulnerability pair by
   asset or asset group, with current controls, likelihood, impact, inherent
   level, risk response, residual level, and acceptance approver *[new: OCR
   elements 3–7; spec]*.
8. **Security Rule Findings**: summary of the HIPAA Controls sheet, linked to risks.
9. **Control Enhancements (recommendations, not regulatory requirements)**: each
   with a source (HICP practice / HPH CPG / NIST CSF / consultant), stated as
   voluntary *[changed: source attribution]*.
10. **Technical Vulnerability Summary** (from scans) and **Site Review Findings** (keep, from Johnathan's sheets 3–4).
11. **Program Elements Reviewed** *[new]*:
    - 11.1 Policies and procedures: version, last review date
    - 11.2 Workforce training: evidence reviewed and completion status
    - 11.3 Business associates: inventory and BAA status
    - 11.4 Security incidents in the period: summary only, no PHI
    - 11.5 Contingency plan testing: last test date
12. **Privacy Rule and Breach Notification Review** (outside the Security Rule
    risk analysis) *[changed: separated]*.
13. **Recognized Security Practices** (optional) *[new: PL 116-321]*: practices in
    place, framework (HICP / NIST CSF), evidence and dates. No safe-harbor claim.
14. **Remediation Plan (POA&M) summary** and status definitions, including Risk
    Accepted and Validated *[changed]*.
15. **Next Steps and Review Cycle**: "periodic evaluation… and in response to
    environmental or operational changes". The yearly service cycle is described
    as RainTech's engagement, not a legal interval. Add the MIPS line only when
    the profile says the client participates *[changed: ADR 0011]*.

**Appendices**

- A: Terminology
- B: Security Rule requirements table at implementation-specification level (citation, name from the pinned catalog, status, evidence location or gap) *[changed level]*
- C: POA&M workbook (separate XLSX: HIPAA Controls, Control Enhancements, Technical, Site)
- D: Risk method detail and scales, generated from the engine *[replaces the summed formula]*
- E: Evidence index
- F: Assessment team and contacts; references (800-30r1 App. K)
- G: Prior-year comparison detail *[new]*

## 11. Not verified

- Full text of OCR's 2010 risk-analysis guidance, including the "annually or as
  needed (e.g., bi-annual or every 3 years)" sentence attributed to HHS; hhs.gov
  returned 403.
- OCR Audit Protocol current version and contents (a 2018 update is reported but not confirmed).
- Any vendor's actual sample report or table of contents.
- Clearwater's likelihood and impact scales and risk threshold.
- Abyde's and Compliancy Group's risk scales and report contents.
- Whether the 2023 HICP edition changed the volume structure.
- OCR Risk Analysis Initiative counts (secondary sources disagree).
