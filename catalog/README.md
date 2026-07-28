# Framework catalogs

Versioned, pinned framework catalogs and the scripts that build them.

This is not application code. There is no database, API, UI, or ORM here, and
none belongs here. The catalog is a fixture that later slices read.

## Layout

```
catalog/
  hipaa_ingest.py   build a catalog from pinned eCFR source XML
  hipaa_export.py   render a catalog as Markdown for practitioner review
  sources/          pinned eCFR XML, committed as provenance
  versions/         the catalogs themselves, one file per pinned version
docs/catalogs/      the readable exports
tests/              structure and count tests
```

## HIPAA — 45 CFR Part 164

Three catalog areas:

| Catalog area | Subpart | Sections |
|---|---|---|
| Security Rule | C | 45 CFR 164.302–164.318 |
| Privacy Rule | E | 45 CFR 164.500–164.535 |
| Breach Notification Rule | D | 45 CFR 164.400–164.414 |

Four work areas over three catalog areas. The Security Risk Analysis is a
workflow surface, not a catalog area — risk analysis is 45 CFR
164.308(a)(1)(ii)(A), a single Required implementation specification inside the
Security Management Process standard, and it is ingested exactly once.

### What becomes a record

Only what the regulation itself labels:

- paragraphs marked `Standard`. Most are named — `Standard: Security management
  process` — but some are bare, where the section heading supplies the subject.
  45 CFR 164.502(a) and all four Breach Notification Rule standards are written
  the bare way; matching only the named form loses all five.
- paragraphs marked `Implementation specification(s)`
- published paragraph records for provisions that carry distinct obligations
  under no standard or implementation-specification label: 45 CFR 164.412(a),
  164.412(b), 164.414(a), and 164.414(b)

**All three rules share one shape** — a standard with its implementation
specifications beneath it. Four published paragraph records are the documented
exception where neither label exists. The catalog contains 194 records and no
whole-section fallback records.

No objective layer is created. 45 CFR Part 164 publishes no such
decomposition, and inventing one would produce assessable records that cannot
be cited. The OCR Audit Protocol's key activities and audit inquiries belong in
the implementation-guidance and expected-evidence fields; they do not carry
determinations.

### Required and Addressable

The Required/Addressable distinction exists **only in the Security Rule**, per
45 CFR 164.306(d). The Privacy Rule uses standards and implementation
specifications more heavily than the Security Rule does but designates none of
them. Modelling the Privacy Rule as standards-only drops most of its assessable
records.

`uses_addressable` is a property of the pinned `framework_version`, never a
hardcoded assumption. The January 2025 Security Rule NPRM would remove the
addressable category and make every implementation specification in 164.308,
.310, .312 and .316 required. If that is finalized, it produces a **new catalog
version**, not a schema migration.

## Rebuilding

The pinned source XML in `sources/` is committed, so a rebuild is
deterministic and offline:

```
python catalog/hipaa_ingest.py \
    --snapshot 2026-07-01 --retrieved 2026-07-27 \
    --out catalog/versions/hipaa-45cfr164-2026-07-01.json

python catalog/hipaa_export.py \
    --catalog catalog/versions/hipaa-45cfr164-2026-07-01.json \
    --out docs/catalogs/hipaa-45cfr164-2026-07-01.md
```

Pass `--no-cache` to fetch from eCFR instead of the pinned source. Do that only
when deliberately creating a **new** version; re-fetching under an existing
version identifier would silently change what a past assessment cited.

CI regenerates the catalog from the pinned source on every push and fails if
the committed file differs.

## Tests

```
python -m unittest discover -s tests -v
```

Standard library only. The tests read the committed fixture and the committed
source XML and make no network calls, so eCFR availability cannot break CI.

They recount from the source rather than trusting the expected numbers, which
is what stops a parser regression from silently dropping records and then
passing because someone updated the expected count to match.

## Independent control: Appendix A

Appendix A to Subpart C is the Security Standards Matrix — HHS's own enumeration
of the standards and implementation specifications in 164.308, .310 and .312,
published inside the regulation. It is **not ingested as records**, because that
would double-count every Security Rule record. It is used as an external control
on the parse instead, and the tests enforce the agreement.

Restricted to the matrix's scope, catalog and matrix agree exactly:

| | Standards | Impl. specs | Required | Addressable |
|---|---:|---:|---:|---:|
| Appendix A | 18 | 36 | 14 | 22 |
| Catalog (164.308/.310/.312) | 18 | 36 | 14 | 22 |

Two things about the matrix are load-bearing and easy to get wrong:

- **It cites a standard by the paragraph that contains it.** Where a standard has
  implementation specifications, the standard sits at 164.308(a)(1)(i) and the
  matrix cites 164.308(a)(1). Comparing raw citations reports six standards as
  missing when none are.
- **It omits the (A) on Workforce Clearance Procedure.** The section text at
  164.308(a)(3)(ii)(B) carries it, and the section text is controlling.

This control earned its place: it caught **45 CFR 164.308(b)(1)** missing from the
catalog. That paragraph is a standard in the matrix, but the section text titles
it without the `Standard:` prefix that every other Security Rule standard carries,
so a label-driven parse cannot see it. It is now promoted with a note recording
Appendix A as the authority.

**There is no equivalent control for the Privacy or Breach Notification Rules.**
The CFR publishes no matrix for either. Those two areas are verified against the
source text and for internal structural consistency, but they have no second
opinion. The HHS OCR Audit Protocol is the candidate — it enumerates provisions by
CFR citation across all three rules — and cross-checking against it is worth doing
before the catalog is relied on for Privacy or Breach work.

## Spot reconciliation sample

Recorded so the check is repeatable rather than asserted. On 2026-07-27 these
six records were compared against text fetched live from eCFR, bypassing the
pinned source. All six matched verbatim.

| Citation | Title |
|---|---|
| 45 CFR 164.308(a)(1)(ii)(A) | Risk analysis |
| 45 CFR 164.308(a)(5)(ii)(C) | Log-in monitoring |
| 45 CFR 164.310(d)(2)(i) | Disposal |
| 45 CFR 164.312(a)(2)(iv) | Encryption and decryption |
| 45 CFR 164.316(b)(2)(iii) | Updates |
| 45 CFR 164.314(a)(2) | Implementation specifications |

The sample deliberately covers all three implementation-specification label
forms — bare header child, inline, and designated header — because each is
parsed by a different branch, and an earlier revision silently dropped records
from two of them.

Practitioner review of the full export is a separate, outstanding step. This
sample checks the parser, not the catalog's fitness for assessment.

## Adding a framework

Do not generalize this into a framework-agnostic ingestion engine. Add the
second framework as its own script and revisit sharing once there is a real
second use case, per the design gate in `docs/agents/tech-debt-gates.md`.
