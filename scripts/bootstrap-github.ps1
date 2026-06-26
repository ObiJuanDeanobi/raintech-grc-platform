param(
    [string]$RepoName = "raintech-grc-platform",
    [string]$Owner = "",
    [switch]$CreateRepo,
    [switch]$Push,
    [switch]$SeedBacklog
)

$ErrorActionPreference = "Stop"

function Require-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is not installed or not on PATH. Install GitHub CLI, run 'gh auth login', then rerun this script."
    }
}

function Get-RepoFullName {
    $repo = gh repo view --json nameWithOwner --jq ".nameWithOwner" 2>$null
    if (-not $repo) {
        throw "Could not resolve GitHub repository. Create the repo or set the origin remote first."
    }
    return $repo.Trim()
}

Require-Command "git"
Require-Command "gh"

gh auth status | Out-Host

$root = git rev-parse --show-toplevel
Set-Location $root

if ($CreateRepo) {
    $repoArg = $RepoName
    if ($Owner.Trim()) {
        $repoArg = "$Owner/$RepoName"
    }

    $hasOrigin = $false
    try {
        git remote get-url origin *> $null
        $hasOrigin = $true
    } catch {
        $hasOrigin = $false
    }

    if (-not $hasOrigin) {
        gh repo create $repoArg --private --source . --remote origin --description "RainTech local-first CMMC GRC platform"
    }
}

if ($Push) {
    $branch = git branch --show-current
    if (-not $branch) {
        throw "No current branch found. Commit the repository before pushing."
    }
    git push -u origin $branch
}

if ($SeedBacklog) {
    $repoFullName = Get-RepoFullName

    $labelsPath = Join-Path $root ".github/backlog/labels.json"
    $milestonesPath = Join-Path $root ".github/backlog/milestones.json"
    $issuesPath = Join-Path $root ".github/backlog/issues.json"

    $labels = Get-Content -Raw $labelsPath | ConvertFrom-Json
    foreach ($label in $labels) {
        gh label create $label.name --repo $repoFullName --color $label.color --description $label.description --force
    }

    $milestones = Get-Content -Raw $milestonesPath | ConvertFrom-Json
    foreach ($milestone in $milestones) {
        $existing = gh api "repos/$repoFullName/milestones" --jq ".[] | select(.title == `"$($milestone.title)`") | .number" 2>$null
        if (-not $existing) {
            gh api "repos/$repoFullName/milestones" -f title="$($milestone.title)" -f description="$($milestone.description)" | Out-Null
        }
    }

    $issues = Get-Content -Raw $issuesPath | ConvertFrom-Json
    foreach ($issue in $issues) {
        $existingIssue = gh issue list --repo $repoFullName --state all --search "`"$($issue.title)`" in:title" --json title --jq ".[] | select(.title == `"$($issue.title)`") | .title" 2>$null
        if ($existingIssue) {
            Write-Host "Skipping existing issue: $($issue.title)"
            continue
        }

        $tmp = New-TemporaryFile
        Set-Content -LiteralPath $tmp.FullName -Value $issue.body -Encoding UTF8

        $issueArgs = @("issue", "create", "--repo", $repoFullName, "--title", $issue.title, "--body-file", $tmp.FullName)
        if ($issue.milestone) {
            $issueArgs += @("--milestone", $issue.milestone)
        }
        if ($issue.labels -and $issue.labels.Count -gt 0) {
            $issueArgs += @("--label", ($issue.labels -join ","))
        }

        gh @issueArgs
        Remove-Item -LiteralPath $tmp.FullName -Force
    }
}

Write-Host "GitHub bootstrap complete."
