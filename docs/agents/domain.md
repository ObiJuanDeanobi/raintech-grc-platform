# Domain Docs

This is a single-context repository for the RainTech CMMC GRC platform.

Before software delivery work, read:

- `README.md`
- `ROADMAP.md`
- `docs/PROJECT_OPERATING_MODEL.md`
- `docs/specification.md`
- relevant files under `docs/decisions/`

## Domain Direction

- CMMC Level 2 is the only compliance framework in scope until V1-V5 are solid.
- The product spine is: `Profile -> Scope/Quote -> Gap Analysis -> Evidence -> Reports -> Documents`.
- The customer profile is progressive:
  - `InitialProfile` supports intake, readiness scoring, and quoting.
  - `ImplementationProfile` is enriched during gap analysis and drives documents/reports.
- Build vertical slices instead of broad disconnected dashboards.

## Existing Decision Location

Existing decisions live under `docs/decisions/`. Use those files as the current ADR-style record for this repo.

If future decisions are needed, keep them concise and use the existing style unless the user asks for a different decision format.
