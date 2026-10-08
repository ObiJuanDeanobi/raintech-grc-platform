"""Build CMMC Level 2 scoring data from the pinned 32 CFR 170.24 and 170.21 text.

The point values are taken from the regulation, not typed in. Requirement IDs
are read from the published lists in 32 CFR 170.24(c)(2)(i)(B). Two IDs are
printed irregularly in the regulation ("IA-L2-3.5.1", "AC.L2- 3.1.19"); they
are normalized to the catalog form and reported in ``discrepancies``.

Usage:
    python catalog/cmmc_scoring.py --out catalog/versions/cmmc-l2-scoring-32cfr170-2024-12-16.json

Standard library only.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from hashlib import sha256
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCES = REPO_ROOT / "catalog" / "sources"
SCORING_SOURCE = "title-32-part-170-section-170.24-2026-10-01.xml"
POAM_SOURCE = "title-32-part-170-section-170.21-2026-10-01.xml"
CATALOG = REPO_ROOT / "catalog" / "versions" / "cmmc-l2-ag-v2.13.json"
SCORING_ID = "cmmc-l2-scoring-32cfr170-2024-12-16"
AMENDMENT_DATE = "2024-12-16"
SNAPSHOT_DATE = "2026-10-01"

ID_RE = re.compile(r"\b([A-Z]{2})[.-]L2-\s?(3\.\d+\.\d+)\b")
PARTIAL = {
    "IA.L2-3.5.3": "32 CFR 170.24(c)(2)(i)(B)(4)(i)",
    "SC.L2-3.13.11": "32 CFR 170.24(c)(2)(i)(B)(4)(ii)",
}
SSP_REQUIREMENT = "CA.L2-3.12.4"


class ScoringError(ValueError):
    """The pinned source no longer reads as expected. Never guessed around."""


def plain_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw))).strip()


def _between(text: str, start: str, end: str) -> str:
    try:
        begin = text.index(start) + len(start)
        return text[begin : text.index(end, begin)]
    except ValueError as error:
        raise ScoringError(f"Source text not found: {start!r} .. {end!r}") from error


def _ids(fragment: str, discrepancies: list[dict[str, str]]) -> list[str]:
    found = []
    for match in ID_RE.finditer(fragment):
        normalized = f"{match.group(1)}.L2-{match.group(2)}"
        if match.group(0) != normalized:
            discrepancies.append(
                {
                    "printed": match.group(0),
                    "normalized": normalized,
                    "note": "Irregular punctuation or spacing in the published regulation text.",
                }
            )
        found.append(normalized)
    return found


def build() -> dict[str, Any]:
    scoring_text = plain_text(SOURCES / SCORING_SOURCE)
    poam_text = plain_text(SOURCES / POAM_SOURCE)
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    requirement_ids = [r["id"] for r in catalog["records"] if r["record_type"] == "requirement"]
    discrepancies: list[dict[str, str]] = []

    five = _between(scoring_text, "five (5) points include:", "( 2 )")
    three = _between(scoring_text, "three (3) points include:", "( 3 )")
    groups = {
        5: (
            _ids(_between(five, "Basic security requirements.", "( ii )"), discrepancies),
            _ids(five.split("Derived security requirements.", 1)[1], discrepancies),
            "32 CFR 170.24(c)(2)(i)(B)(1)",
        ),
        3: (
            _ids(_between(three, "Basic security requirements.", "( ii )"), discrepancies),
            _ids(three.split("Derived security requirements.", 1)[1], discrepancies),
            "32 CFR 170.24(c)(2)(i)(B)(2)",
        ),
    }
    for phrase in (
        "three (3) points are subtracted from the maximum score if MFA is implemented only for remote and privileged users",
        "Five (5) points are subtracted from the maximum score if MFA is not implemented for any users",
        "If encryption is employed, but is not FIPS-validated, three (3) points are subtracted",
        "if encryption is not employed; five (5) points are subtracted",
        "For these, 1 point is subtracted from the maximum score",
        "The maximum score achievable for a Level 2 self-assessment or Level 2 certification assessment is equal to the total number of CMMC Level 2 security requirements",
        "The absence of an up to date SSP at the time of the assessment would result in a finding",
    ):
        if phrase not in scoring_text:
            raise ScoringError(f"Expected 32 CFR 170.24 text not found: {phrase!r}")

    values: dict[str, dict[str, Any]] = {}
    for points, (basic, derived, source) in groups.items():
        for designation, ids in (("basic", basic), ("derived", derived)):
            for requirement_id in ids:
                if requirement_id in values:
                    raise ScoringError(f"{requirement_id} listed twice")
                values[requirement_id] = {
                    "rule": "fixed",
                    "points": points,
                    "designation": designation,
                    "source": source,
                }
    for requirement_id, source in PARTIAL.items():
        values[requirement_id] = {
            "rule": "partial",
            "points_by_implementation": {"partial": 3, "none": 5},
            "designation": "derived",
            "source": source,
        }
    values[SSP_REQUIREMENT] = {
        "rule": "ssp_required",
        "designation": "basic",
        "source": "32 CFR 170.24(c)(2)(i)(B)(5)",
        "note": (
            "No point value is listed. Without an up-to-date SSP the assessment "
            "cannot be completed."
        ),
    }
    unknown = sorted(set(values) - set(requirement_ids))
    if unknown:
        raise ScoringError(f"Regulation lists requirements not in the catalog: {unknown}")
    for requirement_id in requirement_ids:
        values.setdefault(
            requirement_id,
            {
                "rule": "fixed",
                "points": 1,
                "designation": "derived",
                "source": "32 CFR 170.24(c)(2)(i)(B)(3)",
            },
        )

    excluded_text = _between(poam_text, "None of the following security requirements are included in the POA&M:", "(3) Level 3")
    for phrase in (
        "greater than or equal to 0.8",
        "None of the security requirements included in the POA&M have a point value of greater than 1",
        "SC.L2-3.13.11 CUI Encryption may be included on a POA&M if encryption is employed but it is not FIPS-validated",
        "(i) The assessment score divided by the total number of CMMC Level 2 security requirements",
        "(ii) None of the security requirements included in the POA&M",
        "(iii) None of the following security requirements are included in the POA&M",
    ):
        if phrase not in poam_text:
            raise ScoringError(f"Expected 32 CFR 170.21 text not found: {phrase!r}")
    ordered = {requirement_id: values[requirement_id] for requirement_id in requirement_ids}
    scored = [v for v in ordered.values() if v["rule"] != "ssp_required"]
    worst = sum(v.get("points", v.get("points_by_implementation", {}).get("none", 0)) for v in scored)
    return {
        "id": SCORING_ID,
        "authority": "32 CFR 170.24 CMMC Scoring Methodology; 32 CFR 170.21 POA&M requirements",
        "source": {
            "publisher": "eCFR versioner API, Title 32 Part 170",
            "amendment_date": AMENDMENT_DATE,
            "snapshot_date": SNAPSHOT_DATE,
            "files": {
                name: sha256((SOURCES / name).read_bytes()).hexdigest()
                for name in (SCORING_SOURCE, POAM_SOURCE)
            },
        },
        "catalog_content_sha256": catalog["content_sha256"],
        "maximum_score": len(requirement_ids),
        "minimum_score": len(requirement_ids) - worst,
        "requirements": ordered,
        "conditional_poam": {
            "source": "32 CFR 170.21(a)(2)",
            # Each Conditional Level 2 check cites its own paragraph (GitHub issue #141).
            "paragraphs": {
                "minimum_score": "32 CFR 170.21(a)(2)(i)",
                "maximum_points": "32 CFR 170.21(a)(2)(ii)",
                "excluded": "32 CFR 170.21(a)(2)(iii)",
            },
            "minimum_score_ratio": 0.8,
            "maximum_points": 1,
            "exceptions": {
                "SC.L2-3.13.11": {
                    "implementation": "partial",
                    "points": 3,
                    "note": "Encryption employed but not FIPS-validated.",
                }
            },
            "excluded": _ids(excluded_text, discrepancies),
        },
        "discrepancies": discrepancies,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    data = build()
    args.out.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"{args.out}: max {data['maximum_score']}, min {data['minimum_score']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
