# CLAUDE.md

This file exists so Claude Code loads the project's working agreement automatically.

It is a **pointer, not a copy**. Every rule has one canonical home. Do not restate
rules here — a second copy is a place for the two to disagree.

## Read before any software delivery work

1. `AGENTS.md` — governs everything. Classify the request as CHAT, PLAN, BUILD, or
   REVIEW before acting, and respect the approval gates.
2. `docs/PROJECT_OPERATING_MODEL.md` — product spine, core data objects, and the
   rules that constrain design: progressive profile, evidence, work queue,
   versioning, vertical slices, tech-debt gates, and verification defaults.
3. `ROADMAP.md` — slice order and V1 boundaries.
4. `docs/specification.md` — the approved specification. Changing it requires
   Johnathan's approval.
5. `docs/decisions/` — accepted decisions and their supersessions. Read these
   before reopening a settled question.
6. `PROJECT_STATUS.md` — current phase, active ticket, and next action.

Prototype work additionally requires `docs/prototypes/v1-ui-prototype-brief.md` and
`docs/prototypes/v1-ui-prototype-review.md`.

## Skills

Shared agent skills live in `.agents/skills/`. Read them from there.

Do not duplicate them into `.claude/skills/`. Both Claude and Codex work in this
repository, and one canonical copy is the point.

## If you read nothing else

These three prevent the damage that is hardest to undo. They are restated from
`AGENTS.md` and `docs/PROJECT_OPERATING_MODEL.md`, which remain authoritative.

- Do not promote prototype code into production. Production is reimplemented from
  a clean branch against the real architecture.
- Do not claim completion without executed verification. Report what you ran, what
  passed, and what you skipped. "It generated successfully" is not a result.
- Do not begin production BUILD work, change architecture, add a major dependency,
  or edit the approved specification without explicit approval.
