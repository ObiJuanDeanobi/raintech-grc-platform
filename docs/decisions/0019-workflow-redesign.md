# ADR 0019: Reshape the workflow layer; keep the engine

## Status

Proposed October 8, 2026. Direction agreed by Johnathan on October 8, 2026
("agreed on all CMMC bits"; HIPAA executive summary to use counts). Becomes
Accepted when Johnathan approves the matching specification amendment.

## Context

On October 6, 2026 Johnathan used the Windows build and called it "really not
usable". Research and a measured walk-through of the build
(`docs/research/2026-10-competitor-ux/`) found that the data model, versioning,
scoring and packaging are sound, and that the problems are in how the work is
done:

- CMMC is worked one assessment objective per page, about 320 page turns.
- Met is refused at the click unless evidence is already mapped.
- Issuing a package takes about ten sign-off acts, two of them for the Profile.
- CMMC can only issue at 110 of 110 Met, so a client with gaps gets no deliverable.
- There is no picture of where an engagement stands.

The specification contradicted itself on the CMMC unit of work (requirement-
centred in V1 Scope, objective-by-objective in the Accepted Interaction Model).
A second research pass checked the proposed redesign against shipping tools
(`docs/research/2026-10-competitor-ux/validation/README.md`); nothing was
contradicted except using RMM/PSA data as assessment answers.

Johnathan also set product direction: consultant first; compliance as a service
is a growth priority (monthly focus, monthly client meeting, client updates on
regulatory change, yearly assessment or report); HIPAA's yearly deliverable
follows his existing report and POA&M template unless there is a good reason to
change it; Halo PSA and NinjaOne integrations are V2; client access is V3.

## Decision

1. **Keep the engine.** Catalogs, objective-level determinations, derived
   requirement status, official scoring, evidence versions and hashes,
   snapshots, immutability, revisions, audit and backup are unchanged.
2. **Requirement-centred assessment.** CMMC is worked from a requirement view
   that shows all of its objectives as rows with a one-click determination each.
   Determinations stay at objective level. A focused one-item interview view
   works over the same data.
3. **Evidence is enforced at issue, not at the click.** Met may be recorded
   without evidence; it is shown as evidence pending. Two scores are shown:
   the verified SPRS score (only Met objectives with current evidence or a
   documented interview or observation) as the headline, and a projected score
   as secondary. Only verified results appear in an issued self-assessment or
   SPRS figure. Expired evidence returns a verified Met to evidence pending
   without changing the determination.
4. **One review-and-issue act.** Drafts can be generated at any time and are
   watermarked DRAFT. Issuing is one act with a checklist that warns rather than
   blocks, records the reviewer, and runs the pre-issuance backup automatically.
   The Profile is approved once.
5. **A CMMC gap-assessment package** can be issued with NOT MET requirements:
   gap report, verified SPRS worksheet, POA&M, draft SSP and evidence index.
   The existing 110-of-110 internal readiness close is kept.
6. **CMMC scoping records**: asset inventory with 32 CFR 170.19 categories, CUI
   inventory, external service providers with inherited responsibilities, and
   32 CFR 170.22 affirmation tracking.
7. **Compliance as a service** becomes a first-class engagement shape: a client
   service year with a monthly focus, monthly meeting records whose focus points
   become tracked work, a regulatory change log showing affected clients and when
   each was told, and the yearly assessment as a reassessment.
8. **HIPAA yearly deliverable** reproduces Johnathan's November 2025 report and
   POA&M template, corrected for the accuracy problems recorded in
   `docs/research/2026-10-competitor-ux/hipaa-report-reference.md`, with counts
   by status instead of compliance percentages, and with added sections for
   business associates, training, incidents, contingency testing, the per-asset
   risk register and changes since the prior year.
9. **Integrations stay out of V1.** In V2, Halo PSA and NinjaOne data may pre-fill
   Profile facts and inventories and attach evidence as unconfirmed suggestions;
   it never becomes an assessment determination. An ADR on external-service-
   provider scope is required before any integration work.

## Consequences

- The specification's Accepted Interaction Model, report lifecycle, CMMC close
  rules, navigation and acceptance criteria change; see the amendment in
  `docs/specification.md`.
- Issues #128–#133 are superseded by tickets cut from the amended specification.
- Verified-score display carries False Claims Act weight: an inflated
  self-assessment is the failure mode (DOJ, MORSECORP settlement, March 2025).
- The frontend workflow is rebuilt against the existing API; schema changes are
  limited to new record types (scoping records, service-year records, change
  log, HIPAA enhancement, vulnerability and site findings).
