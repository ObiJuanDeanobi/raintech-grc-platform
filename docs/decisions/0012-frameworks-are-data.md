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
   implementation specification, with four paragraph-level exceptions where
   the rule publishes distinct citable obligations under neither label:
   164.412(a), 164.412(b), 164.414(a), and 164.414(b).
2. **Rollup rule.** How a parent's status derives from its children, including
   precedence. Currently written as prose in `docs/specification.md`; it
   becomes data.
3. **Status set.** The determinations available, and what each requires. CMMC
   is Blank, Met, Not Met, Pending. HIPAA adds N/A with rationale, and the
   addressable decision required by 45 CFR 164.306(d).
4. **Presentation mode.** Whether the workspace frames a parent with its
   children visible together, or one record at a time. CMMC needs the first,
   HIPAA the second.

For HIPAA, published subordinate CFR paragraphs beneath an assessable record
are part of the guidance presentation, not additional assessable records. The
workspace presents them beneath the parent as individually cited prompts with
no status or finding of their own. The parent retains its lead regulation text;
the child text is not duplicated into it. The complete official context is the
parent lead plus its nested cited paragraphs. Approved by Johnathan, July 28,
2026.

Privacy Rule entries declare one of three presentation roles:
`assessment_check` for an operative or conditional requirement,
`applicability_note` for exceptions and scope/N/A conditions, and `context` for
structural lead-ins or optional permissions. Only an `assessment_check` renders
a checkbox. None of the roles changes the parent determination or produces a
finding. Approved by Johnathan, July 28, 2026.

Security Rule guidance routes to the determination-bearing record. When a NIST
SP 800-66r2 key activity identifies an implementation specification, its
questions attach to that specification. Genuinely standard-wide questions stay
on the parent as introductory guidance. A parent with implementation
specifications remains a derived rollup without an editable determination.
Approved by Johnathan, July 28, 2026.

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
- A framework's published subordinate guidance can be displayed below an
  assessable record without changing record count or determination shape.
  Presentation must preserve each child's source citation and must not allow a
  child prompt to carry status or produce a finding. Presentation roles control
  whether the child renders as a check, applicability note, or context.
- Guidance attachment follows the framework's determination location. For
  Security Rule records, NIST-labelled implementation-specification questions
  attach to that specification rather than accumulating on the parent standard.
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

### Intended frameworks

Settled by Johnathan, July 2026: **no additional frameworks in V1.** SOC 2 and
possibly PCI DSS are considered for later, with no commitment and no date.

Both are on the strained list above, so the strain is real rather than
hypothetical. What each would actually need, recorded now while the analysis is
cheap and before anyone assumes "it is just another catalog":

- **PCI DSS** fits the record shape well — requirements decompose into
  sub-requirements and testing procedures, close to CMMC's shape. It needs a
  richer status set than met-or-not, and it needs the compensating control
  worksheet, which is a parallel artefact attached to a requirement rather than
  a determination on it.
- **SOC 2** fits the record shape for the Trust Services Criteria and their
  points of focus, but its conclusion model does not fit at all. The opinion is
  formed at report level over a system description, and what gets tested is the
  entity's *own* controls mapped to criteria.

Both therefore want the same thing, and it is the one thing neither CMMC nor
HIPAA needs: **a client-defined control that satisfies a framework record**,
sitting between the published requirement and the determination. HIPAA hints at
it — an addressable specification may be met by "an equivalent alternative
measure" — but nothing in V1 models a client control as an object.

Nothing is built for this now. The one property worth preserving, and it is
already the case in `docs/specification.md`, is that determinations live on an
assessment result that references a catalog record, rather than on the record
itself. That separation is what would later allow a result to reference a
client-defined control without disturbing the catalog. It costs nothing to keep
and would be expensive to reintroduce.

No ticket, no debt issue, no further design. Per the tech-debt gate, debt issues
are not created for hypothetical future work. If either framework is actually
adopted it is a specification change, and this section is the starting point for
that conversation rather than its conclusion.
