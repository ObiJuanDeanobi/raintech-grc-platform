# Competitor UX review and product rethink — October 2026

Status: **research, for Johnathan's decision.** Nothing here changes the approved
specification. Decisions this asks for are listed at the end.

Why this exists: on October 6, 2026, Johnathan used the Surface build and said
the tool was "really not usable" — unintuitive, and it didn't flow. Issue #127
recorded a first, light comparison (six vendor pages). On October 8 Johnathan
asked for a step back and proper research before building more.

## Bottom line

1. **The engine is sound; the experience on top of it is the problem.** Every
   serious competitor has the same core objects we have: a pinned catalog,
   objective-level answers rolling up to requirements, a score, evidence linked
   to many controls, POA&M, generated SSP. Our data model, snapshots,
   versioning and packaging are not what make the tool feel bad.
2. **What makes it feel bad is the interaction model and four rules:**
   one objective per page (~320 pages for CMMC), evidence required at the
   moment you click Met, ~10 sign-off steps to issue, and a CMMC close that only
   works at 110/110 MET.
3. **The last one is a product gap, not just friction.** Today the tool cannot
   issue a deliverable for a client that still has gaps — which is most
   readiness clients. No competitor gates output on 100% completion; the two
   that did (HHS SRA Tool, Kaseya's legacy worksheets) are criticised for it.
4. **Recommendation: reshape the workflow layer, keep the engine.** Not a
   rewrite and not six incremental patches. Re-specify how an assessment is
   worked (below), prototype it, let Johnathan try it, then rebuild the
   frontend workflow against the existing API and data model, changing the
   four rules above.

## How this was done

Five research tracks, each written up in this folder with a URL and a source
label (vendor docs, vendor marketing, user review, regulation, practitioner)
on every claim:

| Track | File |
|---|---|
| Our own app, run and measured | [current-app.md](current-app.md) |
| CMMC-specific tools and how assessors actually work | [cmmc-tools.md](cmmc-tools.md) |
| Consultant / MSP multi-client GRC tools | [msp-grc.md](msp-grc.md) |
| HIPAA risk-assessment tools | [hipaa-tools.md](hipaa-tools.md) |
| Market-leading GRC platforms and general UX guidance | [leading-grc-ux.md](leading-grc-ux.md) |

**Limits — read before relying on any of it:**

- Nobody used a competitor hands-on. Findings come from help centres, user
  guides, training syllabi and product docs where available, otherwise
  marketing. Marketing claims (for example "gap assessment in under 60
  minutes") are labelled as such.
- G2, Capterra and Reddit blocked direct reads. Review quotes come from search
  snippets and are marked that way. There are no Reddit quotes.
- Depth varies: deep for HHS SRA Tool v3.7, Totem, FutureFeed, Kaseya and
  ControlMap; medium for Clearwater, Accountable, Apptega; mostly marketing for
  Cynomi, Vanta, Drata, HIPAA One, Compliancy Group.
- Names checked and **not** found as real products: "Galaxy" (GRC), "Intraprise
  HealthSnap", "Intelligent Systems CyberAssist" (CyberAssist is a free
  resource site), Kieri Solutions (an assessment firm, no software). PreVeil's
  Compliance Accelerator is a document pack, not an assessment tool.

## Regulatory context that shapes the product (verified October 8, 2026)

- **CMMC Phase 2 is suspended.** On July 13, 2026 the DoD CIO suspended the
  Phase 2 (C3PAO-at-award) start of November 10, 2026 and "all pending and
  future CMMC milestones until further notice", and opened a 60-day CMMC
  Reform Task Force review. Phase 1 (self-assessment) remains in force.
  Sources: [Federal News Network](https://federalnewsnetwork.com/cybersecurity/2026/07/pentagon-suspends-cmmc-phase-two-requirements-launches-review-of-program/),
  [Greenberg Traurig](https://www.gtlaw.com/en/insights/2026/7/dod-suspends-cmmc-deadlines-and-seeks-to-reassess-requirements),
  [Holland & Knight](https://www.hklaw.com/en/insights/publications/2026/07/dow-suspends-cmmc-phase-ii-requirements).
  A September 3, 2026 class deviation reportedly directs contracting officers to
  remove third-party requirements; that detail rests on secondary sources.
  As of early October the Task Force report is not public. **Recheck before
  any client advice — this is moving.**
- **Consequence for the product:** the deliverables clients need right now are
  the Level 2 self-assessment, the SPRS score, the SSP and the POA&M (DFARS
  252.204-7012/-7019/-7020, NIST SP 800-171 Rev 2). C3PAO preparation is
  secondary until the Task Force outcome is known.
- **32 CFR 170.24:** a requirement is MET when all applicable objectives are
  satisfied "based on evidence", in final form. That governs a *determination*,
  not every click during fieldwork. No documented readiness tool enforces
  evidence at the moment status is set.
- **32 CFR 170.21** POA&M rules (minimum score, which requirements may be on a
  POA&M, 180-day closeout) are rules the tool should check *inline* when a gap
  is recorded, not only at close.
- **HIPAA Security Rule NPRM** (RIN 0945-AA22, 90 FR 898, January 6, 2025) is
  not final. The federal regulatory agenda lists it under Long-Term Actions
  with final action targeted for July 2027
  ([reginfo.gov](https://www.reginfo.gov/public/do/eAgendaViewRule?pubId=202510&RIN=0945-AA22)).
  The current rule governs.

## Where we stand today (measured, synthetic projects)

Full detail and file:line references in [current-app.md](current-app.md).

| | CMMC L2 | HIPAA |
|---|---|---|
| Records in the work list | 430 (110 requirements + 320 objectives) | 194 |
| Page transitions to decide everything | ≥ 320 | ~150–194 |
| Actions per Met with evidence | ~4–6 | ~4–6 + questions |
| Fieldwork actions, rough | ~1,300–2,000 | ~700–1,200 |
| Close blockers shown on a new project | 323 ungrouped lines | 153 |
| Sign-off acts to issue | 10 | 9 |
| Overview page height | 11,455 px | — |

The API is not the problem: 10–35 ms per call. The cost is clicks and steps.

Top problems, worst first:

1. **One objective per page.** Status can only be set on each objective's own
   page ([screens/06](screens/06-cmmc-objective-page.png)).
2. **Met is refused without evidence, and the reason is hidden.** The screen
   shows "Save failed · Retry" while the pill still reads Met
   ([screens/07](screens/07-cmmc-met-without-evidence.png)). That is also a
   defect in its own right.
3. **No picture of where you stand.** One meter ("x of 320 resolved"); work-list
   rows carry no status; Overview is a 300-line blocker wall
   ([screens/08](screens/08-cmmc-overview.png)).
4. **~10 sign-offs**, Profile signed off twice.
5. **No deliverable for a client with gaps.** CMMC close requires 110/110 MET.
6. **Evidence mapping is a per-record form**; no evidence view, no bulk link.
7. **Every requirement page carries panels that aren't the task** (SSP, score,
   an empty "0 questions" panel); the objective list starts at the bottom of
   the first screen ([screens/04](screens/04-cmmc-requirement-page.png)).
8. **The Profile is a blank generic form**; no questionnaire, no quote, and
   "Intake complete" can be recorded on an empty Profile
   ([screens/02](screens/02-cmmc-profile-top.png)).
9. **Dead ends** — a permanently disabled Actions button, an empty SRA tab
   ([screens/14](screens/14-hipaa-sra.png)), raw IDs typed into link fields.
10. **Missing views** the spec calls for: Dashboard and queues, Evidence,
    Risks, Policies, Reports.

**The spec contradicts itself** on the CMMC unit of work:
`docs/specification.md:104` says "requirement-centered workspace with its
assessment objectives visible together"; `docs/specification.md:493` says
"Assessments is objective-by-objective". The build followed the second. So
#128's "the build drifted" is half right; the spec needs correcting too.

## What the best tools do that we don't

Grouped by the problem each solves. Tool names point to the track files.

### Working an assessment

- **Requirement list with objectives inline, one click per objective.** Totem
  shows a family's requirements; each expands to its objectives with status set
  per objective; requirement result is derived. DIBCAC's own assessor database
  is one row per objective with examine / interview / test columns. ControlMap
  answers at objective level and rolls up to the 110 requirements live.
  *No competitor or practitioner source works one objective per page.*
- **Two views of the same assessment, one click apart** (Kaseya): a focused
  one-item view (guidance, answer, comment, attach, Next) for interviews, and a
  colour-coded list with bulk edit for cleanup.
- **Master-detail on a wide screen**: list stays visible on the left, the
  selected requirement is edited on the right, no modals, no losing your place
  (Microsoft list/details pattern, NN/g; reviewers' top complaint about the
  big platforms is losing their place).
- **Interview by family or role.** Practitioners schedule interviews by family
  and role, not by objective number; one session records answers across many
  requirements (DeepSeas SOW, practitioner write-ups in cmmc-tools.md).
- **Keyboard-driven review.** No leading vendor documents shortcuts — open
  ground for a desktop power tool (arrows to move, number keys for
  MET / NOT MET / N/A, a command palette).

### Status and evidence

- **A fast provisional pass, clearly marked.** Totem's "Trending Met" scores as
  met but shows as unverified; Kaseya's Rapid Baseline runs in under an hour and
  imports into the formal assessment. Evidence is enforced at the final
  determination, not at the click.
- **Calculated status, human override with a reason, "restore calculated"**
  (Secureframe). Fits an assessor: the tool proposes, the assessor decides, the
  audit trail records why.
- **Separate health dimensions** shown as small chips: determination, evidence
  count, evidence freshness, open POA&M (Hyperproof).
- **Evidence uploaded once, linked to many, versioned with auto-relink**, and
  reverse links shown ("used by 7 objectives") (Totem, Hyperproof). Evidence can
  be a link to where the file lives, not only an upload (FutureFeed,
  ControlMap).

### Gaps, score, outputs

- **Live SPRS score pinned on the assessment screen**, with the arithmetic one
  click away (ControlMap had to publish a help article because its breakdown
  didn't add up) and the partial-credit cases handled inline (Totem).
- **NOT MET leads straight to a POA&M draft**, prefilled, with eligibility
  checked (ControlMap "No → create risk"; Totem multi-select → "Add to POA&M").
- **Implementation text written once per requirement/objective *is* the SSP**;
  generating it is one step, with a working copy vs issued revision (Totem,
  FutureFeed, ComplyUp).
- **Outputs at any time, marked DRAFT until issued**; regenerate in one action;
  download as one bundle (Kaseya). Locking is one step: submit / issue
  (Accountable).

### Orientation

- **Home answers "what do I do today"** — a ranked queue (Urgent, Coming soon,
  Unscheduled, Waiting on client), not a menu of modules (Vanta's redesign was
  driven by exactly this).
- **Every number links to the rows behind it** ("AC: 14/22 met" opens those 22,
  filtered) (Drata).
- **One clearly defined progress metric per level** — an Apptega customer asked
  "why 3 representations of a 22% metric?"
- **A visible journey** (FutureFeed's Profile → Technology → Assess → SSP →
  Deliverables map) so you always know where you are.

### HIPAA specifically

- **Gate the risk register with "which vulnerabilities apply?"** (HHS SRA Tool):
  only ticked vulnerabilities generate threats to rate — ~200 possible rows
  become the handful that matter. Pre-tick from failing safeguard answers.
- **Rate once, apply many** (Clearwater): group assets by threat surface, copy
  ratings between groups, suggested ratings the assessor accepts or changes.
- **Answer-specific help, "I don't know" and "Flag for later"** as real answers,
  with a clickable flagged list (HHS — whose own flagged report isn't
  clickable).
- **Section close-out**: % complete, notes, and a "section reviewed" stamp with
  name and date — a natural checkpoint instead of a global sign-off chain.
- **Remediation ends at "verified", not "done"** (Accountable).

### What not to copy

- Reports locked until 100% complete (HHS SRA Tool, Kaseya legacy).
- Back/Next-only editing, and edits that un-complete a section (HHS).
- Irreversible "complete" (Kaseya legacy worksheets).
- Bulk tools that overwrite without preview or undo (Totem, Kaseya).
- Suggested or auto answers that count toward the score before confirmation.
- Two different numbers both called "risk" (HHS).
- Module sprawl as top-level navigation (Vanta, Hyperproof complaints).
- Monitoring dashboards from Vanta/Drata — wrong model for an
  interview-and-examine assessor, and neither documents SPRS or SSP for CMMC.

## Proposed shape (for discussion, not approved)

Keep: Client → Project → Profile → Assessment → Remediation → Evidence →
Outputs, the catalog, snapshots, versioning, audit, backup.

Change how it is worked:

1. **Home** — engagement queue across clients: what's overdue, what's next,
   what's waiting on the client.
2. **Project rail** — Scope → Assess → Remediate → Deliver, each with one
   progress number, always visible.
3. **Assess (CMMC)** — master-detail. Left: families → requirements, each row
   showing derived status and evidence/POA&M chips. Right: the requirement with
   all its objectives as rows, one click each for MET / NOT MET / N/A,
   examine/interview/test notes, implementation text (feeds the SSP), linked
   evidence in a side drawer. Live SPRS score in the header. Keyboard
   throughout. A focused "interview mode" walks a family or role one item at a
   time over the same data.
4. **Provisional vs verified.** A provisional "likely met — evidence pending"
   state for fieldwork. The header shows two scores: *verified* (counts only
   evidenced MET) and *projected*. Only the verified score and evidenced MET may
   appear in an issued self-assessment or SPRS figure. This keeps 32 CFR 170.24
   intact while removing the per-click gate.
5. **NOT MET → POA&M in place**, prefilled, with 32 CFR 170.21 eligibility
   flagged as you record the gap.
6. **Evidence library** — upload or link once, attach to many, reverse links,
   a coverage view ("objectives with no evidence").
7. **Deliver** — draft outputs any time, watermarked; one "Review and issue"
   step with a checklist; automatic backup on issue. **A gap-assessment
   package** (SPRS score, POA&M, SSP draft, findings) issuable for a client that
   is not at 110/110.
8. **HIPAA** — two views (question wizard / list), skip logic, flag for later,
   section close-out stamps, vulnerability checklist gating the SRA, suggested
   5×5 ratings to accept or change.
9. **Profile** — a short guided questionnaire that drives scope and the quote,
   not a blank form.

How it relates to the existing plan in #127: #128 (requirement workspace) and
#129 (dashboard) fit inside items 3 and 2; #130 and #131 are decisions D2 and
D3 below; #132 and #133 stay later. New here: provisional/verified scores, the
gap-assessment deliverable, NOT MET → POA&M inline, interview mode, the
evidence library, the Profile questionnaire, and fixing the spec's
contradiction.

## Product direction from Johnathan (October 8, 2026)

Given after reviewing the mockup. These are direction, not yet spec changes.

- **Consultant first.** The tool serves an RPO-style consultant. Deliverables
  are packaged so they would hold up in a CMMC Level 2 assessment. C3PAO
  assessor features may come later.
- **Compliance as a service is a growth priority.** Retained clients with
  ongoing work, not only one-off projects. This raises the weight of the Home
  queue, recurring reviews and year-over-year history.
- **HIPAA needs a full yearly report as a deliverable.** Note for whoever
  builds it: ADR 0011 still applies. The report can be produced yearly as a
  service, but generated text must not say the Security Rule requires an annual
  interval, because the current rule says "periodic" (45 CFR 164.308(a)(8),
  164.316(b)(2)(iii)). Contents still to be defined with Johnathan.
- **Evidence maps to many objectives or requirements, and warns before it goes
  stale.** Both are already in the spec (Evidence; Recurring Reviews and
  Notifications); the build has neither an evidence view nor stale warnings.
- **Build with automation in mind, V2.** Johnathan is moving to Halo PSA and
  wants Halo PSA or NinjaOne data to flesh out client profiles and pre-fill
  much of the gap analysis. V1 stays manual (spec non-goal), but the V1 data
  model should keep the seam open: every profile fact and answer records its
  source and whether it is suggested or confirmed, so imported data can arrive
  as unconfirmed suggestions later.
- **Service cadence for retained clients (varies by client).** One monthly
  maintenance focus plus one yearly push.
  - CMMC: monthly check-ins on policies, procedures and software inventory,
    looking for changes that need maintenance; yearly a simple gap analysis /
    mock assessment.
  - HIPAA: monthly maintenance; yearly a report deliverable to the client with
    the POA&M.
  - Design consequence: a client record spans years; monthly focus items and
    the yearly assessment are scheduled work on the Home queue; the yearly
    assessment carries last year's answers forward for revalidation.
- **Client access is V3.**
- **No other frameworks for now** (SOC 2, HITRUST, PCI DSS out of scope).
- **CUI/PHI/ePHI stay out of the tool** by operator practice; Johnathan is the
  only user. No change to `docs/local-evidence-operating-boundary.md`.

## Decisions needed from Johnathan

| # | Decision | Recommendation |
|---|---|---|
| D1 | Repair the current workflow (#127's six tickets) or reshape the workflow layer as above, keeping the engine | **Reshape.** Six patches on the objective-per-page model would still leave the gap-deliverable and orientation problems. |
| D2 | When evidence is required for MET (#130) | **At issue, not at click**, with provisional vs verified scores as in item 4. |
| D3 | Sign-off chain (#131) | **One Profile approval and one Review-and-issue step**; backup runs automatically on issue. |
| D4 | Allow issuing a CMMC package with NOT MET requirements (gap assessment: SPRS + POA&M + SSP draft) | **Yes.** This is the main readiness deliverable. |
| D5 | Priority given Phase 2 suspension | **Self-assessment path first** (SPRS, SSP, POA&M); C3PAO-prep features later. |
| D6 | Process | **Prototype the Assess workspace first** (per decision 0010), Johnathan tries it on the Surface, then amend the spec and cut tickets. |

D1–D4 change the approved specification and need Johnathan's approval before
any BUILD work.
