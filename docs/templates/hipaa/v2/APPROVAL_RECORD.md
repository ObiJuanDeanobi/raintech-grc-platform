# HIPAA template approval record — v2

## Release decision

**Status:** Approved for governed use  
**Ticket:** GitHub issue #66  
**Approver:** Johnathan Dean  
**Approval date:** 2026-09-08  
**Decision source:** Johnathan approved the recommended v2 candidates in the
conversation on 2026-09-08 after review against the CMMC L2 Evidence Master and
POA&M workflow.

These are approved reusable templates for the Issue #71 report-generation
critical path. They are not client deliverables and do not certify RainTech or
any client as HIPAA or CMMC compliant.

## Governed artifacts and immutable hashes

| Artifact | Repository path | SHA-256 |
|---|---|---|
| Combined HIPAA assessment report v2 | `docs/templates/hipaa/v2/RainTech_HIPAA_Combined_Assessment_Report_v2.docx` | `EAB1AB025131E6A365F0747D687EDE8D8DCD6774491AC89AC576CF563FB3619B` |
| HIPAA POA&M v2 | `docs/templates/hipaa/v2/RainTech_HIPAA_POAM_v2.xlsx` | `21AB98FE1BAFA926CDA4E3ADC0F7271D4400E166E73A941140A92464CCE571A9` |

Hashes are SHA-256 values calculated from the committed repository bytes on the
approval record date. Any changed bytes require a new immutable template
version and a new approval record.

## Provenance and sanitization gate

The candidates were supplied from the externally maintained, revised candidate
set at:

`C:\Users\johnathan\Documents\Codex\2026-09-07\grc-template-drafts\revised`

Source files:

- `RainTech_HIPAA_Combined_Assessment_Report_Candidate_v2.docx`
- `RainTech_HIPAA_POAM_Candidate_v2.xlsx`

The repository contains only the approved outputs above. Original drafts,
client source files, intermediate derivatives, and inspection artifacts remain
outside Git and were not copied into the repository.

The manual sanitization gate was completed before this approval: the candidates
were reviewed as reusable, client-neutral templates; client names, PHI/ePHI,
CUI, credentials, client identifiers, and client-specific evidence were removed
or excluded. The result is suitable for governed templating, subject to
per-client source validation during generation. This record is the required
manual verification trail under ADR-0016; it does not claim automated DLP or
sanitization enforcement.

## Validation performed

- DOCX and XLSX package integrity validated as readable ZIP packages.
- SHA-256 hashes recorded above.
- Workbook inspection confirmed the candidate is the approved CMMC-shaped
  operational POA&M artifact; the source inspection output was not committed.
- The report and POA&M were reviewed for ADR-0011 language constraints:
  no certification claim, no invented regulatory frequency, no generic
  compliance percentage, and no false cross-framework equivalence.
- Final Word/PDF rendering remains a client-facing generation QA step for Issue
  #71; this approval does not approve an individual client issuance.

## Workflow conventions

The approved pair follows the familiar CMMC L2 operating rhythm while retaining
HIPAA-specific substance:

`scope/profile → requirement → evidence → determination → finding → POA&M/action → validation → report/review`

- `Control Group` is derived from the pinned HIPAA work area: Security,
  Privacy, or Breach Notification.
- `Validation Owner` is a governed platform actor ID rendered as a display name;
  it is not a free-text substitute for accountable ownership.
- Requirement-level results retain determination, implementation statement,
  evidence, finding, risk, and POA&M linkage.
- An open corrective action does not erase the underlying Not Met determination;
  closure requires governed validation.
- The SRA remains a distinct HIPAA requirement. CMMC-shaped layout and workflow
  do not imply HIPAA/CMMC equivalence or create a HIPAA score.
- The platform remains authoritative; exported DOCX/XLSX files are governed
  artifacts produced from a specific immutable template version.

## Traceability

- ADR-0011 — Generated Output Language Constraints
- ADR-0016 — Sanitized Template Provenance
- Issue #66 — Human-gated sanitized template approval
- Issue #71 — HIPAA report and POA&M generation critical path
