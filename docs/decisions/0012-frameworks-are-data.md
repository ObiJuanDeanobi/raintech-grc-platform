# ADR 0012 - Frameworks Are Data, Not Code

## Status

Accepted

## Decision

A framework is defined by data, not by application code. Adding one means
writing an ingestion script and declaring four things; it does not mean
changing the assessment workspace.

Declared per framework version:

1. **Record shape.** The hierarchy of assessable units and what may parent
   what. CMMC is requirement to assessment objective. HIPAA is standard to
   implementation specification, with a section-level exception where the rule
   labels no standard.
2. **Rollup rule.** How a parent's status derives from its children, including
   precedence. Currently written as prose in `docs/specification.md`; it
   becomes data.
3. **Status set.** The determinations available, and what each requires. CMMC
   is Blank, Met, Not Met, Pending. HIPAA adds N/A with rationale, and the
   addressable decision required by 45 CFR 164.306(d).
4. **Presentation mode.** Whether the workspace frames a parent with its
   children visible together, or one record at a time. CMMC needs the first,
   HIPAA the second.

**Ingestion stays bespoke per source and is deliberately not generalized.**
eCFR publishes structured XML, the CMMC Assessment Guide is a converted PDF,
and practitioner guidance arrives as a spreadsheet. A framework-agnostic
ingestion engine would be an abstraction over three unlike things. Each
framework gets its own script; the scripts share only the shape of what they
emit.

## Context

Two frameworks are catalogued. Johnathan intends to add more, and wants the
tool to guide him through an unfamiliar framework the way it is being built to
guide him through HIPAA.

That intent is load-bearing rather than aspirational. For a framework he knows
cold, the tool's value is mostly bookkeeping. For one he does not, the guidance
layer *is* the product — the prompts, the expected evidence, the required
versus addressable machinery, the citations. If adding a framework requires
building a workspace, the guidance never arrives cheaply enough to be the
reason to adopt a new framework.

ADR 0009 already shares the evidence, risk, action, recurring-review, audit and
reporting engines while keeping "separate framework catalogs and guided
assessment workflows." That is correct at two frameworks. At five it means five
hand-built workspaces, which is the cost this decision exists to avoid. This
extends 0009; it does not contradict it.

The two catalogs built so far already share a record shape — a stable published
identifier, a citation, an optional parent, text, an optional designation, and
a source — despite the frameworks decomposing differently. That shape survived
contact with both, which is the evidence that it is worth committing to.

The design gate in `docs/agents/tech-debt-gates.md` warns against adding shared
abstraction without a demonstrated second use case. There are now two
implemented and more intended, so the gate is satisfied for the catalog
contract. It is *not* satisfied for ingestion, which is why ingestion is
explicitly excluded.

## Consequences

- Slice 1's data model must treat framework definition as versioned data. This
  is the least reversible decision in the project and is the reason this ADR
  precedes that ticket.
- The rollup rules in `docs/specification.md` become the specification of a
  data structure rather than instructions to a programmer. The specification
  text stays authoritative; the implementation reads it as configuration.
- The two assessment workspaces prototyped for CMMC and HIPAA are two
  presentation modes of one workspace, not two screens. Building them as two
  screens would violate this decision.
- Adding a framework becomes: write an ingester, pin its source, declare the
  four items above, and have the catalog reviewed by a practitioner. No
  application change.
- Framework-specific *workflow* beyond assessment — the HIPAA Security Risk
  Analysis area, CMMC scoring — remains framework-specific, per ADR 0009. This
  decision covers the assessment surface and the catalog, not every engine.

### Where this model does not reach

Stated so the boundary is known before it is discovered:

- **SOC 2** produces an auditor's opinion rather than per-control
  determinations. The record shape fits; the conclusion model does not.
- **PCI DSS** has compensating control worksheets, which are a parallel
  artefact rather than a determination.
- **ISO 27001** has a Statement of Applicability that is a deliverable in its
  own right, not a filter over records.

Frameworks that decompose into a hierarchy of citable requirements carrying a
met-or-not judgement — ISO 27001's controls, NIST CSF, FedRAMP, CJIS, state
RAMPs — fit without strain. The three above would need new workflow, not a new
catalog, and adopting one is a specification change rather than an ingestion
task.

### Open

Which frameworks are actually intended has not been decided. That answer
determines how much of the strain above is theoretical, and it should be
settled before Slice 1 fixes the data model.
