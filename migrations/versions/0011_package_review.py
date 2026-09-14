"""Add append-only exact-package review/sign-off lifecycle."""  # noqa: E501
# ruff: noqa: E501

from collections.abc import Sequence

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""CREATE TABLE package_review_events (
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, assessment_id TEXT NOT NULL,
      package_id TEXT NOT NULL, sequence INTEGER NOT NULL,
      prior_state TEXT NOT NULL CHECK(prior_state IN ('Complete candidate','In Review','Reviewed')),
      next_state TEXT NOT NULL CHECK(next_state IN ('In Review','Reviewed','Ready to issue')),
      actor_id TEXT NOT NULL, reviewer_name TEXT NOT NULL, reviewer_role TEXT NOT NULL,
      note TEXT NOT NULL, approval TEXT NOT NULL, confirmations_json TEXT NOT NULL,
      package_sha256 TEXT NOT NULL, source_snapshot_id TEXT NOT NULL,
      source_snapshot_sha256 TEXT NOT NULL, template_version TEXT NOT NULL,
      component_ids_json TEXT NOT NULL, component_hashes_json TEXT NOT NULL,
      template_hashes_json TEXT NOT NULL,
      close_decision_json TEXT NOT NULL,
      created_at TEXT NOT NULL,
      UNIQUE(package_id, sequence), UNIQUE(id, project_id),
      FOREIGN KEY(project_id) REFERENCES projects(id),
      FOREIGN KEY(actor_id) REFERENCES user_accounts(id),
      FOREIGN KEY(assessment_id, project_id) REFERENCES assessment_revisions(assessment_id, project_id),
      FOREIGN KEY(package_id, project_id) REFERENCES generated_packages(id, project_id),
      FOREIGN KEY(source_snapshot_id, project_id) REFERENCES source_snapshots(id, project_id)
    )""")
    op.execute(
        "CREATE INDEX idx_package_review_events_package ON package_review_events(project_id, package_id, sequence)"
    )
    op.execute("""CREATE TRIGGER package_review_events_transition_guard
      BEFORE INSERT ON package_review_events
      WHEN NEW.sequence != COALESCE((SELECT MAX(sequence)+1 FROM package_review_events
                                      WHERE package_id=NEW.package_id
                                        AND project_id=NEW.project_id), 1)
        OR NEW.prior_state != COALESCE((SELECT next_state FROM package_review_events
                                        WHERE package_id=NEW.package_id
                                          AND project_id=NEW.project_id
                                        ORDER BY sequence DESC LIMIT 1), 'Complete candidate')
        OR NOT ((NEW.prior_state='Complete candidate' AND NEW.next_state='In Review')
             OR (NEW.prior_state='In Review' AND NEW.next_state='Reviewed')
             OR (NEW.prior_state='Reviewed' AND NEW.next_state='Ready to issue'))
        OR NOT EXISTS (SELECT 1 FROM generated_packages p
                       WHERE p.id=NEW.package_id AND p.project_id=NEW.project_id
                         AND p.assessment_id=NEW.assessment_id AND p.state='promoted')
        OR NEW.package_sha256 != (SELECT sha256 FROM generated_packages
                                  WHERE id=NEW.package_id AND project_id=NEW.project_id)
        OR NEW.source_snapshot_id != (SELECT source_snapshot_id FROM generated_packages
                                      WHERE id=NEW.package_id AND project_id=NEW.project_id)
        OR NEW.source_snapshot_sha256 != (SELECT sha256 FROM source_snapshots
                                           WHERE id=NEW.source_snapshot_id
                                             AND project_id=NEW.project_id)
        OR NEW.source_snapshot_sha256 IS NOT
           json_extract((SELECT manifest_json FROM generated_packages
                         WHERE id=NEW.package_id AND project_id=NEW.project_id),
                        '$.source_snapshot_sha256')
        OR NEW.template_version != (SELECT template_version FROM generated_packages
                                    WHERE id=NEW.package_id AND project_id=NEW.project_id)
        OR NOT json_valid(NEW.component_ids_json)
        OR NOT json_valid(NEW.component_hashes_json)
        OR NOT json_valid(NEW.template_hashes_json)
        OR NOT json_valid(NEW.close_decision_json)
        OR EXISTS (SELECT 1 FROM generated_components c
                   WHERE c.package_id=NEW.package_id AND c.project_id=NEW.project_id
                     AND (json_extract(NEW.component_ids_json, '$.' || c.kind) IS NOT c.id
                       OR json_extract(NEW.component_hashes_json, '$.' || c.kind) IS NOT c.sha256))
        OR (SELECT COUNT(*) FROM json_each(NEW.component_ids_json)) !=
           (SELECT COUNT(*) FROM generated_components
            WHERE package_id=NEW.package_id AND project_id=NEW.project_id)
        OR (SELECT COUNT(*) FROM json_each(NEW.component_hashes_json)) !=
           (SELECT COUNT(*) FROM generated_components
            WHERE package_id=NEW.package_id AND project_id=NEW.project_id)
        OR json_extract(NEW.template_hashes_json, '$.assessment_report') IS NOT
           json_extract((SELECT manifest_json FROM generated_packages
                         WHERE id=NEW.package_id AND project_id=NEW.project_id),
                        '$.template_hashes.assessment_report')
        OR json_extract(NEW.template_hashes_json, '$.poam') IS NOT
           json_extract((SELECT manifest_json FROM generated_packages
                         WHERE id=NEW.package_id AND project_id=NEW.project_id),
                        '$.template_hashes.poam')
        OR json_extract(NEW.close_decision_json, '$.generation_attempt_id') IS NOT
           (SELECT generation_attempt_id FROM generated_packages
            WHERE id=NEW.package_id AND project_id=NEW.project_id)
        OR json_extract(NEW.close_decision_json, '$.target') IS NOT
           (SELECT target FROM generation_attempts
            WHERE id=(SELECT generation_attempt_id FROM generated_packages
                      WHERE id=NEW.package_id AND project_id=NEW.project_id))
        OR json_extract(NEW.close_decision_json, '$.decision') IS NOT
           json_extract((SELECT source_json FROM source_snapshots
                         WHERE id=NEW.source_snapshot_id AND project_id=NEW.project_id),
                        '$.readiness')
        OR trim(NEW.reviewer_name)='' OR trim(NEW.reviewer_role)='' OR trim(NEW.note)=''
        OR (NEW.next_state IN ('Reviewed','Ready to issue') AND
            (json_extract(NEW.confirmations_json, '$.assessment_report') IS NOT 1
             OR json_extract(NEW.confirmations_json, '$.poam') IS NOT 1
             OR json_extract(NEW.confirmations_json, '$.__source') IS NOT 1))
        OR (NEW.next_state='Ready to issue' AND trim(NEW.approval)='')
      BEGIN SELECT RAISE(ABORT, 'invalid package review transition'); END""")
    op.execute("""CREATE TRIGGER package_review_events_append_only_update BEFORE UPDATE ON package_review_events
      BEGIN SELECT RAISE(ABORT, 'package review events are append-only'); END""")
    op.execute("""CREATE TRIGGER package_review_events_append_only_delete BEFORE DELETE ON package_review_events
      BEGIN SELECT RAISE(ABORT, 'package review events are append-only'); END""")


def downgrade() -> None:
    op.execute("DROP TRIGGER package_review_events_transition_guard")
    op.execute("DROP TRIGGER package_review_events_append_only_delete")
    op.execute("DROP TRIGGER package_review_events_append_only_update")
    op.execute("DROP TABLE package_review_events")
