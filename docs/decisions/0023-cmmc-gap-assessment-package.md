# ADR 0023: The CMMC gap-assessment package is the default CMMC finalize

## Status

Accepted as built, within the engineering delegation of October 8, 2026 (`AGENTS.md`,
"Current delegation"). Implements ADR 0019 decision 5 and acceptance criterion AC-025
of the *[Amendment 2026-10]* specification. The specification is not edited here.
Ticket #146. Three points are flagged for Johnathan's review at the end.

## Context

Until now a CMMC project could only issue when every one of the 110 requirements was
Met (the internal readiness close, AC-018). A client with gaps saw blockers that could
never clear, and so got no deliverable at all (ADR 0019, Context).

The specification now defines two CMMC packages besides the internal close:

> **Gap assessment package**, issuable with NOT MET requirements: gap report grouped
> by family with examine/interview/test notes, verified SPRS worksheet, POA&M with
> 32 CFR 170.21 eligibility, SSP draft, and evidence index.

> AC-025: A CMMC gap-assessment package can be issued with NOT MET requirements in one
> review-and-issue act, showing only the verified score.

and says of evidence (AC-004):

> Met recorded without evidence shows as evidence pending, is excluded from the
> verified score, and blocks the self-assessment package but not the gap-assessment
> package.

The score rule (Frameworks and Assessments) is that "Only the verified score may appear
in an issued self-assessment, SPRS worksheet, or client deliverable." An inflated
self-assessment is a False Claims Act exposure (MORSECORP settled for $4.6M in March
2025 after posting 104 against a third-party figure of -142;
`docs/research/2026-10-competitor-ux/validation/cmmc-validation.md`), so the design
errs toward understating.

## Decision

### 1. Two packages, one act, chosen at finalize

`POST .../assessments/{a}/issue`, `GET .../issue-checklist` and `GET .../draft` take a
package choice (`package` in the body, or as a query parameter):

- `gap_assessment`, the **default** for CMMC: this ADR.
- `readiness_close`: **Final self-assessment (all requirements Met)**, the existing
  internal readiness close. Every gate is unchanged (AC-018) and so is its output. The
  menu label is as approved; the identifier is `readiness_close` because the
  specification reserves "Self-assessment package" for a different, unbuilt package
  (see Flagged, item 2). No other value is accepted; nothing is stored under any
  earlier name.

HIPAA has no choice. Asking for one is refused (422 on issue, draft and checklist alike,
as for any invalid value; 409 is kept for business gates), not ignored. The draft follows the same choice, so what a person downloads
is what the act would issue, watermarked DRAFT as in ADR 0021.

The gap package reuses the engine as it is: one generation from current data, one
sign-off event, the automatic pre-issuance full backup, the frozen snapshot, and the
supersession and reopening rules of ADRs 0014, 0018 and 0021. Nothing in the issue
machinery was relaxed for it. What differs is which conditions are gates (section 2)
and what the package contains (section 4).

### 2. Hard gates and warnings

The test applied to each condition: does issuing with it present something false, or
lose something that cannot be recovered? If so it blocks. If the package can state the
condition truthfully, it is reported and does not block.

**Hard gates** (409 with plain-English `groups`; nothing is generated, signed off,
backed up or issued):

| Gate | Why it stays hard | Source |
| --- | --- | --- |
| An active assessment exists | There is nothing to report on. | |
| Profile approved and complete, with no recorded unknown | "profile-complete, gap-analysis completion, and scope-dependent issuance require no unresolved unknown." The Profile defines the scope every figure rests on; the gate is as built and the ticket keeps it. | AC-016, ADR 0021 decision 5 |
| Every objective decided (none blank, none Pending) | The report states results for decided objectives. A blank objective is undecided work and a Pending one is an outstanding evidence request (specification: Pending "blocks close"). Issuing over either would freeze an unfinished assessment as the version of record. Not Met is a decision and is allowed (AC-025). Group label: "Objectives not yet decided". Lead decision. | AC-025, Findings and POA&M |
| Reopened records revalidated | Carried-over work must be rechecked before a successor is issued. | ADR 0018 decision 1 |
| Evidence files pass their integrity check | The package carries an evidence index. A file that fails its hash or is missing would be indexed as something it is not. | AC-018 (hashes), ADR 0015 |
| Source and template binding (no drift) | The exact reviewed package, source snapshot and template bytes are what is issued. If the data changed since generation, the issue is refused. | ADR 0014, ADR 0021 decision 3 |
| Successful pre-issuance full backup | "A failed backup still blocks issue." A failed backup returns 409, records the failure, issues nothing, and the previous issue stays Current. | Reports and Governance; Local Operation and Recovery |
| Package type matches the issue it would replace | A different kind of package from unchanged data is not a presentation-only correction; it needs reopening (section 5). | ADR 0021 decision 6 |

