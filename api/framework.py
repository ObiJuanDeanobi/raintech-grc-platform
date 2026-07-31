import json
from collections import defaultdict
from hashlib import sha256
from pathlib import Path
from typing import Any

from api.database import Database

FRAMEWORK_ID = "hipaa-45cfr164-2026-07-01"


def _prompt_id(prompt: dict[str, Any], occurrence: int) -> str:
    stable_parts = [
        str(prompt.get(key, ""))
        for key in ("text", "source", "source_detail", "cfr_paragraph", "group")
    ]
    stable_parts.append(str(occurrence))
    return sha256("\0".join(stable_parts).encode()).hexdigest()[:24]


def seed_framework(database: Database, repository_root: Path) -> None:
    catalog_path = repository_root / "catalog" / "versions" / f"{FRAMEWORK_ID}.json"
    prompts_path = repository_root / "catalog" / "versions" / f"{FRAMEWORK_ID}-prompts.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    prompt_layer = json.loads(prompts_path.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = catalog["records"]
    parent_ids = {record["parent_id"] for record in records if record["parent_id"]}
    declarations = {
        "record_shape": {
            "hierarchy": ["standard", "implementation_specification", "paragraph"],
            "determination_rule": "records_without_children",
        },
        "rollup_rule": {
            "precedence": ["Not Met", "Pending"],
            "blank_children_prevent_met": True,
            "satisfied_child_statuses": ["Met", "N/A"],
            "satisfied_rollup_status": "Met",
            "blank_status": "",
        },
        "status_set": ["", "Met", "Not Met", "Pending", "N/A"],
        "designation_rules": {
            "addressable": {
                "dispositions": [
                    "standard_measure",
                    "equivalent_alternative",
                    "non_implementation",
                ],
                "reason_required_for": [
                    "equivalent_alternative",
                    "non_implementation",
                ],
            }
        },
        "presentation_mode": "one_record_with_parent_context",
    }
    with database.connect() as connection:
        connection.execute(
            "INSERT OR IGNORE INTO user_accounts(id, display_name) VALUES (?, ?)",
            ("johnathan", "Johnathan"),
        )
        connection.execute(
            """
            INSERT OR IGNORE INTO framework_versions(
                id, name, record_count, prompt_count, declarations_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (
                FRAMEWORK_ID,
                "HIPAA 45 CFR Part 164",
                len(records),
                prompt_layer["counts"]["prompts_total"],
                json.dumps(declarations),
            ),
        )
        for order, record in enumerate(records):
            connection.execute(
                """
                INSERT OR IGNORE INTO framework_records(
                    framework_version_id, record_id, citation, title, regulation_text,
                    work_area, record_type, parent_id, designation, sort_order,
                    carries_determination
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    FRAMEWORK_ID,
                    record["id"],
                    record["citation"],
                    record["title"],
                    record["text"],
                    record["work_area"],
                    record["record_type"],
                    record["parent_id"],
                    record["designation"],
                    order,
                    int(record["id"] not in parent_ids),
                ),
            )
        occurrences: defaultdict[str, int] = defaultdict(int)
        prompt_order = 0
        for record_id, entry in prompt_layer["entries"].items():
            for prompt in entry["prompts"]:
                fingerprint = "\0".join(
                    str(prompt.get(key, ""))
                    for key in ("text", "source", "source_detail", "cfr_paragraph", "group")
                )
                occurrence = occurrences[fingerprint]
                occurrences[fingerprint] += 1
                connection.execute(
                    """
                    INSERT OR IGNORE INTO framework_prompts(
                        prompt_id, framework_version_id, original_record_id, prompt_text,
                        source, source_detail, cfr_paragraph, group_name, designation,
                        role, role_reason, sort_order
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        _prompt_id(prompt, occurrence),
                        FRAMEWORK_ID,
                        record_id,
                        prompt["text"],
                        prompt["source"],
                        prompt["source_detail"],
                        prompt["cfr_paragraph"],
                        prompt["group"],
                        prompt["designation"],
                        prompt["role"],
                        prompt["role_reason"],
                        prompt_order,
                    ),
                )
                prompt_order += 1
