# Domain Docs

This is a single-context repository for the RainTech GRC platform.

Before software delivery work, read:

- `README.md`
- `ROADMAP.md`
- `docs/PROJECT_OPERATING_MODEL.md`
- `docs/specification.md`
- relevant files under `docs/decisions/`

## Domain Direction

- CMMC Level 2 and a full HIPAA program are both in V1.
- The product spine is:
  `Client -> Project -> Profile -> Assessment -> Continuous Remediation -> Evidence -> Reports/Documents`.
- The project is the engagement boundary.
- The project profile begins during onboarding and matures during assessment,
  evidence, and remediation work.
- Issued assessments and reports use immutable profile snapshots.
- Remediation and recurring reviews continue at project level across assessments.
- Build vertical slices instead of broad disconnected dashboards.

## Existing Decision Location

Existing decisions live under `docs/decisions/`. Use those files as the current ADR-style record for this repo.

If future decisions are needed, keep them concise and use the existing style unless the user asks for a different decision format.