**Warnings** (listed under "Worth checking" in the dialog, stated in the report, never
block, nothing to tick):

| Condition | What happens instead of blocking |
| --- | --- |
| Requirements Not Met | They are the report's subject: listed by family with each failed objective, notes, interview or observation, the POA&M position and 32 CFR 170.21 eligibility. |
| Met without current evidence (evidence pending) | Counted as not met in the verified score; listed under "Met, evidence still needed" with the objectives that lack support. Not a gap in the sense of a failed objective, and not a block. AC-004. |
| NOT MET requirement with no POA&M item | Listed in the POA&M file as "No POA&M item yet". Creating the POA&M is a deliberate act (specification, Findings), never automatic. |
| Open or draft POA&M items | A "POA&M items still open" warning with the draft count; the POA&M file lists every item with its status, drafts included. |
| 32 CFR 170.21 conditional-status checks failing | A "conditional status checks failing" warning; each check is reported with its reason in the gap report, never blocking (the ticket and the specification: "Show the 32 CFR 170.21 Conditional-status checks alongside the score"). |
| System Security Plan not approved | The SSP goes in as a draft: the file is named `System_Security_Plan_DRAFT.docx` and its first page says NOT APPROVED. The package is specified to carry an "SSP draft". If an approved SSP exists it is used and named without DRAFT. |
| Evidence past its review date or due soon | The existing warning, unchanged. A Met that relies on past-due evidence already stops counting as verified. |

**Decision on undecided objectives: they block (lead-approved, replacing the first
build, which only warned).** The first build warned on blank and Pending objectives and
scored them as not met. That is never an overstatement, but it let an unfinished
assessment be frozen and handed over as the version of record, and Pending (an evidence
request) is work the specification says blocks. A Not Met objective is what the package
is for and stays allowed. A **draft** of an incomplete assessment is still available at
any time and opens with "This assessment is not complete" and "N of 320 objectives not
yet assessed", each counted as not met, so the consultant can show work in progress
without issuing it.

### 3. What the report must say

