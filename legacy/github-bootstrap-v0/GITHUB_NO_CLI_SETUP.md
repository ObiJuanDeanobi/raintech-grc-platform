# GitHub Setup Without GitHub CLI

Use this path when GitHub CLI cannot be installed on the work PC.

## What You Need

Create a temporary GitHub personal access token with private repo access.

The simplest option is a classic token with the `repo` scope. Delete the token after the repository is created and seeded.

If the repository belongs to a GitHub organization, make sure the token is authorized for that organization if SSO is enforced.

## Recommended Command

From this repository folder:

```powershell
.\scripts\bootstrap-github-rest.ps1 -CreateRepo -Push -SeedBacklog
```

The script will prompt for the token securely. It does not write the token to disk.

This creates:

- private GitHub repository named `raintech-grc-platform`
- `origin` remote
- pushed `main` branch
- GitHub labels
- V1-V8 milestones
- starter backlog issues

## Organization Repo

If the repository should live under a GitHub organization:

```powershell
.\scripts\bootstrap-github-rest.ps1 -Owner "ORG_NAME" -RepoName "raintech-grc-platform" -CreateRepo -Push -SeedBacklog
```

Replace `ORG_NAME` with the GitHub organization login.

## Existing Repo

If you manually create the private repo in GitHub first, set the remote and push:

```powershell
git remote add origin https://github.com/OWNER/raintech-grc-platform.git
git push -u origin main
.\scripts\bootstrap-github-rest.ps1 -Owner "OWNER" -RepoName "raintech-grc-platform" -SeedBacklog
```

## After Setup

Confirm the repository has:

- `main` branch
- 8 milestones
- 16 labels
- 18 starter issues
- issue templates under `.github/ISSUE_TEMPLATE`
- roadmap and decision docs

Then delete the temporary GitHub token.
