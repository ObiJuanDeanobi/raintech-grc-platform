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
        throw "$Name is not installed or not on PATH."
    }
}

function Get-PlainToken {
    if ($env:GITHUB_TOKEN) {
        return $env:GITHUB_TOKEN
    }

    $secure = Read-Host "Paste a GitHub fine-grained token or classic PAT with repo access" -AsSecureString
    $ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

function Invoke-GitHubApi {
    param(
        [string]$Method,
        [string]$Path,
        [object]$Body = $null
    )

    $uri = "https://api.github.com$Path"
    $params = @{
        Method  = $Method
        Uri     = $uri
        Headers = $script:Headers
    }

    if ($null -ne $Body) {
        $params.ContentType = "application/json"
        $params.Body = ($Body | ConvertTo-Json -Depth 20)
    }

    return Invoke-RestMethod @params
}

function Invoke-GitHubApiOrNull {
    param(
        [string]$Method,
        [string]$Path,
        [object]$Body = $null
    )

    try {
        return Invoke-GitHubApi -Method $Method -Path $Path -Body $Body
    }
    catch {
        if ($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -eq 404) {
            return $null
        }
        throw
    }
}

function Ensure-Origin {
    param([string]$RepoFullName)

    $remoteUrl = "https://github.com/$RepoFullName.git"
    $existing = ""
    try {
        $existing = git remote get-url origin 2>$null
    }
    catch {
        $existing = ""
    }

    if ($existing) {
        if ($existing -ne $remoteUrl) {
            Write-Host "origin already exists: $existing"
            Write-Host "Expected GitHub remote: $remoteUrl"
            Write-Host "Leaving existing remote unchanged."
        }
        return
    }

    git remote add origin $remoteUrl
}

Require-Command "git"

$root = git rev-parse --show-toplevel
Set-Location $root

$token = Get-PlainToken
$script:Headers = @{
    Authorization            = "Bearer $token"
    Accept                   = "application/vnd.github+json"
    "X-GitHub-Api-Version"   = "2022-11-28"
    "User-Agent"             = "raintech-grc-bootstrap"
}

$me = Invoke-GitHubApi -Method "GET" -Path "/user"
if (-not $Owner.Trim()) {
    $Owner = $me.login
}

$repoFullName = "$Owner/$RepoName"

if ($CreateRepo) {
    $repo = Invoke-GitHubApiOrNull -Method "GET" -Path "/repos/$repoFullName"

    if (-not $repo) {
        $body = @{
            name        = $RepoName
            private     = $true
            description = "RainTech local-first CMMC GRC platform"
        }

        if ($Owner -eq $me.login) {
            $repo = Invoke-GitHubApi -Method "POST" -Path "/user/repos" -Body $body
        }
        else {
            $repo = Invoke-GitHubApi -Method "POST" -Path "/orgs/$Owner/repos" -Body $body
        }

        Write-Host "Created private repo: $($repo.full_name)"
    }
    else {
        Write-Host "Repo already exists: $($repo.full_name)"
    }

    Ensure-Origin -RepoFullName $repoFullName
}

if ($Push) {
    $branch = git branch --show-current
    if (-not $branch) {
        throw "No current branch found."
    }

    git push -u origin $branch
}

if ($SeedBacklog) {
    $repo = Invoke-GitHubApiOrNull -Method "GET" -Path "/repos/$repoFullName"
    if (-not $repo) {
        throw "Repository $repoFullName does not exist or token cannot access it."
    }

    $labelsPath = Join-Path $root ".github/backlog/labels.json"
    $milestonesPath = Join-Path $root ".github/backlog/milestones.json"
    $issuesPath = Join-Path $root ".github/backlog/issues.json"

    $labels = Get-Content -Raw $labelsPath | ConvertFrom-Json
    foreach ($label in $labels) {
        $encodedLabel = [uri]::EscapeDataString($label.name)
        $existingLabel = Invoke-GitHubApiOrNull -Method "GET" -Path "/repos/$repoFullName/labels/$encodedLabel"

        $labelBody = @{
            name        = $label.name
            color       = $label.color
            description = $label.description
        }

        if ($existingLabel) {
            Invoke-GitHubApi -Method "PATCH" -Path "/repos/$repoFullName/labels/$encodedLabel" -Body $labelBody | Out-Null
        }
        else {
            Invoke-GitHubApi -Method "POST" -Path "/repos/$repoFullName/labels" -Body $labelBody | Out-Null
        }
    }

    $milestones = Get-Content -Raw $milestonesPath | ConvertFrom-Json
    $existingMilestones = Invoke-GitHubApi -Method "GET" -Path "/repos/$repoFullName/milestones?state=all&per_page=100"
    $milestoneNumbers = @{}

    foreach ($milestone in $milestones) {
        $match = $existingMilestones | Where-Object { $_.title -eq $milestone.title } | Select-Object -First 1
        if (-not $match) {
            $match = Invoke-GitHubApi -Method "POST" -Path "/repos/$repoFullName/milestones" -Body @{
                title       = $milestone.title
                description = $milestone.description
            }
        }
        $milestoneNumbers[$milestone.title] = $match.number
    }

    $issues = Get-Content -Raw $issuesPath | ConvertFrom-Json
    $existingIssues = Invoke-GitHubApi -Method "GET" -Path "/repos/$repoFullName/issues?state=all&per_page=100"

    foreach ($issue in $issues) {
        $existingIssue = $existingIssues | Where-Object { $_.title -eq $issue.title } | Select-Object -First 1
        if ($existingIssue) {
            Write-Host "Skipping existing issue: $($issue.title)"
            continue
        }

        $issueBody = @{
            title  = $issue.title
            body   = $issue.body
            labels = @($issue.labels)
        }

        if ($issue.milestone -and $milestoneNumbers.ContainsKey($issue.milestone)) {
            $issueBody.milestone = $milestoneNumbers[$issue.milestone]
        }

        $created = Invoke-GitHubApi -Method "POST" -Path "/repos/$repoFullName/issues" -Body $issueBody
        Write-Host "Created issue #$($created.number): $($created.title)"
    }
}

Write-Host "GitHub REST bootstrap complete for $repoFullName."
