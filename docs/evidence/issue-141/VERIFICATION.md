# Issue #141 verification: evidence pending, verified/projected SPRS, 32 CFR 170.21 checks

Date: October 8, 2026. Branch built on #140 (`22e7fa6`, `442e890`
cherry-picked). Synthetic data only.

## What changed

- **Met is accepted and flagged** (`api/main.py`, `api/framework.py`). The CMMC
  declaration carries `"met_without_evidence": "evidence_pending"`. When that key
  is present, Met without evidence is saved as evidence pending instead of being
  refused. Unmapping a Met's last evidence returns the Met to evidence pending
  instead of being refused. HIPAA has no such key and is unchanged: Met without
  evidence is still refused at the click, and so is unmapping the last evidence.
- **Verification is derived, not stored** (`api/verification.py`, new). A Met
  objective is verified when it has a current evidence mapping or a non-empty
  documented interview/observation; otherwise it is evidence pending. A
  requirement is verified Met only when all of its objectives are.
  `CURRENT_MAPPING` is the single predicate #142 extends with staleness and
  expiry. There is no migration and no new column.
  - Record detail determinations and `record_states` gain a `verification`
    field: `verified`, `evidence_pending`, or `null`.
- **Scoring** (`api/cmmc.py` `score()`):
  - Returns `verified` and `projected`, each with `{value, deductions[], arithmetic}`.
    The arithmetic is a literal string, for example `110 − 5 − 5 − 1 − 1 − 3 = 95`.
  - `score` is the verified value, so the issued report, which reads `score`,
    can only show the verified figure.
  - Verified counts only verified-Met requirements as Met. Projected also counts
    evidence-pending Met.
  - Every other requirement (Not Met, Pending, not assessed) deducts its weight
    in both scores.
  - Partial credit (3.5.3, 3.13.11) uses the existing `partial_implementations`
    input, and only for a Not Met requirement. Any other non-Met state deducts
    the full 5.
- **32 CFR 170.21 checks** (`conditional.checks`), computed on the verified
  score only:
  - (a)(2)(i): verified ÷ 110 ≥ 0.8, compared exactly with `Fraction`, so the
    minimum is 88.
  - (a)(2)(ii): every requirement that is not verified Met must be worth 1
    point, except SC.L2-3.13.11 when it is partial at 3 points.
  - (a)(2)(iii): the six never-POA&M requirements must each be verified Met.
  - The paragraph citations are framework data. They were added to
    `conditional_poam.paragraphs` in the scoring JSON, which is rebuilt from the
    pinned XML by `catalog/cmmc_scoring.py`, and the builder now asserts the
    (i)/(ii)/(iii) text is present.
- **Close and issue stay strict** (`api/close.py`):
  - Where evidence pending is allowed (CMMC), every Met objective must be
    verified for `fieldwork_ready`. Otherwise the blocker
    `met_evidence_pending` names the objective.
  - Issue and backup re-run `fieldwork_ready`, so an evidence-pending Met also
    blocks backup and issue of an already signed package.
  - The #108 readiness close (all 110 Met) therefore still requires evidence.
- **UI**:
  - `web/src/views/assessment/CmmcScore.tsx` (new). The toolbar shows the
    verified SPRS score large and the projected score small, labelled
    "projected (includes evidence pending)", plus the Conditional verdict. "Arithmetic and 170.21
    checks" opens both arithmetic strings, deduction totals grouped by reason,
    and the three checks with pass/fail, sources and per-requirement POA&M
    eligibility.
  - The Overview gets the same block, with the arithmetic expandable.
  - The projected score is only ever rendered inside the component that
    renders the verified score first.
  - Evidence pending is shown on objective rows (dashed amber left rule,
    dashed Met button, "Evidence pending" tag), in the requirement header, and
    on requirement-list rows (dashed status dot, "Evidence pending" marker).
  - The old unused `CmmcScorePanel` in `RecordPanels.tsx` was removed.

## Point-value reconciliation (no discrepancy)

- **Regulation text.** `docs/sources/cmmc-dfars/title-32-part-170-2026-10-06.xml`
  sections 170.21 and 170.24 were compared, after tag-stripping, with
  `catalog/sources/title-32-part-170-section-170.2{1,4}-2026-10-01.xml`, the
  files the scoring JSON is built from. The text is identical (3059 and 9751
  characters).
- **Methodology against the scoring JSON.** Annex A of the pinned DoD
  Assessment Methodology v1.2.1 (sha256 `dd88416c…0835`, pp. 12–20) was
  extracted with `pdftotext` and compared row by row with the JSON:
  - All 107 fixed values match.
  - 3.5.3 and 3.13.11 are "3 to 5" in Annex A (p. 15 and p. 19) and partial
    3 / none 5 in the JSON. Section 5(e), p. 7 says the same.
  - 3.12.4 is "NA" in Annex A (p. 18); the JSON rule is `ssp_required`, with
    no points.
  - The 5- and 3-point lists of section 5(d), p. 6 are transcribed into
    `tests/test_cmmc_scoring.py` as a cross-check.
- **Weights.** No weight was changed.

## Judgement calls

- **Unassessed requirements deduct.** Before this change, an empty assessment
  scored 110 (provisional), counting only Not Met. "Counting only verified Met"
  means anything not verified Met deducts its weight. Otherwise marking Met
  without evidence would lower the verified score below leaving the
  requirement blank, and day one would show 110 as the verified headline. An
  empty assessment now shows −203, which equals the official minimum.
  `test_issue_105` was updated to match. This is noted as an open question in
  PROJECT_STATUS.md.
- **Partial credit only for Not Met.** Applying it to any other state, including
  evidence-pending Met with a stale level on file, would understate the
  deduction.
