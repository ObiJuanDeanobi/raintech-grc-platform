# Issue #105 — CMMC official scoring, requirement findings, and POA&M

October 6, 2026. Synthetic data only.

## Scoring source (the ticket's open question)

Johnathan delegated the decision. The source is the regulation:

- **32 CFR 170.24 (CMMC Scoring Methodology)**, Table 7, for point values.
- **32 CFR 170.21(a)(2)** for conditional POA&M rules.

Both are pinned from the eCFR versioner API as of 2026-10-01; the text was last
amended 2024-12-16. The files are in `catalog/sources/` and their SHA-256 hashes
are recorded. `catalog/cmmc_scoring.py` reads the published requirement lists
from that text, so nothing is typed in by hand. The result is
`catalog/versions/cmmc-l2-scoring-32cfr170-2024-12-16.json`.

What the regulation gives:

| Rule | Paragraph | Count |
|---|---|---|
| 5 points | 170.24(c)(2)(i)(B)(1) | 42 (23 basic, 19 derived) |
| 3 points | 170.24(c)(2)(i)(B)(2) | 14 (7 basic, 7 derived) |
| 3 or 5 points (partial credit) | 170.24(c)(2)(i)(B)(4) | 2: IA.L2-3.5.3, SC.L2-3.13.11 |
| No point value; missing SSP blocks completion | 170.24(c)(2)(i)(B)(5) | 1: CA.L2-3.12.4 |
| 1 point (all remaining) | 170.24(c)(2)(i)(B)(3) | 51 |

The maximum score is 110. The computed minimum is −203, which matches the
published SPRS floor.

Reported, not silently fixed: the regulation prints `IA-L2-3.5.1`,
`IA-L2-3.5.2`, and `AC.L2- 3.1.19`. These are normalized to catalog IDs and
listed in `discrepancies`.

**For Johnathan:** 170.24(b)(3) allows N/A at both requirement and objective
level, and treats N/A as Met. The approved specification's CMMC status set
(Blank, Met, Not Met, Pending) has no N/A. I kept to the specification. Adding
N/A for CMMC needs your approval of a specification change.

## Behaviour

- **Score** (`GET …/cmmc-score`):
  - Reads only derived requirement status.
  - Each Not Met requirement subtracts its declared value, with its paragraph
    cited.
  - The score is provisional, and lists its blockers, while any requirement is
    Blank or Pending.
  - It is also provisional while a partial-credit requirement lacks an
    implementation level (partial or none, with a rationale), and while
    CA.L2-3.12.4 is Not Met.
  - Conditional-status eligibility follows 170.21(a)(2):
    - score ratio at least 0.8
    - POA&M items at most 1 point, except SC.L2-3.13.11 at 3 points when
      encryption is not FIPS-validated
    - none of the six excluded requirements
- **Findings:**
  - Exactly one project-level finding per requirement (migration `0016`,
    `requirement_findings` keyed by project and requirement). It opens when the
    requirement derives Not Met.
  - Newly failed objectives join the existing finding.
  - The finding is kept when the requirement clears, and reused if it fails
    again.
  - History is append-only, enforced by triggers.
  - The finding carries to successor revisions (ADR 0018).
  - Saving again with nothing changed writes nothing.
- **POA&M:** items are corrective actions on that finding. They are accepted
  only while the requirement is Not Met.
- **Pending:** creates `follow_up` evidence-request items in the score
  response. It never creates a finding or POA&M item.
- **HIPAA paths:**
  - Objective-level reconciliation returns 409 for CMMC.
  - HIPAA has no `scoring` declaration, so its score endpoint returns 404.

## Automated

- `tests/test_cmmc_scoring.py` (7 tests):
  - the committed file rebuilds from the pinned source
  - every catalog requirement has exactly one value
  - the value distribution, plus spot checks
  - every value cites its paragraph
  - discrepancies are reported
  - the 170.21 rules
- `api/tests/test_issue_105_cmmc_scoring_findings.py` (7 tests):
  - 5/3/1 deductions and the all-Met score
  - partial credit: blocked until recorded, then 107 or 105
  - the 3.13.11 conditional exception
  - SSP and excluded-item blockers
  - one finding with history across a retry, a newly failed objective,
    clearing, re-failing, and restart
  - carry to a successor revision
  - Pending creates no finding and no POA&M
  - isolation and HIPAA unchanged
  - migration up/down/up, append-only triggers, and the downgrade guard
- Frontend: one new test covers the score and finding panels.

## Browser

Fixture: `prepare_synthetic_browser_fixture.py`. The score is 102 of 110,
provisional:

- 110 − 5 for AC.L2-3.1.1
- − 3 for partial MFA
- one Pending objective

Captured in headless Chromium in the cloud container (not Edge on the Surface)
at 1600×1000 and 1280×720:

- `CHROMIUM_SCORE_AND_FINDING_*`: the score panel, and the AC.L2-3.1.1 finding
  with its failed objective, note, and POA&M item.
- `CHROMIUM_FINDING_PANEL_*`: the finding panel on its own.
- `CHROMIUM_PARTIAL_CREDIT_*`: IA.L2-3.5.3, worth 3 or 5 points.

There was no horizontal overflow. The only console entry was the missing
`/favicon.ico`.
