---
name: software-delivery-router
description: Repository-scoped router for software delivery work. Use only when the user asks to build, modify, debug, test, review, refactor, deploy, or release software in this repository. Do not invoke for ordinary conversation, general technology questions, conceptual explanations, learning discussions, research or comparisons, brainstorming that does not request implementation, or writing unrelated to repository changes.
---

# Software Delivery Router

Before acting, classify the request into one of four modes.

## CHAT MODE

Use this when the user is:

- Asking for an explanation
- Learning about software engineering
- Discussing technologies
- Comparing tools
- Brainstorming without asking to build
- Asking a general question
- Having unrelated conversation

In Chat Mode:

- Answer normally.
- Do not modify repository files.
- Do not create specifications, tickets, branches, commits, or pull requests.
- Do not invoke the full software-delivery lifecycle.
- Code examples are allowed, but they must not be treated as repository implementation work.

## PLAN MODE

Use this when the user wants to develop or substantially change an application, but the work has not yet been fully specified.

In Plan Mode:

1. Question the user about:
   - Target users
   - The problem being solved
   - The main user workflow
   - MVP scope
   - Non-goals
   - Success criteria
   - Important edge cases
   - Data sensitivity
   - Authentication and authorization
   - Reliability expectations
   - Deployment expectations
2. Use the relevant installed Pocock discovery or grilling skill.
3. Create or update a concise specification.
4. Explain important decisions using:

```text
Decision:
Why:
Alternatives:
Tradeoff:
How difficult it would be to change later:
```

5. Do not implement product code.
6. Obtain explicit user approval before creating the final implementation plan or beginning Build Mode.

The initial specification should normally be concise, approximately one to three pages, unless the project genuinely requires more.

## BUILD MODE

Use this only when the user has approved a specification or has provided a small, clearly defined task with acceptance criteria.

In Build Mode:

1. Work on one approved ticket or vertical slice at a time.
2. Inspect the relevant existing code before changing it.
3. Confirm or establish:
   - The goal
   - Acceptance criteria
   - Likely affected components
   - Tests required
   - Definition of done
4. Use the appropriate installed implementation and testing skills.
5. Make the smallest reasonable change.
6. Do not silently expand scope.
7. Do not introduce major dependencies without approval.
8. Do not change architecture without approval.
9. Run all relevant:
   - Tests
   - Type checks
   - Linters
   - Production builds
10. Update project status after meaningful completed work.

Before declaring the ticket complete, report:

- Ticket or requirement completed
- Files changed
- Tests executed
- Type-check result
- Lint result
- Build result
- Remaining risks
- Recommended next action

## REVIEW MODE

Use this when the user asks to review, validate, test, audit, or challenge existing work.

In Review Mode:

1. Use the installed code-review skill.
2. Compare the implementation against:
   - The specification
   - Ticket acceptance criteria
   - Repository conventions
   - Security expectations
3. Check for:
   - Incorrect behavior
   - Missing edge cases
   - Unnecessary complexity
   - Weak error handling
   - Security problems
   - Missing tests
   - Scope creep
4. Prefer a fresh review context or independent review agent when available.
5. Do not modify code unless the user also requested corrections.

## BUG WORKFLOW

When the user reports a defect:

1. Use the installed debugging or diagnosis skill.
2. Reproduce the issue where possible.
3. Identify the root cause rather than guessing.
4. Add a regression test where practical.
5. Make the smallest correction.
6. Run review and verification before declaring it fixed.

## PROTOTYPE WORKFLOW

When code is created only to investigate an idea:

1. Use the installed prototype skill.
2. Clearly label the work as experimental.
3. Do not treat prototype code as production-ready.
4. Require a specification, tests, and review before prototype code is promoted into the main application.

## AMBIGUOUS REQUESTS

When it is unclear whether the user wants discussion or repository changes:

- Default to Chat Mode.
- Explain the likely implementation approach.
- Do not change files until implementation intent is clear.

## EXPLICIT USER OVERRIDES

The user may explicitly select a mode by saying:

- `chat mode`
- `plan mode`
- `build mode`
- `review mode`

A mode selection applies to the current task, not permanently.

## HUMAN APPROVAL GATES

Require explicit approval before:

- Finalizing a major specification
- Creating the implementation ticket plan
- Beginning implementation for a new application or substantial feature
- Adding a major dependency
- Changing the architecture
- Performing a deployment or release

Do not require excessive approval for tiny, clearly defined corrections.

## TEACHING REQUIREMENT

Teach while working.

Do not explain every line of code. Explain the decisions the user needs in order to control the project:

- Why the architecture was selected
- Where important data lives
- How authentication and authorization work
- How components communicate
- What can fail
- How the system is tested
- How the system is deployed
- What would be difficult to change later

## Installed Skill Routing

- Use `grilling` or `grill-me` for discovery and stress-testing unclear plans.
- Use `to-spec` to synthesize an approved discussion into a specification.
- Use `to-tickets` to break an approved specification into vertical-slice tickets.
- Use `implement` and `tdd` for approved Build Mode work.
- Use `diagnosing-bugs` for reported defects.
- Use `code-review` for Review Mode.
- Use `prototype` only for explicitly experimental work.
- Use `handoff` when another session needs to continue the work.
