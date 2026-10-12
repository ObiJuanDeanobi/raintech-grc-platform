# Issue #146 evidence: the CMMC gap-assessment package

All data is synthetic (`seed_half_done.py`, an approved Profile and a gap-bearing CMMC project:
five requirements Not Met, two Met with nothing yet to verify them, one POA&M draft and one
open item). Two seeds: `MODE=half` leaves 212 of 320 objectives undecided; `MODE=decided`
decides every objective. Decision record: `docs/decisions/0023-cmmc-gap-assessment-package.md`.

| File | Shows |
| --- | --- |
| `01-reports-tab-with-package-choice-1440.png` | Reports tab: the two-option choice above Download draft and Review and issue |
| `02-finalize-dialog-gap-assessment-default.png` | Decided project, Gap assessment (default): no "Must be fixed", five "Worth checking" lines (10 Met needing evidence, 3 gaps with no POA&M item, 2 open POA&M items, 2 failing 170.21 checks, SSP not approved), Issue enabled |
| `03-finalize-dialog-final-self-assessment-blocked.png` | Same dialog with Final self-assessment: its own unchanged gates, Issue disabled |
| `09-half-done-finalize-blocked-undecided.png` | Half-done project: "Must be fixed: 212 Objectives not yet decided"; Issue disabled. The draft still downloads |
| `04-draft-gap-report-incomplete-page1.png` | Draft of the half-done project: "This assessment is not complete, 212 of 320 objectives not yet assessed", verified score with arithmetic, 170.21 checks |
| `05-draft-sprs-worksheet-csv.png` | Verified SPRS worksheet draft: Assessment complete row, "n/a until assessed", Scoring note column |
| `06-draft-poam-csv.png` | POA&M draft: Draft and Open items, "No POA&M item yet", eligibility and reason |
| `07-draft-ssp-page1.png` | SSP draft (`System_Security_Plan_DRAFT.docx`, reads NOT APPROVED) |
| `08-draft-evidence-index-csv.png` | Evidence index draft |
| `10-finalized-gap-assessment-1440.png` | One Issue on the decided project: issued, Current, five files |
| `11-issued-gap-report-page1.png`, `11b-...-page2.png` | The issued report (no "not complete" section, because every objective is decided) |

DOCX files were converted with LibreOffice (`soffice --headless --convert-to pdf`) and
rendered with `pdftoppm`; CSV pictures are made by `render_csv.mjs`. `capture_screenshots.mjs`
prints what it measured: for `MODE=half` the gap checklist had one must-fix group
(212 Objectives not yet decided) and Issue was disabled while both drafts answered 200; for
`MODE=decided` there were no must-fix groups, Issue was enabled, the readiness-close option
listed 17 Objectives still Not Met, 10 Met evidence still needed, 2 Open POA&M items and
1 SSP not approved with Issue disabled, and the issued version had
`CMMC_L2_Gap_Assessment_Report.docx`, `SPRS_Worksheet_Verified.csv`, `CMMC_POAM.csv`,
`System_Security_Plan_DRAFT.docx`, `Evidence_Index.csv`.