- **HIPAA close is not changed.** A generic close check broke a HIPAA fixture
  that inserts Met rows directly without evidence. The issue's non-goal and the
  brief ("keep HIPAA unchanged") apply, so the new close check is scoped to
  frameworks that allow evidence pending. HIPAA still refuses Met without
  evidence at the click.
- **Current mapping** means the mapping pins a stored version of a project
  artifact that is not in the recycle bin. Binning already requires no
  mappings, so today this equals "mapping exists".
- **Issue comment (#143).** #143 has not landed, so there is no POA&M draft to
  warn on. Per-requirement POA&M eligibility, with its reason, is in the checks
  and in each deduction line (`conditional_poam_allowed`, `poam_reason`) for
  #143 to read.

## Commands run

| Command | Result |
|---|---|
| `python -m pip install -e ".[dev]"` (venv) | ok |
| `pytest` | 253 passed (243 before: +10 in `test_issue_141_verified_score.py`) |
| `ruff check .` | All checks passed |
| `mypy catalog api` | Success: no issues found in 65 source files |
| `python -m unittest discover -s tests` | 97 run, OK (15 skipped) |
| `pnpm install --frozen-lockfile` | ok, lockfile unchanged |
| `pnpm run typecheck` | ok |
| `pnpm run lint` | ok, no warnings |
| `pnpm run test` x3 | 78 passed, 6 files, on each of 3 runs (76 before) |
| `pnpm run build` | ok |

New and changed tests:

- `api/tests/test_issue_141_verified_score.py` (10 tests):
  - Met is saved without evidence as evidence pending, and evidence or an
    observation verifies it.
  - Unmapping returns a verified Met to evidence pending.
  - A requirement is verified only when every objective is.
  - HIPAA still refuses Met without evidence.
  - An empty assessment scores −203 in both figures.
  - Mixed evidence gives `110 − 5 − 1 − 3 = 101` verified and `110 − 3 = 107`
    projected, and mapping evidence raises verified by 5.
  - Arithmetic is parsed and summed.
  - Partial credit follows Methodology p. 7 and Annex A pp. 15 and 19.
  - The 88 boundary: 88 passes, 87 fails, and projected 88 never rescues
    verified 87.
  - Never-POA&M requirements fail the check when Not Met or evidence pending.
  - 3.12.4 has no points but blocks completion.
  - The checks cite (a)(2)(i)–(iii).
  - An evidence-pending Met blocks close, backup and issue of a signed #108
    package, and package generation.
- `tests/test_cmmc_scoring.py`:
  - The paragraph citations.
  - Methodology reconciliation (section 5(d) lists p. 6, section 5(e) p. 7,
    Annex A pp. 15, 18, 19).
- Updated:
  - `test_issue_104`: the click-time refusal test became the evidence-pending
    test.
  - `test_issue_105`: the empty score is now −203.
  - `test_issue_140`: `record_states` gained `verification`.
  - `RequirementWorkspace.test.tsx`: the mock API no longer refuses Met; the
    failed-save test uses a different refusal; added an evidence-pending test
    and a score block test.
  - `App.test.tsx`: the score mock is in the new shape; the Overview score
    block is asserted.
- No isolation or security test was weakened.

## Run against the app

1. `python docs/evidence/issue-140/serve_synthetic_api.py <empty-dir>`
2. `pnpm run dev`
3. `python docs/evidence/issue-141/seed_synthetic_cmmc.py`. It prints the
   arithmetic and the checks for both projects.
4. `PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers node docs/evidence/issue-141/capture_screenshots.mjs docs/evidence/issue-141`

Measured (Chromium, synthetic):

| Measure | Result |
|---|---|
| Fieldwork project, verified | `110 − 5 − 5 − 1 − 1 − 3 = 95` |
| Fieldwork project, projected | `110 − 5 − 1 − 3 = 101` |
| Fieldwork 170.21 | (i) pass, (ii) **fail** (AC.L2-3.1.1 evidence pending 5 pt, AC.L2-3.1.2 Not Met 5 pt), (iii) pass; Not eligible |
| Conditional project, verified / projected | `110 − 1 − 1 − 3 = 105` / `110 − 1 − 3 = 106` |
| Conditional 170.21 | all pass (SC.L2-3.13.11 at 3 points as the named exception); Eligible |
| AC.L2-3.1.1 rows | 5 evidence pending, 1 verified by mapped evidence |
| List rows marked evidence pending | AC.L2-3.1.1, IA.L2-3.5.9 |
| Horizontal overflow at 800 px | 0 px |

## Screenshots

| File | Shows |
|---|---|
| `01-requirement-view-evidence-pending-1440.png` | Toolbar score (verified 95 headline, projected 101 labelled, Not eligible); evidence-pending objective rows, header tag and list marker |
| `02-score-arithmetic-and-170-21-failing-1440.png` | Expanded arithmetic for both scores and a failing 170.21 (a)(2)(ii) check |
| `03-requirement-list-evidence-pending-1440.png` | Requirement list with the dashed evidence-pending row |
| `04-overview-score-170-21-failing-1440.png` | Overview score block, arithmetic expanded, failing case |
| `05-overview-score-170-21-passing-1440.png` | Overview score block, every 170.21 check passing, Eligible |
| `06-requirement-view-score-800.png` | Score detail at 800 px |

## Not done here

- Evidence staleness and expiry (#142). The hook is `CURRENT_MAPPING`.
- Package gating on evidence pending (tickets 7 and 9). This ticket provides
  `evidence_pending` and `verification` for them to read.
- The 170.21 warning on a POA&M draft (#143 has not landed).
- No Windows or Surface run. CI has not run; the commits are local only.
