# ADR 0011 - Generated Output Language Constraints

## Status

Accepted

## Decision

Generated deliverables, templates, and approved reusable content blocks must not
assert compliance certification or invent regulatory frequencies.

Specifically, generated or template-sourced content must not:

- describe RainTech, this platform, or a client system as "CMMC certified" or
  "HIPAA certified"; organizations are assessed, products are not certified
- state that a practice is required annually, or at any other interval, unless the
  controlling authority actually mandates that frequency
- present evidence reuse across frameworks as proof of framework equivalence
- present a generic readiness or compliance percentage as an assessment conclusion

## Context

These constraints already govern how Johnathan writes and reviews client work. The
platform generates client-facing SSPs, policies, reports, and corrective action
plans from templates and reusable content blocks. A constraint that lives only in
conversation does not survive being encoded into a template, so the first
deliverable produced by the tool could assert a claim its author would never make.

Project completion percentage and profile completeness exist in the workspace as
internal progress indicators. They are not compliance conclusions and do not belong
in client-facing output.

## Consequences

- These constraints become acceptance criteria for the Slice 6 template, policy,
  and report work, not only a writing convention.
- Approved reusable content blocks are reviewed against this ADR before they become
  reusable.
- Recurring review schedules may offer Annual as an option, but generated text must
  not describe an interval as legally required unless it is.
- The approved specification should carry a reference to this ADR in its document
  governance section at the next approved specification update.
