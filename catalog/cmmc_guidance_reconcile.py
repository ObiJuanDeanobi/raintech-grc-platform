"""Compare the committed CMMC guidance layer with the original worksheet (issue #31).

Run only where the workbook lives; it holds client identifiers and must never
enter Git. Reads only the named per-objective columns, keyed by objective ID,
and prints differences. It writes nothing.

Usage:
  python catalog/cmmc_guidance_reconcile.py WORKBOOK.xlsx [--sheet NAME]
      [--id-column "Objective"] [--type-column "Evidence Type"]
      [--examples-column "Evidence Examples"]
      [--considerations-column "Assessment Considerations"]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LAYER = REPO_ROOT / "catalog/versions/cmmc-l2-ag-v2.13-guidance.json"
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
OBJECTIVE = re.compile(r"(\d+\.\d+\.\d+)\s*\[?([a-z]+)\]?")


def _rows(path: Path, sheet: str | None) -> list[list[str]]:
    with zipfile.ZipFile(path) as book:
        shared = []
        if "xl/sharedStrings.xml" in book.namelist():
            root = ET.fromstring(book.read("xl/sharedStrings.xml"))
            shared = ["".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")) for si in root]
        workbook = ET.fromstring(book.read("xl/workbook.xml"))
        rels = ET.fromstring(book.read("xl/_rels/workbook.xml.rels"))
        targets = {r.get("Id"): r.get("Target") for r in rels}
        sheet_list = workbook.find("m:sheets", NS)
        if sheet_list is None:
            raise ValueError("Workbook has no sheets")
        sheets = {s.get("name"): str(targets[s.get(REL)]) for s in sheet_list}
        name = sheet or next(iter(sheets))
        data = ET.fromstring(book.read("xl/" + sheets[name].lstrip("/").removeprefix("xl/")))
    rows = []
    for row in data.iter(f"{{{NS['m']}}}row"):
        values: dict[int, str] = {}
        for cell in row.iter(f"{{{NS['m']}}}c"):
            column = sum(
                (ord(ch) - 64) * 26**i
                for i, ch in enumerate(reversed(re.sub(r"\d", "", cell.get("r", ""))))
            )
            value = cell.find("m:v", NS)
            inline = cell.find("m:is", NS)
            text = (
                shared[int(value.text)]
                if cell.get("t") == "s" and value is not None and value.text
                else "".join(t.text or "" for t in inline.iter(f"{{{NS['m']}}}t"))
                if inline is not None
                else (value.text or "")
                if value is not None
                else ""
            )
            values[column - 1] = text
        rows.append([values.get(i, "") for i in range(max(values, default=-1) + 1)])
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--sheet")
    parser.add_argument("--id-column", default="Objective")
    parser.add_argument("--type-column", default="Evidence Type")
    parser.add_argument("--examples-column", default="Evidence Examples")
    parser.add_argument("--considerations-column", default="Assessment Considerations")
    args = parser.parse_args()
    if REPO_ROOT in args.workbook.resolve().parents:
        print("Refusing: the workbook must stay outside the repository.", file=sys.stderr)
        return 2
    layer = json.loads(LAYER.read_text(encoding="utf-8"))
    by_nist = {oid.split("-", 1)[1]: oid for oid in layer["objectives"]}
    by_nist.update(
        {oid.split("-", 1)[1]: oid for field in layer["blanks"].values() for oid in field}
    )
    rows = _rows(args.workbook, args.sheet)
    header_index = next(i for i, row in enumerate(rows) if args.id_column in row)
    header = rows[header_index]
    columns = {
        "evidence_type": header.index(args.type_column),
        "evidence_examples": header.index(args.examples_column),
        "assessment_considerations": header.index(args.considerations_column),
    }
    id_column = header.index(args.id_column)
    differences = 0
    seen = set()
    for row in rows[header_index + 1 :]:
        match = OBJECTIVE.search(row[id_column] if id_column < len(row) else "")
        if not match:
            continue  # Scaffold rows carry no objective ID and are never read.
        oid = by_nist.get(match.group(1) + match.group(2))
        if oid is None:
            print(f"UNMAPPED workbook objective {match.group(0)}")
            differences += 1
            continue
        seen.add(oid)
        committed = layer["objectives"].get(oid, {})
        for field, index in columns.items():
            source = (row[index] if index < len(row) else "").strip()
            if source != committed.get(field, ""):
                print(f"DIFF {oid} {field}: workbook={source!r} committed={committed.get(field)!r}")
                differences += 1
    for oid in sorted(set(by_nist.values()) - seen):
        print(f"MISSING from workbook: {oid}")
        differences += 1
    print(f"{differences} difference(s).")
    return 1 if differences else 0


if __name__ == "__main__":
    raise SystemExit(main())
