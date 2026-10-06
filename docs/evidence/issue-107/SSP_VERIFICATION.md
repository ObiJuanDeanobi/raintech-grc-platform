# Issue #107 — Minimum authoritative final SSP

October 6, 2026. Synthetic data only.

## Template decision

The template had to be decided without new material. Johnathan, October 6:
"make your best decisions with what I've given you". The decision:

- The structure follows the **public NIST SP 800-171 Rev. 2 CUI SSP template**.
  It is a U.S. Government work and holds no client material.
- NIST's *Not Applicable* choice is removed, because CMMC has no N/A
  (Johnathan, October 6).
- Provenance, hashes, and the delegated approval are recorded in
  `docs/templates/cmmc/ssp-v1/APPROVAL_RECORD.md`.
- `api/ssp.py` refuses to generate if `structure.json` changes from its
  approved hash.

## Behaviour

- **Generate** (`POST …/assessments/{a}/ssp`). The request is refused, with
  named blockers, unless:
  - the framework declares scoring (CMMC);
  - the Profile is approved; and
  - all 110 requirements derive Met or Not Met.

  Each SSP pins:
  - the template version and template hash;
  - a canonical source snapshot (Profile fields, environment items,
    requirement statuses, POA&M items) and its hash.

  Statuses are *Implemented* (Met) or *Planned to be Implemented* (Not Met,
  with POA&M items listed). Implementation statements are drafted only from the
  assessor's own notes and interview observations. No text is invented.
- **Edit** (`PUT /ssp/{id}`): every save appends an immutable version. You can
  edit the system description, the environment narrative, and per-requirement
  statements.
- **Approve** (`POST /ssp/{id}/approve`): needs every section filled in. It
  records the approver and freezes the document, enforced by database triggers.
  After approval:
  - no new version can be added;
  - only the latest version can have been approved;
  - document, version, and approval rows can never change.
- **Export** (`GET /ssp/{id}/versions/{n}/docx`): a deterministic DOCX delivery
  copy, marked approved or NOT APPROVED. The export is never the system of
  record.
- **UI**: an SSP panel in the CMMC workspace. Opening a requirement shows its
  own implementation statement for editing. The fields are keyed by version,
  so they always start from the loaded version.

## Automated

`api/tests/test_issue_107_cmmc_ssp.py` (4 tests):

- Generation is blocked until every requirement is resolved.
- The full flow, in order:
  - generate: 110 requirements, Planned with the POA&M item on the Not Met
    requirement, and drafts made from the observations;
  - approval is blocked while sections are empty;
  - an edit creates version 2;
  - an unknown requirement is rejected;
  - approve; a second approval returns 409;
  - an edit after approval returns 409;
  - the export is byte-identical on repeat, contains the edited text and
    "Planned to be Implemented", and does not contain "Not Applicable";
  - an unknown version returns 404.
- Isolation: another project's paths and a HIPAA project return 404.
  Direct-SQL updates and deletes are refused.
- A changed template is refused.

A frontend test edits the open requirement's statement, saves a new version,
then approves and checks the frozen view. A load race was found here: the
fields could render empty for one frame. It was fixed with a keyed editor, and
the test then passed 8 of 8 runs; the full suite passed 3 of 3.

Local results:

- `pytest`: 234 passed
- catalog `unittest`: OK
- frontend: 66 passed
- Ruff, Mypy, typecheck, ESLint, and build: clean
- The exported DOCX parses as well-formed XML: 109 *Implemented* and 1
  *Planned*.

## Browser

Fixture: `prepare_synthetic_browser_fixture.py`. Captured in headless Chromium
in the cloud container (not Edge on the Surface) at 1600×1000 and 1280×720:

- `CHROMIUM_SSP_GENERATE_*`
- `CHROMIUM_SSP_EDITED_*` (version 2)
- `CHROMIUM_SSP_FROZEN_*` (approved and frozen)

There was no horizontal overflow. The only console entry was the existing
`/favicon.ico` 404.

## Not covered

- Opening the DOCX in Microsoft Word on the Surface (#109).
- The SSP inside the issued CMMC package. That is #108.
