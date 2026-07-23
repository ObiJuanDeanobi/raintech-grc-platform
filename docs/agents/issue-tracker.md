# Issue Tracker

Issues and implementation tickets for this repo live in GitHub Issues:

`ObiJuanDeanobi/raintech-grc-platform`

## Local Constraints

GitHub CLI is not installed on this work PC. Prefer the GitHub web UI, the repository's REST helper scripts, or available GitHub connector tools when creating or updating issues.

If GitHub CLI becomes available later, standard `gh issue` commands are acceptable from inside this repository.

## When a skill says "publish to the issue tracker"

Create or update a GitHub issue in this repository.

## When a skill says "fetch the relevant ticket"

Read the corresponding GitHub issue, including its body, labels, comments, and acceptance criteria.

## Ticket expectations

Tickets should be vertical slices with:

- outcome
- data objects touched
- acceptance criteria
- verification steps
- screenshots required when UI changes

The original seed backlog was superseded by the fresh-start specification and
is preserved under `legacy/github-bootstrap-v0/backlog/`.

Do not seed or create a replacement implementation backlog until the user
approves `docs/specification.md`. After approval, create tickets as vertical
slices from the current roadmap and acceptance criteria.

Every feature ticket must include the scope and bloat check defined in
`docs/agents/tech-debt-gates.md`. Accepted debt is tracked in GitHub with the
`tech-debt` label, a reason, and a revisit point.
