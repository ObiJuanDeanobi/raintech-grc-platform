# Issue #108 — CMMC readiness close gate and standard package issuance

October 6, 2026. Synthetic data only.

## Behaviour

- **Close gate.** CMMC now declares `close_readiness` with `final_statuses:
  ["Met"]`. The shared determination check therefore requires every one of
  the 320 objectives to be Met, which means every one of the 110 requirements
  is Met. Three CMMC validators are added in `api/close.py`, and each blocks
  on its own, with a named reason and a link:
  - `poam_closed`: no open POA&M item on any requirement finding.
  - `ssp_approved`: an approved SSP exists for this assessment.
  - `evidence_verified`: every mapped evidence version passes its hash check.
    The close-readiness API runs this check when it has a storage root, and
    issuance has enforced it since #106.

  The Profile must be complete, as for HIPAA. The SRA check now runs only when
  a framework lists `sra_complete`, so HIPAA is unchanged and CMMC never gets
  "SRA not declared".
- **Closing POA&M items** (migration `0020`):
  - Corrective actions used to close only through a HIPAA validation event.
    CMMC items now close through an append-only `poam_closures` record, which
    requires a rationale.
  - The API allows a closure only while the requirement derives Met.
  - The close trigger accepts either path.
  - Downgrade is refused once any closure exists.
- **Standard package** (`cmmc-v1`):
  - The source snapshot adds a `cmmc` block: the score, every requirement's
    derived status and objectives, the findings with POA&M items, closures and
    history, and the approved SSP version as plain data.
  - `api/renderers/cmmc.py` renders four components from that snapshot alone:
    - the assessment report (DOCX), showing the score as "110 of 110";
    - the approved SSP (DOCX);
    - the POA&M history (CSV);
    - the evidence index (CSV).
  - The package manifest is the issuance manifest.
  - SSP DOCX rendering was split into a pure `ssp_docx()` so issued packages
    never read live data.
- **Reuse.** The HIPAA chain applies unchanged: review and sign-off, the
  pre-issuance backup, atomic issue, presentation correction (#80/#100), and
  substantive reopening (#81). The only change is that review now gets each
  template version's expected component kinds from `package_component_kinds()`.
  HIPAA versions keep the per-template-file rule.
- **UI:**
  - The package heading is now framework-neutral.
  - POA&M items get **Close item** once their requirement derives Met.
  - Close and package panels appear for CMMC because it declares
    `close_readiness`.

## Automated

`api/tests/test_issue_108_cmmc_close_issue.py` (5 tests):

- **Each gate condition blocks on its own.** Final determinations, open
  POA&M, the SSP, and the Profile are each blocked, with no SRA blocker.
  Closing a POA&M item is refused while the requirement is Not Met and refused
  with an empty rationale; after the fix it succeeds. Generation is refused
  while the Profile is incomplete, and no package is written.
- **Full issue flow:**
  - The package has four components and template `cmmc-v1`.
  - The SSP and report contents are correct, and the POA&M history shows the
    closure.
  - Issuing without sign-off is refused. Sign-off, backup, and issue succeed.
  - A presentation correction is reissued.
  - After a restart, exactly one package is Current, and `current_issuances`
    has 1 row.
- **Substantive reopening:**
  - The successor is blocked on revalidation and on a new SSP.
  - After revalidation and an approved SSP, it is reissued.
  - The prior package becomes Superseded and the new one Current.
- **Isolation:** another project's paths are refused.
- **Migration:** a 0020 cycle, append-only closures, and the downgrade guard.

Existing tests changed:

- The #104 test now expects CMMC close readiness to return 200 and be blocked,
  instead of 409 "not declared".
- The #104 frontend assertion follows the neutral package heading.

New frontend test: a POA&M item is closed only once its requirement derives Met.

Local results:

- `pytest`: 239 passed
- catalog `unittest`: OK
- frontend: 67 passed (three consecutive runs)
- Ruff, Mypy, typecheck, ESLint, and build: clean

## Browser

Fixture: `prepare_synthetic_browser_fixture.py`. Captured in headless Chromium
in the cloud container (not Edge on the Surface) at 1600×1000 and 1280×720:

- `CHROMIUM_CLOSE_BLOCKED_*`: Project A, with blockers named: "Close POA&M
  item on AC.L2-3.1.1…" and "Approve the final System Security Plan".
- `CHROMIUM_PACKAGE_ISSUED_*`: Project B. All five close checks are Ready.
  The package shows its four components, "Issued · Current", and the
  correction and reopen controls.

There was no horizontal overflow. The only console entry was the existing
`/favicon.ico` 404.

## Not covered

- #109: the CMMC Windows/offline acceptance on the Surface, including opening
  the DOCX components in Word. This is deferred by Johnathan.
