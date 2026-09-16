"""Add exact recovery-set backup and immutable issuance records."""
# ruff: noqa: E501

from collections.abc import Sequence

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""CREATE TABLE backup_records(
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, assessment_id TEXT NOT NULL,
      package_id TEXT NOT NULL, source_snapshot_id TEXT NOT NULL,
      source_snapshot_sha256 TEXT NOT NULL, package_sha256 TEXT NOT NULL,
      review_event_id TEXT, actor_id TEXT NOT NULL,
      status TEXT NOT NULL CHECK(status IN ('complete','failed')),
      relative_path TEXT NOT NULL, manifest_json TEXT NOT NULL,
      manifest_sha256 TEXT NOT NULL, archive_sha256 TEXT NOT NULL,
      byte_count INTEGER NOT NULL CHECK(byte_count >= 0), started_at TEXT NOT NULL,
      completed_at TEXT NOT NULL, failed_stage TEXT, error TEXT NOT NULL,
      UNIQUE(id, project_id), FOREIGN KEY(project_id) REFERENCES projects(id),
      FOREIGN KEY(assessment_id, project_id) REFERENCES assessment_revisions(assessment_id, project_id),
      FOREIGN KEY(package_id, project_id) REFERENCES generated_packages(id, project_id),
      FOREIGN KEY(source_snapshot_id, project_id) REFERENCES source_snapshots(id, project_id),
      FOREIGN KEY(review_event_id, project_id) REFERENCES package_review_events(id, project_id),
      FOREIGN KEY(actor_id) REFERENCES user_accounts(id)
    )""")
    op.execute("""CREATE TABLE backup_items(
      id TEXT PRIMARY KEY, backup_id TEXT NOT NULL, project_id TEXT NOT NULL,
      relative_path TEXT NOT NULL, source_kind TEXT NOT NULL
        CHECK(source_kind IN ('database','managed','template','metadata')),
      sha256 TEXT NOT NULL, byte_count INTEGER NOT NULL CHECK(byte_count >= 0),
      UNIQUE(backup_id, relative_path),
      FOREIGN KEY(backup_id, project_id) REFERENCES backup_records(id, project_id)
    )""")
    op.execute("""CREATE TABLE issuance_attempts(
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, assessment_id TEXT NOT NULL,
      package_id TEXT NOT NULL, backup_id TEXT, actor_id TEXT NOT NULL,
      status TEXT NOT NULL CHECK(status IN ('issued','failed')),
      started_at TEXT NOT NULL, completed_at TEXT NOT NULL, error TEXT NOT NULL,
      UNIQUE(id, project_id), FOREIGN KEY(project_id) REFERENCES projects(id),
      FOREIGN KEY(assessment_id, project_id) REFERENCES assessment_revisions(assessment_id, project_id),
      FOREIGN KEY(package_id, project_id) REFERENCES generated_packages(id, project_id),
      FOREIGN KEY(backup_id, project_id) REFERENCES backup_records(id, project_id),
      FOREIGN KEY(actor_id) REFERENCES user_accounts(id)
    )""")
    op.execute("""CREATE TABLE issuance_snapshots(
      id TEXT PRIMARY KEY, project_id TEXT NOT NULL, assessment_id TEXT NOT NULL,
      package_id TEXT NOT NULL, attempt_id TEXT NOT NULL, backup_id TEXT NOT NULL,
      source_snapshot_id TEXT NOT NULL, review_event_id TEXT NOT NULL,
      package_sha256 TEXT NOT NULL, source_snapshot_sha256 TEXT NOT NULL,
      backup_manifest_sha256 TEXT NOT NULL, manifest_json TEXT NOT NULL,
      sha256 TEXT NOT NULL, issuer_id TEXT NOT NULL, issued_at TEXT NOT NULL,
      UNIQUE(id, project_id), UNIQUE(project_id, package_id),
      FOREIGN KEY(project_id) REFERENCES projects(id),
      FOREIGN KEY(assessment_id, project_id) REFERENCES assessment_revisions(assessment_id, project_id),
      FOREIGN KEY(package_id, project_id) REFERENCES generated_packages(id, project_id),
      FOREIGN KEY(attempt_id, project_id) REFERENCES issuance_attempts(id, project_id),
      FOREIGN KEY(backup_id, project_id) REFERENCES backup_records(id, project_id),
      FOREIGN KEY(source_snapshot_id, project_id) REFERENCES source_snapshots(id, project_id),
      FOREIGN KEY(review_event_id, project_id) REFERENCES package_review_events(id, project_id),
      FOREIGN KEY(issuer_id) REFERENCES user_accounts(id)
    )""")
    op.execute("""CREATE TRIGGER backup_records_insert_guard BEFORE INSERT ON backup_records
      WHEN (NEW.status='complete' AND NOT EXISTS (SELECT 1 FROM generated_packages p
        JOIN source_snapshots s ON s.id=p.source_snapshot_id AND s.project_id=p.project_id
        JOIN package_review_events r ON r.id=NEW.review_event_id AND r.project_id=p.project_id
        WHERE p.id=NEW.package_id AND p.project_id=NEW.project_id
          AND p.assessment_id=NEW.assessment_id AND s.id=NEW.source_snapshot_id
          AND p.sha256=NEW.package_sha256 AND s.sha256=NEW.source_snapshot_sha256
          AND r.package_id=p.id AND r.next_state='Ready to issue'))
        OR (NEW.status='failed' AND NOT EXISTS (SELECT 1 FROM generated_packages p
          JOIN source_snapshots s ON s.id=p.source_snapshot_id AND s.project_id=p.project_id
          WHERE p.id=NEW.package_id AND p.project_id=NEW.project_id
            AND p.assessment_id=NEW.assessment_id AND s.id=NEW.source_snapshot_id
            AND p.sha256=NEW.package_sha256 AND s.sha256=NEW.source_snapshot_sha256))
        OR (NEW.status='complete' AND (NEW.relative_path='' OR NEW.manifest_sha256=''
          OR NEW.archive_sha256='' OR NEW.byte_count=0 OR NEW.failed_stage IS NOT NULL OR NEW.error!=''))
        OR (NEW.status='failed' AND (NEW.relative_path!='' OR NEW.manifest_json!='{}'
          OR NEW.manifest_sha256!='' OR NEW.archive_sha256!='' OR NEW.byte_count!=0
          OR NEW.failed_stage IS NULL OR trim(NEW.error)=''))
      BEGIN SELECT RAISE(ABORT, 'invalid backup binding'); END""")
    op.execute("""CREATE TRIGGER backup_items_insert_guard BEFORE INSERT ON backup_items
      WHEN (SELECT status FROM backup_records WHERE id=NEW.backup_id
            AND project_id=NEW.project_id) IS NOT 'complete'
      BEGIN SELECT RAISE(ABORT, 'invalid backup item binding'); END""")
    op.execute("""CREATE TRIGGER issuance_attempts_insert_guard BEFORE INSERT ON issuance_attempts
      WHEN NEW.status='issued' AND (NEW.backup_id IS NULL OR NOT EXISTS (
        SELECT 1 FROM backup_records b WHERE b.id=NEW.backup_id
          AND b.project_id=NEW.project_id AND b.package_id=NEW.package_id
          AND b.status='complete'))
      BEGIN SELECT RAISE(ABORT, 'invalid issuance attempt binding'); END""")
    op.execute("""CREATE TRIGGER issuance_snapshots_insert_guard BEFORE INSERT ON issuance_snapshots
      WHEN NOT EXISTS (SELECT 1 FROM generated_packages p
        JOIN source_snapshots s ON s.id=p.source_snapshot_id AND s.project_id=p.project_id
        JOIN package_review_events r ON r.id=NEW.review_event_id AND r.project_id=p.project_id
        JOIN backup_records b ON b.id=NEW.backup_id AND b.project_id=p.project_id
        JOIN issuance_attempts a ON a.id=NEW.attempt_id AND a.project_id=p.project_id
        WHERE p.id=NEW.package_id AND p.project_id=NEW.project_id
          AND p.assessment_id=NEW.assessment_id AND s.id=NEW.source_snapshot_id
          AND r.package_id=p.id AND r.next_state='Ready to issue'
          AND b.package_id=p.id AND b.review_event_id=r.id AND b.status='complete'
          AND a.package_id=p.id AND a.backup_id=b.id AND a.status='issued'
          AND NEW.package_sha256=p.sha256 AND NEW.source_snapshot_sha256=s.sha256
          AND NEW.backup_manifest_sha256=b.manifest_sha256 AND NEW.issuer_id=a.actor_id)
      BEGIN SELECT RAISE(ABORT, 'invalid issuance snapshot binding'); END""")
    for table in ("backup_records", "backup_items", "issuance_attempts", "issuance_snapshots"):
        op.execute(f"""CREATE TRIGGER {table}_immutable_update BEFORE UPDATE ON {table}
          BEGIN SELECT RAISE(ABORT, '{table} are immutable'); END""")
        op.execute(f"""CREATE TRIGGER {table}_immutable_delete BEFORE DELETE ON {table}
          BEGIN SELECT RAISE(ABORT, '{table} are immutable'); END""")


def downgrade() -> None:
    for table in ("issuance_snapshots", "issuance_attempts", "backup_items", "backup_records"):
        op.execute(f"DROP TRIGGER {table}_immutable_delete")
        op.execute(f"DROP TRIGGER {table}_immutable_update")
    op.execute("DROP TRIGGER issuance_snapshots_insert_guard")
    op.execute("DROP TRIGGER issuance_attempts_insert_guard")
    op.execute("DROP TRIGGER backup_items_insert_guard")
    op.execute("DROP TRIGGER backup_records_insert_guard")
    op.execute("DROP TABLE issuance_snapshots")
    op.execute("DROP TABLE issuance_attempts")
    op.execute("DROP TABLE backup_items")
    op.execute("DROP TABLE backup_records")
