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

- paragraphs marked `Standard:`
- paragraphs marked `Implementation specification(s)`
- section-level records where a subpart publishes obligations under no
  `Standard:` label at all, which is the Breach Notification Rule's shape

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
