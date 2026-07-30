# RainTech GRC Platform

Fresh-start local-first platform for RainTech internal CMMC Level 2 and HIPAA
delivery work.

## Current Status

The first production vertical slice is implemented on Issue #44: a local
FastAPI/SQLite service and React assessment workspace for the pinned HIPAA
catalog. Existing application code remains legacy reference material and is not
the production direction.

## Direction

The rebuild follows this product spine:

```text
Client -> Project -> Profile -> Assessment -> Continuous Remediation
       -> Evidence -> Reports/Documents
```

- V1 supports CMMC Level 2 and a full HIPAA program.
- The project is the engagement boundary.
- The project profile begins during onboarding and matures throughout delivery.
- Issued assessments are immutable snapshots; remediation continues across them.
- Hosted access, RBAC, public intake, crosswalking, and automation are deferred.

See [ROADMAP.md](ROADMAP.md) and [docs/PROJECT_OPERATING_MODEL.md](docs/PROJECT_OPERATING_MODEL.md) before adding new product surface area.

The approved specification draft is [docs/specification.md](docs/specification.md).
The planned UI comparison is
[docs/prototypes/v1-ui-prototype-brief.md](docs/prototypes/v1-ui-prototype-brief.md).

## Repository Map

```text
.agents/             Repository-scoped AI development skills
.github/             Active issue and pull-request templates
docs/                Current specification, operating model, ADRs, and briefs
legacy/              Superseded application, prototypes, and setup artifacts
data/                Legacy local database/evidence (ignored; do not delete)
exports/             Legacy generated exports (ignored)
PROJECT_STATUS.md    Current phase, objective, risks, and next action
ROADMAP.md           Approved product sequencing
```

Production code lives under `api/` and `web/`. The committed framework layer in
`catalog/versions/` is a read-only application input.

## Run the Slice 1a Workspace

Prerequisites: Python 3.12, Node 24, and pnpm 11.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
pnpm install
```

Start the API:

```powershell
.\.venv\Scripts\python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, start the UI:

```powershell
pnpm dev
```

Open http://127.0.0.1:5173. The first launch creates `data/workspace.db` and
`data/files/`; both are intentionally ignored because they hold local
engagement data. Launcher, packaging, and backup/restore remain Issue #32.

## Verify

```powershell
pytest
ruff check .
mypy catalog api
pnpm typecheck
pnpm lint
pnpm test
pnpm build
python -m unittest discover -s tests
```

## Legacy Reference App

The prior FastAPI tracker remains available under `legacy/evidence-tracker/`.
It is reference material, not the production foundation.

```powershell
powershell -ExecutionPolicy Bypass -File ".\legacy\evidence-tracker\run.ps1" -Port 8010
```

Then open:

- Legacy platform shell: http://127.0.0.1:8010/platform
- Legacy evidence tracker: http://127.0.0.1:8010

## AI-Assisted Development Workflow

This repo uses a lightweight AI workflow. Chat Mode is for discussion, learning, brainstorming, and questions without file changes. Plan Mode creates or refines the project specification before implementation. Build Mode implements one approved ticket or vertical slice at a time. Review Mode validates existing work against the specification and acceptance criteria.

Major transitions require user approval. Product code is not considered complete until the relevant tests, type checks, lint checks, builds, and review results have been reported.
