# Issue #145 evidence: drafts any time, one review-and-issue act, Profile approved once

All data is synthetic (`seed_synthetic_projects.py`). Decision record:
`docs/decisions/0021-one-act-issue.md`.

## What the pictures show

| File | Shows |
| --- | --- |
| `01-draft-hipaa-report-docx-page1.png`, `01b-...-page3.png` | HIPAA report draft: header on the first and a later page, title prefixed |
| `02-draft-hipaa-poam-xlsx-sheet1.png` | HIPAA POA&M draft: `&CDRAFT` sheet header and the banner in the first row |
| `03-draft-cmmc-report-docx-page1.png`, `04-draft-cmmc-ssp-docx-page1.png` | CMMC report and SSP drafts (SSP reads NOT APPROVED) |
| `09-draft-csv-first-line.png` | CMMC CSV drafts: first line is `DRAFT — NOT ISSUED` |
| `05-reports-tab-draft-and-issue-1440.png` | Reports tab: Download draft, Review and issue… |
| `06-review-and-issue-dialog-with-warnings-1440.png` | Dialog: "Worth checking" (two warnings), reviewer, date, optional note, one Issue button, no ticks |
| `07-review-and-issue-dialog-must-fix-1440.png` | Dialog with hard gates under "Must be fixed before issue"; Issue disabled |
| `10-backup-failure-nothing-issued-1440.png` | A failed backup: the message, dialog stays open, nothing issued |
| `11-issued-in-one-act-1440.png` | After one Issue: the issued version, reviewer and note |
| `08-profile-approve-one-step-1440.png`, `08b-profile-approved-1440.png` | Profile: one Approve version button, no Record review; approved in one click |
| `12-profile-unknowns-block-issue-1440.png` | A Profile approved while it still records an unknown: "Profile unknowns to resolve" under Must be fixed, Issue disabled |
| `13-issuing-again-replaces-current-1440.png` | With a current issue the dialog says issuing again replaces it (it will be marked Superseded) |

The DOCX and XLSX pictures are the downloaded drafts converted with LibreOffice
(`soffice --headless --convert-to pdf`) and rendered with `pdftoppm`. LibreOffice opening
them is also the check that the watermarked files are valid. In the converted PDFs the
banner appears on every page: 67 of 66 pages for the HIPAA report (every page plus the
title), 11 of 10 for the CMMC report, 12 of 11 for the SSP, and on every sheet of the
POA&M workbook (33 of 28 pages, including the banner row).

The backup failure is injected with `serve_with_failing_backup.py`, the same way the
tests do (archive validation raises), so the real failure path runs: the failed backup is
recorded and audited, nothing is issued, and the API returns the 409.

`capture_screenshots.mjs` prints the measured values it saw (dialog contents, buttons,
readiness state after approving, backup-failure message, versions after).

## Sign-off acts to issue

Measured by counting the controls a person must use, from a Profile in Draft to an issued
package.

| | Before | After |
| --- | --- | --- |
| HIPAA | 9: Record review, Approve version, Profile complete decision (reviewer and evidence typed), Generate, Start review, Mark reviewed, Sign off, Create backup, Issue | 2: Approve version, Review and issue |
| CMMC | 10: the same nine plus Approve SSP | 3: Approve version, Approve SSP, Review and issue |

## Which checks block and which only warn

Block (stop the issue, listed under "Must be fixed before issue", each linking to its list):

- Profile approved and complete, with no unknown left: no Unknown value and no "Unknowns & follow-up" item (HIPAA and CMMC). Profile complete means no unknown remains, so approving a version that records one does not record Profile complete
- Every objective or standard decided (blank, pending and missing N/A reasons)
- Not Met reconciled to a finding and a corrective action (HIPAA)
- Reopened records revalidated
- Security Risk Analysis scope and risks complete (HIPAA)
- Met with no evidence or observation, every POA&M item closed, SSP approved,
  evidence files verified (CMMC internal readiness close)
- At issue time, unchanged from before: template bytes, package drift against current
  data, evidence file integrity, and a successful automatic backup

Warn only (listed under "Worth checking", nothing to tick):

- Corrective work still open (HIPAA; open work may continue after delivery)
- Evidence due for review soon, or already past its review date

## Checks run

Final tree, with the scratchpad venv (`pip install -e '.[dev]'` from this worktree) and pnpm:

| Command | Result |
| --- | --- |
| `pytest -q` (full) | 329 passed, 2 warnings, 489 s |
| `ruff check .` | All checks passed |
| `mypy catalog api` | Success: no issues found in 78 source files |
| `python -m unittest discover -s tests` | Ran 97 tests, OK (skipped=15) |
| `pnpm install --frozen-lockfile` | Done |
| `pnpm run typecheck` | clean |
| `pnpm run lint` | clean |
| `pnpm run test` | 11 files, 118 tests passed |
| `pnpm run build` | built |

Review fixes added tests that each failed before their fix (backup folder replaced by a
file, database error at the issue step, failed generation keeping its attempt, sign-off
text, double submit) and passed after; see `api/tests/test_issue_145_*.py`,
`web/src/ReviewAndIssue.test.tsx` and `web/src/ProfilePanel.test.tsx`.
