# Working across two agents

Claude and Codex alternate on this repository, usually because one has run out of
usage. Neither can read the other's conversation. Everything below exists to make
that switch uneventful.

This file is portable. The pattern works in any repository where more than one
agent — or more than one person — picks work up cold.

## The failure it prevents

Code is never the problem. Code is in git, and git is unambiguous.

What gets lost is **why**. Why a record is excluded. Why an approach was
abandoned. Which question is currently open and who has to answer it. An agent
that cannot find that reasoning does not stop — it re-derives it, arrives
somewhere different, and is confident about it.

Every expensive mistake in this project so far has had that shape.

## The three buckets

Every durable thing lands in exactly one place. The routing rule matters more
than the format.

| State | Goes to | Test |
|---|---|---|
| **Settled** | `docs/decisions/` | Would reopening it waste a day? |
| **Scoped** | GitHub issue | Is it a unit of work someone could start? |
| **Live but undecided** | `PROJECT_STATUS.md` → Open questions | Is it being actively worked but unresolved? |

The third is the one people skip, and its absence causes the most drift. A
question that is neither settled nor scoped exists nowhere by default — it lives
in the conversation, and the conversation does not survive the switch.

**Conversation is not a bucket.** Anything that exists only in a chat window is
already lost.

## Required at the end of every session

`PROJECT_STATUS.md` must say:

- what phase and mode the project is in
- what the active ticket is
- what is in flight
- what is blocked, and on whom
- what open questions are outstanding, each naming who answers it
- what the next action is

This carries the same weight as tests passing. A session that ends without it
hands the next agent a stale picture that it will act on.

## Branch discipline

Two agents plus long-lived branches is how work gets destroyed.

- **Merge before switching.** Never hand over with unmerged commits stacked on a
  branch.
- **One working branch at a time.**
- **`git log origin/main..HEAD` before any reset or force push.** If it returns
  anything, that work is not on `main` and a reset will discard it.

This is not theoretical. A branch reset in this repository discarded a day of
unmerged work; it was recovered from the local object store, which will not
always be available.

## One rulebook

`AGENTS.md` governs. `CLAUDE.md` is a pointer to it, not a copy — a second copy
is a place for the two to disagree.

Shared skills live in `.agents/skills/` and are deliberately not duplicated into
`.claude/skills/`.

If a rule needs changing, change it in `AGENTS.md` and nowhere else.

## CI is the verification of record

Neither agent's self-report counts. Anything either agent claims to have verified
must be reproducible by the other from the repository alone.

This is what makes the handoff safe rather than trusting. The next agent does not
have to believe the previous one — it can re-run the checks.

Corollaries worth stating:

- Fixtures are committed, and pipelines rebuild them and fail on any difference.
  A fixture that cannot be regenerated is a claim, not a fact.
- Sources are pinned and committed, so verification needs no network and does not
  silently change when an upstream document does.

## Artifacts belong in the repository

Anything generated in a chat — a mockup, a diagram, a report — is invisible to
the other agent. If it informed a decision, commit it. If it did not, it did not
need to exist.

## Adopting this in another repository

Five pieces, in order of how much they matter:

1. `AGENTS.md` as the single rulebook, with a pointer file for each agent that
   reads a different filename.
2. `PROJECT_STATUS.md` as required state, updated at the end of every session.
3. `docs/decisions/` for settled decisions, with the reasoning and evidence.
4. CI that neither agent can talk past.
5. Merge before switching.

The first two get most of the benefit. The rest hardens it.
