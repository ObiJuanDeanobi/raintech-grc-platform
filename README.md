# RainTech CMMC GRC Platform

Local-first CMMC Level 2 GRC platform for RainTech internal delivery work.

## Direction

The rebuild follows this product spine:

```text
Profile -> Scope/Quote -> Gap Analysis -> Evidence -> Reports -> Documents
```

The customer profile is progressive:

- V1 creates an initial scoping profile for readiness and quote.
- V2 gap analysis enriches it into the final implementation profile.
- V5 document generation uses the final implementation profile.

See [ROADMAP.md](ROADMAP.md) and [docs/PROJECT_OPERATING_MODEL.md](docs/PROJECT_OPERATING_MODEL.md) before adding new product surface area.

The original evidence tracker is still available, and the new platform adds:

- customer implementation profiles
- readiness score and quote records
- CMMC Level 2 assessment workspaces
- objective status, notes, POA&M items, and tailored evidence guidance
- manual evidence upload, reuse, and mapping to objectives
- generated SSP/policy/procedure/diagram drafts from templates
- evidence capture, POA&M, and client-ready ZIP exports

## Quick Start

```powershell
.\run.ps1
```

Then open:

- GRC Platform: http://127.0.0.1:8000/platform
- Legacy evidence tracker: http://127.0.0.1:8000

If port 8000 is already in use:

```powershell
.\run.ps1 -Port 8010
```

The app stores its working database and evidence files under `data/`, which is intentionally ignored by Git.

## GitHub Setup

This repository includes GitHub issue templates and backlog seed files under `.github/`.

If GitHub CLI is available:

```powershell
gh auth login
.\scripts\bootstrap-github.ps1 -CreateRepo -Push -SeedBacklog
```

If GitHub CLI is not available, create a GitHub token with private repo access and use the REST bootstrap script:

```powershell
.\scripts\bootstrap-github-rest.ps1 -CreateRepo -Push -SeedBacklog
```

The REST script prompts for the token and does not write it to disk. You can also set it temporarily for the current PowerShell session:

```powershell
$env:GITHUB_TOKEN = "paste-token-here"
.\scripts\bootstrap-github-rest.ps1 -CreateRepo -Push -SeedBacklog
Remove-Item Env:\GITHUB_TOKEN
```

If the private repository already exists and the remote is set, either bootstrap script can seed the backlog:

```powershell
.\scripts\bootstrap-github.ps1 -SeedBacklog
# or
.\scripts\bootstrap-github-rest.ps1 -SeedBacklog
```
