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


def _determination_record_ids(
    records: list[dict[str, Any]], declarations: dict[str, Any]
) -> set[str]:
    rule = declarations["record_shape"]["determination_rule"]
    if rule == "records_without_children":
        parent_ids = {record["parent_id"] for record in records if record["parent_id"]}
        return {record["id"] for record in records if record["id"] not in parent_ids}
    raise ValueError(f"Unsupported determination rule: {rule}")


def seed_framework(database: Database, repository_root: Path) -> None:
    catalog_path = repository_root / "catalog" / "versions" / f"{FRAMEWORK_ID}.json"
    prompts_path = repository_root / "catalog" / "versions" / f"{FRAMEWORK_ID}-prompts.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    prompt_layer = json.loads(prompts_path.read_text(encoding="utf-8"))
    records: list[dict[str, Any]] = catalog["records"]
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
        "walkthrough_membership": "all_records",
        "sra": {
            "anchor_record_id": "164.308(a)(1)(ii)(A)",
            "work_area": "Security Risk Analysis",
            "scope_targets": [
                {"scope_type": "system", "profile_item_types": ["scope_item"]},
                {"scope_type": "location", "profile_item_types": ["location"]},
                {"scope_type": "vendor", "profile_item_types": ["external_service"]},
                {
                    "scope_type": "flow",
                    "profile_item_types": ["business_process"],
                    "profile_sections": [
                        "flows",
                        "information_flows",
                        "data_flows",
                        "ephi_flows",
                    ],
                },
            ],
            "risk_required_fields": [
                "threat",
                "vulnerability",
                "cia_impact",
                "safeguards",
                "owner",
                "status",
                "reviewed_by",
                "reviewed_at",
            ],
            "acceptance_required_fields": [
                "acceptance_rationale",
                "owner",
                "review_date",
            ],
            "approval_required_bands": ["High", "Critical"],
            "approval_required_fields": ["approver", "approved_at"],
        },
        "profile_readiness": {
            "initial_state": "Intake started",
            "states": [
                "Intake started",
                "Intake complete",
                "Needs follow-up",
                "Profile complete",
            ],
            "transitions": {
                "Intake started": ["Intake complete", "Needs follow-up"],
                "Intake complete": ["Needs follow-up", "Profile complete"],
                "Needs follow-up": ["Intake complete", "Profile complete"],
                "Profile complete": ["Needs follow-up"],
            },
            "assessment_entry": {
                "allowed_states": ["Intake complete", "Profile complete"],
                "blocking_reasons": {
                    "Intake started": (
                        "Complete the initial intake before starting a new assessment."
                    ),
                    "Needs follow-up": (
                        "Resolve the recorded follow-up before starting a new assessment."
                    ),
                },
            },
            "profile_completion": {
                "state": "Profile complete",
                "requires_boundary_acknowledgement": True,
                "boundary_acknowledgement_blocking_reason": (
                    "Acknowledge the local evidence operating boundary."
                ),
                "requires_no_unresolved_required_fields": True,
                "unresolved_required_field_blocking_reason": "Resolve required field: {field}.",
                "unresolved_required_fields_validation_message": (
                    "Profile complete cannot have unresolved required fields"
                ),
                "required_fields": {
                    "reviewed_by": {
                        "validation_message": "Profile complete requires a named reviewer",
                        "blocking_reason": "Record a named reviewer.",
                    },
                    "approval_evidence": {
                        "validation_message": (
                            "Profile complete requires review or approval evidence"
                        ),
                        "blocking_reason": "Record review or approval evidence.",
                    },
                },
            },
            "follow_up_work": {
                "required_states": ["Needs follow-up"],
                "required_when_unresolved_required_fields": True,
                "required_state_validation_messages": {
                    "Needs follow-up": "Needs follow-up requires explicit follow-up work"
                },
                "unresolved_required_fields_validation_message": (
                    "Unknown required fields require explicit follow-up work"
                ),
            },
            "requires_boundary_acknowledgement_before_transition": True,
            "boundary_acknowledgement_validation_message": (
                "Acknowledge the local evidence operating boundary first"
            ),
            "boundary_document": "docs/local-evidence-operating-boundary.md",
        },
        "close_readiness": {
            "fieldwork_ready_for_generation": {
                "final_statuses": ["Met", "Not Met", "N/A"],
                "not_met_status": "Not Met",
                "not_applicable_status": "N/A",
                "validators": [
                    "approved_profile_complete",
                    "determinations_final",
                    "not_met_reconciled",
                    "sra_complete",
                ],
                "informational": ["package", "review", "sign", "backup", "snapshot"],
            }
        },
    }
    determination_record_ids = _determination_record_ids(records, declarations)
    no_prompt_explanations = {
        item["record_id"]: item["reason"] for item in prompt_layer["records_without_prompts"]
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
        connection.execute(
            """
            UPDATE framework_versions
            SET record_count = ?, prompt_count = ?, declarations_json = ?
            WHERE id = ?
            """,
            (
                len(records),
                prompt_layer["counts"]["prompts_total"],
                json.dumps(declarations),
                FRAMEWORK_ID,
            ),
        )
        for order, record in enumerate(records):
            connection.execute(
                """
                INSERT OR IGNORE INTO framework_records(
                    framework_version_id, record_id, citation, title, regulation_text,
                    work_area, record_type, parent_id, designation, sort_order,
                    carries_determination, no_prompt_explanation
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    int(record["id"] in determination_record_ids),
                    no_prompt_explanations.get(record["id"]),
                ),
            )
            connection.execute(
                """
                UPDATE framework_records
                SET no_prompt_explanation = ?, carries_determination = ?
                WHERE framework_version_id = ? AND record_id = ?
                """,
                (
                    no_prompt_explanations.get(record["id"]),
                    int(record["id"] in determination_record_ids),
                    FRAMEWORK_ID,
                    record["id"],
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
