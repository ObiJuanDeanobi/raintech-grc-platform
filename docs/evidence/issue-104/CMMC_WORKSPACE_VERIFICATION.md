# Issue #104 — CMMC objective-level workspace verification

October 6, 2026. Synthetic data only.

## What changed

- `seed_cmmc_catalog` runs at startup beside `seed_framework`. On re-seed it
  refreshes the CMMC declarations. HIPAA records are unchanged.
- CMMC declares the shared `PROFILE_READINESS` rule. Previously only HIPAA
  declared it, and project creation needs it.
- `GET /api/frameworks` feeds a framework picker in both project-creation forms.
  HIPAA stays the default.
- Workspace, `requirement_with_objectives` mode:
  - The rail lists requirements; only the open requirement's objectives are
    nested under it.
  - The requirement view shows all of its objectives with their status, and
    the derived requirement status.
  - An objective opens the shared determination editor, under "Requirement
    context".
  - Work-area filters come from the data.
- RainTech practitioner guidance (#31) is read from
  `catalog/versions/cmmc-l2-ag-v2.13-guidance.json` at startup.
  - Startup fails if the guidance is pinned to a different catalog hash.
  - It is returned as `practitioner_guidance` on record detail. It is never
    written to determinations.
  - It is shown in a dashed, amber panel labelled "not DoD or NIST text".
- Hidden for CMMC until their tickets land:
  - fieldwork close and package panels (shown only when `close_readiness` is
    declared)
  - HIPAA-shaped Not Met reconciliation (CMMC findings and POA&M are #105)
- The API already refuses close and SRA for CMMC: 409 and 404.

The shared determination, rollup, evidence-mapping, audit, and active-revision
engines are reused unchanged. Statuses, the rollup, and which records accept a
determination come from the CMMC declarations.

## Automated

- `api/tests/test_issue_104_cmmc_workspace.py` (7 tests):
  - 110 requirements and 320 objectives, with only objectives editable
  - the derivation order: blank, Pending, Not Met over Pending, then Met
  - requirement edits and N/A are refused
  - Met needs evidence or an interview, then succeeds with mapped evidence
  - HIPAA unchanged (149 determinations, N/A kept)
  - cross-framework, same-client, and cross-client guessed IDs return 404
  - close and SRA are refused
  - restart persistence
  - guidance is separate from the official text and changes no status
- Three existing tests changed:
  - The SRA migration test now counts HIPAA records only.
  - Two isolated-repository fixtures now copy the CMMC catalog and guidance
    files.
- Frontend: two new tests cover the CMMC presentation (objectives, nesting,
  hidden HIPAA panels, guidance region) and the framework choice sent at
  project creation. The HIPAA fixture now declares `close_readiness`, as the
  real API does.
- Local results:
  - `.venv/bin/pytest -q`: 208 passed
  - `python -m unittest discover -s tests`: 87 ran, OK
  - `ruff check .` and `mypy catalog api`: clean
  - `pnpm run typecheck`, `lint`, `test` (62 passed), and `build`: clean
- No migration was added, so no alembic cycle was needed.

## Browser

Production build served on loopback from the fixture created by
`prepare_synthetic_browser_fixture.py`. Captured in headless Chromium in the
cloud container (not Edge on the Surface) at 1600×1000 and 1280×720:

- `CHROMIUM_REQUIREMENT_OBJECTIVES_*`: AC.L2-3.1.1 with its six objectives (Met,
  Met, Pending, Not Met, blank, blank). The requirement derives Not Met.
  Guidance is in its own panel.
- `CHROMIUM_OBJECTIVE_DETERMINATION_*`: objective [d] in the editor, under
  "Requirement context".
- `CHROMIUM_SAME_CLIENT_HIPAA_*`: switching to the same client's HIPAA project
  shows the HIPAA workspace.
- `CHROMIUM_CROSS_CLIENT_CMMC_*`: another client's CMMC project. AC.L2-3.1.1
  derives Blank, so nothing leaked.
- `CHROMIUM_PROJECT_CREATION_*`: the framework picker with CMMC selected.

Horizontal overflow was 0px at every step, in both sizes. The only console
entry was a 404 for `/favicon.ico` on first load. It is unrelated: the build
has no favicon.

## Not covered

- Edge on the Surface (#109).
- Scoring, findings and POA&M, close, SSP, and evidence hash checks (#105–#108).
