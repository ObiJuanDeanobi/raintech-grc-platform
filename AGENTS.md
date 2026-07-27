# AI Development Workflow

Before acting, classify the request as:

- CHAT
- PLAN
- BUILD
- REVIEW

## CHAT

Use for explanations, learning, brainstorming, research, comparisons, and ordinary conversation.

In CHAT:

- Answer normally.
- Do not modify repository files.
- Do not invoke the full development workflow.

## PLAN

Use for new applications, substantial features, unclear requirements, or architecture work.

In PLAN:

- Invoke the `software-delivery-router`.
- Question assumptions.
- Create or update the specification.
- Do not implement product code.
- Require approval before moving to BUILD.

## BUILD

Use only for approved specifications, approved tickets, or small tasks with clear acceptance criteria.

In BUILD:

- Invoke the `software-delivery-router`.
- Work on one ticket or vertical slice at a time.
- Use the relevant implementation and testing skills.
- Do not claim completion without executed verification.

## REVIEW

Use for review, validation, testing, auditing, and challenging existing work.

In REVIEW:

- Invoke the `software-delivery-router`.
- Use the relevant review skill.
- Compare the implementation against the specification and acceptance criteria.

## Default behavior

When intent is ambiguous, default to CHAT and make no repository changes.

## User overrides

The user may explicitly say:

- `chat mode`
- `plan mode`
- `build mode`
- `review mode`

## Approval gates

Require user approval before:

- Finalizing a major specification
- Creating a ticket plan
- Beginning a new application or substantial feature
- Adding a major dependency
- Changing architecture
- Deploying or releasing

## Completion

Generated code is not proof of completion.

Completion requires applicable tests, type checking, linting, builds, and review results.

## Agent skills

### Issue tracker

Work is tracked in GitHub Issues for `ObiJuanDeanobi/raintech-grc-platform`. See `docs/agents/issue-tracker.md`.

### Triage labels

Use the default Matt Pocock triage labels: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repo. Read `docs/PROJECT_OPERATING_MODEL.md`, `ROADMAP.md`, relevant `docs/decisions/`, and `docs/specification.md` before software delivery work. See `docs/agents/domain.md`.

## UI and workflow review

Review is iterative and visual. Present one representative surface at a time and say which decision it tests. Do not prototype every screen before the interaction model is settled.

Feedback is cumulative unless the user explicitly reverses a decision. When feedback is given:

- Record the decision in the relevant prototype review document or decision record.
- Check whether the same terminology or hierarchy must also change on other surfaces.
- Preserve the established distinctions: Dashboard vs client workspace, Unified Queue vs Client Queue, project completion vs profile completeness, onboarding baseline vs current implementation state, and Overview orientation vs objective-level assessment work.

If a visual element does not help the user make a decision or perform work, question whether it belongs.

## Repository Notes

- Do not modify application source code during workflow setup or planning-only tasks.
- Preserve the local-first CMMC Level 2 direction in `ROADMAP.md`.
- Preserve the progressive profile model: `InitialProfile` is created during V1 intake; `ImplementationProfile` is enriched during gap analysis.
- Prefer vertical slices over disconnected dashboards.