`api/renderers/cmmc.py`, `_gap_report`. In order: the scope statement ("This is a gap
assessment, not a C3PAO assessment ... It does not certify the organization, and it
does not say the organization is ready for a certification assessment"); the
incompleteness section (drafts only: an issued report has none, because every
objective is decided); the verified SPRS score with
its literal arithmetic (110 minus each deducted weight) and the method (DoD Assessment
Methodology v1.2.1, point values of 32 CFR 170.24(c)(2)(i)(B)); the three 32 CFR
170.21(a)(2) checks, each marked PASS or FAIL with its paragraph and detail, and the
requirements that make it fail; results by family; NOT MET requirements by family; evidence
pending; not yet assessed. No wording says certified, compliant, audit-ready or
certification-ready (ADR 0011). Partial credit for 3.5.3 and 3.13.11 is taken only when
the implementation level was recorded; otherwise the full weight is deducted, and the
report says so. When CA.L2-3.12.4 is not Met the report says the methodology does not
allow an assessment to be completed without an up-to-date SSP (Methodology 5(g)(i):
"The absence of a system security plan would result in a finding that 'an assessment
could not be completed ...'") so the figure is not a complete assessment score.

### 4. Contents and the verified-only rule

Five components: the gap report (`CMMC_L2_Gap_Assessment_Report.docx`), the verified
SPRS worksheet (`SPRS_Worksheet_Verified.csv`, one row per requirement with result,
points deducted and POA&M eligibility, then the score and its arithmetic), the POA&M
(`CMMC_POAM.csv`: every item with its status, drafts included, and the eligibility and
the reason per requirement), the SSP, and the evidence index (reused unchanged).

The worksheet has an "Assessment complete" row and a "Scoring note" column. For a
requirement not scored Not Met, "May be on a POA&M" reads "n/a until assessed", because
32 CFR 170.21(a)(2) concerns requirements scored NOT MET. The note column explains why
IA.L2-3.5.3 and SC.L2-3.13.11 deduct 3 rather than 5 (the recorded implementation
level) or that the full 5 is deducted when none is recorded.

The SSP must agree with the report. A requirement recorded Met that is evidence pending
reads "Evidence pending (recorded as Met, not yet verified)" in the gap package's SSP,
not "Implemented". Only the gap package's copy changes; the approved SSP and the
readiness close keep the template mapping (Met reads Implemented).

Only the verified score reaches the workspace's output. The projected score is removed
from the gap package's source snapshot as well, so it cannot appear in any rendering
now or after a template change. A test asserts the projected figure's arithmetic is in
no artifact and no stored source, with a state where projected and verified differ.

### 5. Immutability and supersession across package types

Nothing about issued records changes. The package type is part of the stored source
snapshot (`package_type`, written only for the gap package), so the package's drift
check, expected components and correction path all rebuild it as the kind it was.
Source snapshots without it are the self-assessment, which keeps every package issued
before this ticket checking exactly as it did.

- Same assessment, same kind: a second issue from unchanged data is a presentation-only
  correction and supersedes the first (ADR 0021 decision 6). `issue-now` keeps the
  kind of the issue it corrects.
- Same assessment, different kind: refused with "This assessment was issued as a gap
  assessment. To issue it as a final self-assessment instead, reopen the assessment
  and issue from the reopened one." The two packages are generated from different
  snapshots, and "presentation only" cannot cover that.
- A reopened successor assessment is issued by the same act in either kind and
  supersedes the prior issue whatever its kind (ADR 0018 decision 4). The superseded
  package and its files stay as issued.

### 6. Overview

**Superseded by ADR 0022**, which removes "left before issue" from the Overview. This
ticket makes no Overview change. `/close-readiness` keeps its meaning, the internal
readiness close.

### 7. Snapshot compatibility

The readiness stored in a source snapshot is part of what the drift check hashes. For the
readiness close and HIPAA it is stored exactly as before #146 (no `package_type`, no
`deferred`), so every package issued earlier hashes identically and can still be
reissued or corrected; tests replay that shape. For the gap package only codes and counts
are stored (`blocking`, `deferred`), never the wording of a blocker detail, so rewording
a message cannot read as drift.

## Consequences

- No migration. `package_type` lives in `source_snapshots.source_json` and the package
  manifest's component kinds; no table or trigger changed.
- Existing CMMC draft tests that expect the readiness-close files now ask for
  `readiness_close` explicitly (`api/tests/test_issue_145_drafts.py`); each assertion
  keeps its intent.
- A finalize on a half-done assessment produces a legitimate, very low verified score.
  That is the intended honesty, and it will look alarming to a client who has not read
  the report's first page. The report's opening says what it is.
- The finalize dialog shows the choice with one plain sentence each (`PackageChoice`).

## Flagged for Johnathan

1. **Undecided objectives block; Not Met does not** (section 2, lead-approved). Blank
   and Pending (evidence requests) both stop the finalize; only drafts can show an
   incomplete assessment. The earlier warn-only choice is one line to restore
   (`_gap_defers` in `api/close.py`).
2. **The specification's separate "Self-assessment package"** ("issuable when no Met
   result is evidence pending": requirement results for SPRS entry, verified SPRS
   worksheet, SSP, POA&M) is **not built here**. The ticket makes the second option
   the existing 110-of-110 internal readiness close, so that is what
   "Final self-assessment (all requirements Met)" issues, with its original four
   files and gates. Because the specification reserves "Self-assessment package" for
   that other package, the identifier is `readiness_close`, not `self_assessment`. If the specification's intermediate package is wanted (a
   self-assessment that may carry POA&M-eligible NOT MET requirements), it is a third
   option and needs the 32 CFR 170.16 and 170.22 affirmation work first.
3. **Client-facing wording.** The scope statement in section 3 is a compliance claim
   about what the document is. It follows ADR 0011 and the ticket's required phrase,
   but it is Johnathan's to approve before any report goes to a client.
