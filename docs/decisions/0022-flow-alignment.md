# ADR 0022: Flow alignment: blockers only when finalizing; progress everywhere else

## Status

Accepted. Approved by Johnathan on October 12, 2026 ("all yes") on all seven decisions
in `docs/research/2026-10-competitor-ux/flow-alignment.md`, section (f). The matching
specification amendment is marked *[Amendment 2026-10, ADR 0022]* in
`docs/specification.md`. ADR 0020 (decision 6 of that list) was confirmed in the same
answer; its status is unchanged.

## Context

After the workflow redesign (ADR 0019) and the one-act issue (ADR 0021), Johnathan
tested the Windows build again and said: "The blockers should only be there when trying
to close the assessment and generate the deliverables." A new CMMC project opened on
SPRS -203, three red FAIL boxes, a "Left before issue" block of grouped counts with
"Show every item", and a step rail that read "Profile not approved" and "323 items left
before issue". A research pass compared how shipped GRC tools structure the whole flow
(`flow-alignment.md`). None keeps a standing blocker panel while someone works; a gate
appears only at the finishing moment, for the item being finished.

## Decision

1. **Progress and next work, not blockers, while working.** The Overview shows
   progress figures that open the matching filtered list: "Profile: 7 facts
   recorded, 2 to follow up" (the neutral Profile form declares no required fields, so
   there is no "N of M"), "4 of 6 decided", "N gaps need a POA&M, M POA&M items
   open", "N Met awaiting evidence", "N Not Met need a corrective action", "N N/A answers need
   a reason", "N records to recheck", and for Deliver "Draft available", "Final v2,
   12 Oct 2026" or "Final v2, new version in progress". It no longer shows "Left before issue" counts, "Show every item",
   "not approved" or an item count. The overview API no longer returns
   `left_before_issue` and no longer runs the close check at all: its figures and
   the lists behind them are built from the Overview's own data, so loading it does
   not re-hash evidence files. The close check (`api/close.fieldwork_ready` and its
   `groups`) is unchanged and is read only by the finalize dialog.
2. **Blockers appear only in the finalize act.** The dialog ("Finalize deliverables")
   has "Fix before finalizing" (the hard gates, grouped, each linked), "Worth a look"
   (warnings), "What will be locked" (Profile version N, the assessment, the documents)
   and the button "Finalize". Hard gates stay enforced exactly as before; drafts stay
   available at all times. The automatic backup, reviewer, date, optional note and
   immutable record are as built in ADR 0021.
3. **The Profile is approved as part of finalizing.** When the current Profile has no
   unknowns, finalizing approves it in the same transaction; unknowns remain a hard
   gate. An optional "Approve now" stays on the Profile, and the readiness pill leaves
   the working toolbar. *This decision is accepted but is not implemented by the first
   ADR 0022 build; another change implements it.* Until then the dialog still lists
   "Profile not approved" as something to fix.
4. **Screen words change; stored states do not.** "Review and issue" becomes
   "Finalize", "Issued versions" become "Final versions", "Superseded" is shown as
   "Replaced", and Reports (tab, page and "Reports and packages") becomes
   "Deliverables". "Reissue" reads "Correct wording (same findings)" and "Reopen"
   reads "Change findings (new version)". Draft, Issued and Superseded remain the
   stored states and what the audit trail records.
5. **The 170.21 checks are "not yet evaluated" until every requirement is decided.**
   The three checks stay on screen as the specification requires, in neutral grey, and
   turn red when every requirement is decided and one actually fails. Refinement
   (approved by the lead under the engineering delegation, pending Johnathan's
   acknowledgement): a check that decided work has already made impossible to pass
   shows red before that, naming the decided item (a decided Not Met on a never-POA&M
   requirement; a decided Not Met worth more than one point, except SC.L2-3.13.11; the
   minimum score when 110 minus the decided Not Met deductions is below 88).
   Evidence-pending Met never fails a check early, and a blank project is all grey.
   The score reads "Not started" until the first decision instead of printing -203.
   No score arithmetic changes. The display flags (`started`, `all_decided`,
   `check_flags`, `hints`) are added by the `/cmmc-score` route outside the score that
   package snapshots hash, so versions finalized before this change can still be
   corrected.
6. **CMMC finalize defaults to the gap-assessment package**, with the 110-of-110
   internal readiness close as an explicit second option ("Final self-assessment (all
   requirements Met)"). This matches ADR 0019 decision 5. It is built separately (#146).
7. **A Clients home and a POA&M view join the navigation**, before more compliance-as-a-
   service features. Both are built separately.

## What this build changes (items 1 to 4 and 10 of the plan)

- Overview progress-only; step rail recast; neutral blank state; label bugs fixed
  (HIPAA "Specifications not decided"; one Profile counts once in the group list);
  Finalize wording; Evidence: "Used by N objectives", a "Requirements with no
  evidence" coverage filter and "Expired" in place of "Stale" (UI words only; the API
  value stays `stale`).
- Not built here: the CMMC package choice (#146), Profile approval inside finalize,
  the POA&M view, the Clients home.

## Consequences

- `docs/specification.md` is amended: the Overview paragraph, Reports and Governance
  (finalize wording and the finalize dialog), the 170.21 and score bullets, the Profile
  approval bullet, CMMC deliverables, Navigation, AC-025 wording and a new AC-028.
- The one decision with a cost: the Overview no longer tells a consultant at a glance
  which gates remain. He learns it by pressing Finalize, which is the point, and the
  dialog lists them with links.
- Tests that asserted the old words and the old Overview counts were rewritten to the
  new behaviour with the same intent; new tests assert that no blocker text appears on
  the Overview of a new CMMC or HIPAA project.
- Evidence: `docs/evidence/issue-flow-a1/`.
