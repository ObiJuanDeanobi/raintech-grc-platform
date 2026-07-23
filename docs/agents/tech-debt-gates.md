# Tech-Debt and Bloat Gates

Use these checks when creating tickets, reviewing designs, reviewing pull
requests, and closing milestones.

## Ticket Gate

- Why is this required now?
- What is the simplest acceptable implementation?
- What is explicitly deferred?
- Does the ticket introduce a dependency, abstraction, or migration concern?

## Design Gate

- Prefer an explicit CMMC or HIPAA workflow over a premature universal model.
- Add a shared abstraction only for a demonstrated requirement or second real
  use case.
- Keep local-to-hosted preparation to stable IDs and thin persistence
  boundaries.
- Do not build rule designers, plugin systems, background schedulers, or generic
  report builders without an approved current requirement.

## Review Gate

- Does the change stay inside the approved ticket?
- Could a smaller implementation satisfy the acceptance criteria?
- Are new dependencies necessary and ARM64/x64 compatible?
- Is lifecycle, versioning, audit, or scheduling logic duplicated?
- Did deferred work enter the change without approval?
- Is legacy code being copied without validating its behavior and fit?

## Milestone Gate

- Remove dead experimental paths and unused dependencies.
- Review open `tech-debt` issues and their revisit points.
- Confirm V1-late enhancements have not become release blockers.
- Confirm the next slice extends the product spine rather than adding a
  disconnected surface.

## Accepted Debt

Accepted debt requires:

- a GitHub issue labeled `tech-debt`
- the reason it is being accepted
- the operational consequence
- the event or milestone that triggers reconsideration
- an owner

Do not create debt issues for hypothetical future improvements.
