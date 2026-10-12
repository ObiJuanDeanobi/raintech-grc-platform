"""One review-and-issue act and a Profile approved once (GitHub issue #145, ADR 0021).

Two append-only guards are recreated; no row is rewritten and no table changes.

* ``package_review_events_transition_guard``: any prior state may go to
  ``Ready to issue``. Reviewer role, note and component confirmations become
  optional; the reviewer name stays required, and so does the approval text on
  ``Ready to issue``. The earlier ``In Review`` and ``Reviewed`` steps stay
  permitted but nothing writes them any more. The binding
  checks (exact package, source snapshot, template hashes, close decision) are
  unchanged. Packages left at ``In Review`` or ``Reviewed`` by the earlier chain
  keep their rows and read as Draft by derivation.
* ``profile_lifecycle_must_be_ordered``: ``Draft`` may go straight to
  ``Approved``. ``Draft`` to ``Reviewed`` to ``Approved`` stays valid, so a
  version already at ``Reviewed`` can still be approved.

Downgrade restores both earlier triggers exactly. It discards nothing: events
and lifecycle rows written under the new rules stay, and the old guards only
check future inserts.

Revision ID: 0022
Revises: 0021
"""
# ruff: noqa: E501

from collections.abc import Sequence

from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Checks shared by the old and new guard, copied from 0011: sequence and prior
# state continuity, an exact promoted package, and every binding to its source.
_BINDING = """
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
"""

_CONTINUITY = """
      WHEN NEW.sequence != COALESCE((SELECT MAX(sequence)+1 FROM package_review_events
                                      WHERE package_id=NEW.package_id
                                        AND project_id=NEW.project_id), 1)
        OR NEW.prior_state != COALESCE((SELECT next_state FROM package_review_events
                                        WHERE package_id=NEW.package_id
                                          AND project_id=NEW.project_id
                                        ORDER BY sequence DESC LIMIT 1), 'Complete candidate')
"""

_OLD_GUARD = f"""CREATE TRIGGER package_review_events_transition_guard
      BEFORE INSERT ON package_review_events
{_CONTINUITY}        OR NOT ((NEW.prior_state='Complete candidate' AND NEW.next_state='In Review')
             OR (NEW.prior_state='In Review' AND NEW.next_state='Reviewed')
             OR (NEW.prior_state='Reviewed' AND NEW.next_state='Ready to issue'))
{_BINDING}        OR trim(NEW.reviewer_name)='' OR trim(NEW.reviewer_role)='' OR trim(NEW.note)=''
        OR (NEW.next_state IN ('Reviewed','Ready to issue') AND
            (json_extract(NEW.confirmations_json, '$.assessment_report') IS NOT 1
             OR json_extract(NEW.confirmations_json, '$.poam') IS NOT 1
             OR json_extract(NEW.confirmations_json, '$.__source') IS NOT 1))
        OR (NEW.next_state='Ready to issue' AND trim(NEW.approval)='')
      BEGIN SELECT RAISE(ABORT, 'invalid package review transition'); END"""

_NEW_GUARD = f"""CREATE TRIGGER package_review_events_transition_guard
      BEFORE INSERT ON package_review_events
{_CONTINUITY}        OR NOT (NEW.next_state='Ready to issue'
             OR (NEW.prior_state='Complete candidate' AND NEW.next_state='In Review')
             OR (NEW.prior_state='In Review' AND NEW.next_state='Reviewed'))
{_BINDING}        OR trim(NEW.reviewer_name)=''
        OR NOT json_valid(NEW.confirmations_json)
        OR (NEW.next_state='Ready to issue' AND trim(NEW.approval)='')
      BEGIN SELECT RAISE(ABORT, 'invalid package review transition'); END"""

_REVISION_CHECK = """OR (
              NEW.status IN ('Reviewed', 'Approved')
              AND (
                  NEW.content_revision != COALESCE((
                      SELECT revision_token FROM profile_content_changes
                      WHERE profile_version_id = NEW.profile_version_id
                      ORDER BY id DESC LIMIT 1
                  ), '')
                  OR NEW.content_revision != profile_snapshot_revision(
                      NEW.profile_version_id,
                      (
                          SELECT COUNT(*) FROM profile_content_changes
                          WHERE profile_version_id = NEW.profile_version_id
                      )
                  )
              )
          )"""


def _profile_trigger(draft_may_go_to: str, message: str) -> str:
    return f"""CREATE TRIGGER profile_lifecycle_must_be_ordered
        BEFORE INSERT ON profile_lifecycle_events
        WHEN (
            NOT EXISTS (
                SELECT 1 FROM profile_lifecycle_events
                WHERE profile_version_id = NEW.profile_version_id
            ) AND NEW.status != 'Draft'
        ) OR (
            EXISTS (
                SELECT 1 FROM profile_lifecycle_events
                WHERE profile_version_id = NEW.profile_version_id
            ) AND (
                (
                    SELECT status FROM profile_lifecycle_events
                    WHERE profile_version_id = NEW.profile_version_id
                    ORDER BY rowid DESC LIMIT 1
                ) = 'Draft' AND {draft_may_go_to}
            )
        ) OR (
            (
                SELECT status FROM profile_lifecycle_events
                WHERE profile_version_id = NEW.profile_version_id
                ORDER BY rowid DESC LIMIT 1
            ) = 'Reviewed' AND NEW.status != 'Approved'
        ) OR (
            (
                SELECT status FROM profile_lifecycle_events
                WHERE profile_version_id = NEW.profile_version_id
                ORDER BY rowid DESC LIMIT 1
            ) = 'Approved'
        ) OR (NEW.status = 'Approved' AND trim(NEW.reviewer) = '')
          {_REVISION_CHECK}
        BEGIN
            SELECT RAISE(ABORT, '{message}');
        END"""


_OLD_PROFILE = _profile_trigger(
    "NEW.status != 'Reviewed'", "Profile lifecycle must follow Draft to Reviewed to Approved"
)
_NEW_PROFILE = _profile_trigger(
    "NEW.status NOT IN ('Reviewed', 'Approved')",
    "Profile lifecycle must follow Draft to Approved",
)


def _replace(trigger: str, statement: str) -> None:
    op.execute(f"DROP TRIGGER {trigger}")
    op.execute(statement)


def upgrade() -> None:
    _replace("package_review_events_transition_guard", _NEW_GUARD)
    _replace("profile_lifecycle_must_be_ordered", _NEW_PROFILE)


def downgrade() -> None:
    _replace("package_review_events_transition_guard", _OLD_GUARD)
    _replace("profile_lifecycle_must_be_ordered", _OLD_PROFILE)
