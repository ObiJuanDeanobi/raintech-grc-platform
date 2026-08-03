# Question Working Record Practitioner Test

GitHub issue #49 provides a local practitioner-test version of the HIPAA
assessment workspace. It tests a proposed change to ADR 0012; it does not revise
the approved architecture or specification yet.

## Interaction under test

- Every `assessment_check` prompt is a working record with its own status,
  assessment notes, optional evidence mappings, optional support rationale,
  N/A rationale, and interview or observation note.
- Selecting a question opens that question's working record in the right pane.
- `context` and `applicability_note` prompts remain guidance only. They do not
  carry a status and do not affect a rollup.
- A CFR record with assessment questions derives its status from those question
  records. A parent standard derives its status from its own assessment questions
  and child CFR records.
- CFR records without assessment questions retain the existing directly editable
  record determination.
- The work list shows each CFR record's direct or derived status with a persistent
  text label and stronger color treatment.
- Evidence support rationale is optional for record-level and question-level
  mappings.

## Practitioner decision requested

Test whether this is the correct unit of day-to-day assessment work. In
particular, verify that question selection, question status, question evidence,
guidance-only content, and parent rollups match how a real HIPAA gap assessment
should be performed.

If the interaction is accepted, revise ADR 0012 and the approved specification
before merging the production change. If it is rejected or refined, discard or
adjust the test branch without changing the approved model.
