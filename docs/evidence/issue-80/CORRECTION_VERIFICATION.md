# Issue #80 presentation-only correction verification

September 29, 2026. Synthetic data only. Branch `claude/issue-80-presentation-lpt8ng` from `main` at `f5ae4fd`.

## What was built

- Migration `0014` adds append-only `package_corrections` and `issuance_supersessions`, a `current_issuances` view, and a trigger that allows at most one current issued package per project. An issue stops being current only when an issued correction supersedes it.
- `POST /api/projects/{project}/packages/{package}/corrections` needs `classification: "presentation_only"` (a missing value returns 422; any other value returns 409), `unchanged_source_attested: true`, and a non-blank reason. It records the actor, the reason, the prior package and prior issue, and the result package.
- The corrected package is rendered from the prior package's **stored** source snapshot, so no new snapshot is taken. The system also checks the attestation: if the live source content differs from the snapshot, the request returns 409 and points to the substantive path (#81).
- The corrected package then goes through the existing review, sign-off, backup, and issue gates. Issuing it writes the supersession record and the new issue snapshot in one transaction. The issued manifest carries the correction record.
- Issue readiness blocks two cases. An ordinary package cannot become a second first issue. A correction whose prior issue is no longer current is stale.
- UI: the current issued package's card carries the correction form (an explicit classification checkbox, the unchanged-source attestation, and a reason). Package cards show `Issued · Current`, `Superseded by …; retained and retrievable`, and `Corrects issued package …`.

## Automated evidence

`api/tests/test_issue_m3_presentation_correction.py` has 12 tests covering:
- same-snapshot reissue
- unchanged source tables
- prior snapshot, components, sign-off, backup, and issue rows kept byte-for-byte
- prior components still downloadable
- exactly one current issue after restart
- classification, attestation, and reason validation with no writes
- changed-source and unissued-package rejection
- failed backup and failed issue leaving the current issue unchanged
- stale second correction and uncorrected regeneration blocked
- same-client and cross-client guessed IDs returning 404
- direct-SQL forgery rejected and immutability of the new tables
- a populated downgrade/upgrade cycle, with downgrade refused once corrections exist
- upgrade refused when legacy data holds two unsuperseded issues in one project

A clean `alembic upgrade head` / `downgrade -1` / `upgrade head` cycle also passed through the CLI.

One existing test changed. The #79 FK-map comparison in `test_issue_m3_assessment_revision_contract.py` now upgrades to `0013` rather than `head`, because it verifies 0013's table rebuild. At `head` it also counted the new 0014 tables.

Local gates: 188 API tests passed; 74 catalog tests passed (15 optional skips); 59 frontend tests passed; Ruff, Mypy, TypeScript typecheck, ESLint, and production build passed.

## Browser evidence

`prepare_synthetic_browser_fixture.py` builds two projects:
- Project A has an original issue that an issued correction supersedes, plus a stale second correction whose backup was refused.
- Project B, under another client, has one current issue.

The production build was served on loopback and captured in **headless Chromium in the cloud container, not Edge on the Surface**, at 1600×1000 and 1280×720:

- `CHROMIUM_CLASSIFICATION_*`: correction form on the current issue
- `CHROMIUM_SUPERSEDED_HISTORY_*`: superseded original, still listed with its components
- `CHROMIUM_FAILED_REISSUE_*`: stale correction blocked, with the recorded failed backup
- `CHROMIUM_PROJECT_SWITCH_*`: Project B after the switch, with no Project A package IDs in its panel

No document-level horizontal overflow at either width. One console error, a 404 resource load on the desktop page's first load. The response listener did not capture its URL (likely the favicon, since the static mount has none). It was not investigated further. Delayed-response isolation is covered by the existing frontend suite; this capture did not inject delays.

Not done: a visible Edge run on the Surface ARM64 pilot device.
