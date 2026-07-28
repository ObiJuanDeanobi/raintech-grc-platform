"""Behavior tests for the representative HIPAA prompt-volume sample."""

from __future__ import annotations

import json
import re
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "catalog"))
sys.path.insert(0, str(REPO_ROOT / "catalog" / "spikes"))

from hipaa_prompts import Prompt, route_security_sample  # noqa: E402
from render_prompt_sample import render  # noqa: E402

SAMPLE_PATH = REPO_ROOT / "catalog" / "spikes" / "prompts-sample.json"
CATALOG_PATH = REPO_ROOT / "catalog" / "versions" / "hipaa-45cfr164-2026-07-01.json"
WALKTHROUGH_PATH = REPO_ROOT / "docs" / "catalogs" / "spike-walkthrough-prompts.md"


class SecurityPromptRoutingTest(unittest.TestCase):
    def test_nist_key_activities_route_to_the_determination_record(self):
        prompts = [
            Prompt(
                text=(
                    "Has all ePHI generated, stored, processed, and transmitted "
                    "within the organization been identified?"
                ),
                source="NIST SP 800-66r2",
                group="Identify All ePHI and Relevant Information Systems",
            ),
            Prompt(
                text="Has a risk management program been created with related policies?",
                source="NIST SP 800-66r2",
                group="Implement a Risk Management Program",
            ),
            Prompt(
                text="Is there a formal process in place to address system misuse?",
                source="NIST SP 800-66r2",
                group="Develop and Implement a Sanction Policy",
            ),
            Prompt(
                text="Is there a policy that establishes what reviews will be conducted?",
                source="NIST SP 800-66r2",
                group="Develop and Deploy the Information System Activity Review Process",
            ),
            Prompt(
                text="Who is the assigned security official?",
                source="NIST SP 800-66r2",
                group="Select a Security Official to be Assigned Responsibility for HIPAA Security",
            ),
        ]

        routed = route_security_sample(prompts)

        self.assertEqual(
            [p.text for p in routed["164.308(a)(1)(ii)(A)"]],
            [prompts[0].text],
        )
        self.assertEqual(
            [p.text for p in routed["164.308(a)(1)(ii)(B)"]],
            [prompts[1].text],
        )
        self.assertEqual(
            [p.text for p in routed["164.308(a)(1)(ii)(C)"]],
            [prompts[2].text],
        )
        self.assertEqual(
            [p.text for p in routed["164.308(a)(1)(ii)(D)"]],
            [prompts[3].text],
        )
        self.assertNotIn(prompts[4], [p for rows in routed.values() for p in rows])

    def test_complete_sample_rejects_a_missing_selector(self):
        with self.assertRaisesRegex(ValueError, "matched 0 prompts"):
            route_security_sample([], require_complete=True)

    def test_committed_sample_is_cleaned_and_routed_for_volume_review(self):
        sample = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
        security = {
            entry["record_id"]: entry["prompts"]
            for entry in sample["entries"]
            if entry["record_id"].startswith("164.308(a)(1)")
        }

        self.assertEqual(
            {record_id: len(prompts) for record_id, prompts in security.items()},
            {
                "164.308(a)(1)(i)": 0,
                "164.308(a)(1)(ii)(A)": 5,
                "164.308(a)(1)(ii)(B)": 6,
                "164.308(a)(1)(ii)(C)": 4,
                "164.308(a)(1)(ii)(D)": 7,
            },
        )
        texts = [p["text"] for prompts in security.values() for p in prompts]
        self.assertEqual(len(texts), 22)
        self.assertFalse(
            [text for text in texts if re.search(r"\?\d{1,3}\b", text)],
            "PDF footnote numbers must not remain attached to questions",
        )
        self.assertFalse(
            [
                p
                for prompts in security.values()
                for p in prompts
                if p["group"].startswith(("Select a Security Official", "Assign and Document"))
            ],
            "questions belonging to 164.308(a)(2) must not leak into this family",
        )

    def test_committed_walkthrough_matches_the_sample(self):
        catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        sample = json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))
        walkthrough = WALKTHROUGH_PATH.read_text(encoding="utf-8")

        self.assertEqual(
            walkthrough,
            render(catalog, sample),
        )
        security_parent = walkthrough.split(
            "## 45 CFR 164.308(a)(1)(i)", 1
        )[1].split("---", 1)[0]
        self.assertIn(
            "applicable questions are routed to child determinations",
            security_parent,
        )
        privacy_parent = walkthrough.split("## 45 CFR 164.520(a)", 1)[1].split("---", 1)[0]
        self.assertIn("**Determination** — one for this record", privacy_parent)
        self.assertNotIn("**Derived status**", privacy_parent)


if __name__ == "__main__":
    unittest.main()
