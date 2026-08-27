"""Versioned framework-neutral Project Profile and typed evidence targets.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence
from uuid import uuid4

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE projects ADD COLUMN active_profile_version_id TEXT")
    op.execute("ALTER TABLE evidence_artifacts ADD COLUMN uploaded_file_id TEXT")
    op.execute("UPDATE evidence_artifacts SET uploaded_file_id = id")
    op.execute(
        "CREATE UNIQUE INDEX uq_evidence_artifacts_uploaded_file_id "
        "ON evidence_artifacts(uploaded_file_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_evidence_artifacts_project_identity "
        "ON evidence_artifacts(id, project_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_evidence_versions_identity "
        "ON evidence_versions(id, artifact_id, project_id)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_assessments_project_identity "
        "ON assessments(id, project_id)"
    )
    schema = """
        CREATE TABLE profile_versions (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id),
            version_number INTEGER NOT NULL,
            created_by TEXT NOT NULL REFERENCES user_accounts(id),
            created_at TEXT NOT NULL,
            content_revision TEXT NOT NULL,
            revision_valid INTEGER NOT NULL DEFAULT 0 CHECK(revision_valid IN (0, 1)),
            UNIQUE(project_id, version_number),
            UNIQUE(id, project_id)
        );
        CREATE TABLE profile_items (
            id TEXT PRIMARY KEY,
            profile_version_id TEXT NOT NULL REFERENCES profile_versions(id),
            client_key TEXT NOT NULL,
            item_type TEXT NOT NULL CHECK(item_type IN (
                'scope_item', 'environment', 'business_process', 'location',
                'external_service', 'person_role', 'exclusion_constraint',
                'reference', 'unknown_follow_up'
            )),
            environment_item_id TEXT,
            sort_order INTEGER NOT NULL,
            UNIQUE(profile_version_id, client_key),
            UNIQUE(id, profile_version_id),
            CHECK(instr(client_key, ':') = 0),
            CHECK (
                (item_type = 'scope_item' AND environment_item_id IS NOT NULL)
                OR (item_type != 'scope_item' AND environment_item_id IS NULL)
            ),
            FOREIGN KEY(environment_item_id, profile_version_id)
                REFERENCES profile_items(id, profile_version_id)
        );
        CREATE TABLE profile_field_values (
            id TEXT PRIMARY KEY,
            profile_version_id TEXT NOT NULL REFERENCES profile_versions(id),
            profile_item_id TEXT,
            section TEXT NOT NULL,
            field_key TEXT NOT NULL,
            label TEXT NOT NULL,
            value TEXT NOT NULL,
            source TEXT NOT NULL,
            reviewer TEXT NOT NULL,
            last_reviewed_at TEXT NOT NULL,
            sort_order INTEGER NOT NULL,
            CHECK(instr(section, ':') = 0),
            CHECK(instr(field_key, ':') = 0),
            FOREIGN KEY(profile_item_id, profile_version_id)
                REFERENCES profile_items(id, profile_version_id)
        );
        CREATE TABLE profile_lifecycle_events (
            id TEXT PRIMARY KEY,
            profile_version_id TEXT NOT NULL REFERENCES profile_versions(id),
            status TEXT NOT NULL CHECK(status IN ('Draft', 'Reviewed', 'Approved')),
            actor_id TEXT NOT NULL REFERENCES user_accounts(id),
            reviewer TEXT NOT NULL DEFAULT '',
            content_revision TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE profile_content_changes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_version_id TEXT NOT NULL REFERENCES profile_versions(id),
            revision_token TEXT NOT NULL,
            changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(profile_version_id, revision_token)
        );
        CREATE INDEX idx_profile_content_changes_version
            ON profile_content_changes(profile_version_id, id);
        CREATE INDEX idx_profile_versions_project
            ON profile_versions(project_id, version_number);
        CREATE INDEX idx_profile_items_version
            ON profile_items(profile_version_id, sort_order);
        CREATE INDEX idx_profile_values_version
            ON profile_field_values(profile_version_id, sort_order);
        CREATE UNIQUE INDEX uq_profile_top_level_field_identity
            ON profile_field_values(profile_version_id, section, field_key)
            WHERE profile_item_id IS NULL;
        CREATE UNIQUE INDEX uq_profile_item_field_identity
            ON profile_field_values(profile_item_id, field_key)
            WHERE profile_item_id IS NOT NULL;
        CREATE INDEX idx_profile_lifecycle_version
            ON profile_lifecycle_events(profile_version_id, created_at);
    """
    for statement in schema.split(";"):
        if statement.strip():
            op.execute(statement)

    triggers = """
        CREATE TRIGGER profile_versions_cannot_change
        BEFORE UPDATE ON profile_versions
        WHEN NEW.id != OLD.id
          OR NEW.project_id != OLD.project_id
          OR NEW.version_number != OLD.version_number
          OR NEW.created_by != OLD.created_by
          OR NEW.created_at != OLD.created_at
          OR NEW.content_revision != OLD.content_revision
          OR NEW.revision_valid != OLD.revision_valid
          OR COALESCE((
              SELECT status FROM profile_lifecycle_events
              WHERE profile_version_id = OLD.id
              ORDER BY rowid DESC LIMIT 1
          ), '') != 'Draft'
        BEGIN
            SELECT RAISE(ABORT, 'Profile versions are immutable');
        END;
        CREATE TRIGGER profile_versions_cannot_delete
        BEFORE DELETE ON profile_versions
        BEGIN
            SELECT RAISE(ABORT, 'Profile versions are immutable');
        END;
        CREATE TRIGGER profile_items_locked_after_draft_update
        BEFORE UPDATE ON profile_items
        WHEN COALESCE((
            SELECT status FROM profile_lifecycle_events
            WHERE profile_version_id = OLD.profile_version_id
            ORDER BY rowid DESC LIMIT 1
        ), '') != 'Draft' OR COALESCE((
            SELECT status FROM profile_lifecycle_events
            WHERE profile_version_id = NEW.profile_version_id
            ORDER BY rowid DESC LIMIT 1
        ), '') != 'Draft'
        BEGIN
            SELECT RAISE(ABORT, 'Approved or reviewed Profile snapshots are immutable');
        END;
        CREATE TRIGGER profile_items_locked_after_draft_insert
        BEFORE INSERT ON profile_items
        WHEN COALESCE((
            SELECT status FROM profile_lifecycle_events
            WHERE profile_version_id = NEW.profile_version_id
            ORDER BY rowid DESC LIMIT 1
        ), '') != 'Draft'
        BEGIN
            SELECT RAISE(ABORT, 'Approved or reviewed Profile snapshots are immutable');
        END;
        CREATE TRIGGER profile_items_locked_after_draft_delete
        BEFORE DELETE ON profile_items
        WHEN COALESCE((
            SELECT status FROM profile_lifecycle_events
            WHERE profile_version_id = OLD.profile_version_id
            ORDER BY rowid DESC LIMIT 1
        ), '') != 'Draft'
        BEGIN
            SELECT RAISE(ABORT, 'Approved or reviewed Profile snapshots are immutable');
        END;
        CREATE TRIGGER profile_values_locked_after_draft_update
        BEFORE UPDATE ON profile_field_values
        WHEN COALESCE((
            SELECT status FROM profile_lifecycle_events
            WHERE profile_version_id = OLD.profile_version_id
            ORDER BY rowid DESC LIMIT 1
        ), '') != 'Draft' OR COALESCE((
            SELECT status FROM profile_lifecycle_events
            WHERE profile_version_id = NEW.profile_version_id
            ORDER BY rowid DESC LIMIT 1
        ), '') != 'Draft'
        BEGIN
            SELECT RAISE(ABORT, 'Approved or reviewed Profile snapshots are immutable');
        END;
        CREATE TRIGGER profile_values_locked_after_draft_insert
        BEFORE INSERT ON profile_field_values
        WHEN COALESCE((
            SELECT status FROM profile_lifecycle_events
            WHERE profile_version_id = NEW.profile_version_id
            ORDER BY rowid DESC LIMIT 1
        ), '') != 'Draft'
        BEGIN
            SELECT RAISE(ABORT, 'Approved or reviewed Profile snapshots are immutable');
        END;
        CREATE TRIGGER profile_values_locked_after_draft_delete
        BEFORE DELETE ON profile_field_values
        WHEN COALESCE((
            SELECT status FROM profile_lifecycle_events
            WHERE profile_version_id = OLD.profile_version_id
            ORDER BY rowid DESC LIMIT 1
        ), '') != 'Draft'
        BEGIN
            SELECT RAISE(ABORT, 'Approved or reviewed Profile snapshots are immutable');
        END;
        CREATE TRIGGER profile_lifecycle_must_be_ordered
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
                ) = 'Draft' AND NEW.status != 'Reviewed'
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
          OR (
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
          )
        BEGIN
            SELECT RAISE(ABORT, 'Profile lifecycle must follow Draft to Reviewed to Approved');
        END;
        CREATE TRIGGER profile_lifecycle_cannot_change
        BEFORE UPDATE ON profile_lifecycle_events
        BEGIN
            SELECT RAISE(ABORT, 'Profile lifecycle events are append-only');
        END;
        CREATE TRIGGER profile_lifecycle_cannot_delete
        BEFORE DELETE ON profile_lifecycle_events
        BEGIN
            SELECT RAISE(ABORT, 'Profile lifecycle events are append-only');
        END;
        CREATE TRIGGER profile_content_changes_cannot_change
        BEFORE UPDATE ON profile_content_changes
        BEGIN
            SELECT RAISE(ABORT, 'Profile content generation ledger is append-only');
        END;
        CREATE TRIGGER profile_content_changes_cannot_delete
        BEFORE DELETE ON profile_content_changes
        BEGIN
            SELECT RAISE(ABORT, 'Profile content generation ledger is append-only');
        END;
        CREATE TRIGGER profile_content_changes_must_match_snapshot
        BEFORE INSERT ON profile_content_changes
        WHEN NEW.revision_token != profile_snapshot_revision(
            NEW.profile_version_id,
            (
                SELECT COUNT(*) + 1 FROM profile_content_changes
                WHERE profile_version_id = NEW.profile_version_id
            )
        )
        BEGIN
            SELECT RAISE(ABORT, 'Profile revision token must match the current snapshot');
        END;
    """
    for statement in triggers.strip().split("END;"):
        if statement.strip():
            op.execute(f"{statement.strip()} END")
    op.execute(
        """
        CREATE TRIGGER projects_active_profile_must_be_null_on_insert
        BEFORE INSERT ON projects
        WHEN NEW.active_profile_version_id IS NOT NULL
        BEGIN
            SELECT RAISE(ABORT, 'Active Profile version must be NULL before approval');
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER projects_active_profile_must_be_approved
        BEFORE UPDATE OF active_profile_version_id ON projects
        WHEN (
          NOT EXISTS (
              SELECT 1
              FROM profile_lifecycle_events approved_events
              JOIN profile_versions approved_versions
                ON approved_versions.id = approved_events.profile_version_id
              WHERE approved_versions.project_id = NEW.id
                AND approved_events.status = 'Approved'
          ) AND NEW.active_profile_version_id IS NOT NULL
        ) OR (
          EXISTS (
              SELECT 1
              FROM profile_lifecycle_events approved_events
              JOIN profile_versions approved_versions
                ON approved_versions.id = approved_events.profile_version_id
              WHERE approved_versions.project_id = NEW.id
                AND approved_events.status = 'Approved'
          ) AND (
            NEW.active_profile_version_id IS NULL OR NOT EXISTS (
            SELECT 1
            FROM profile_versions versions
            WHERE versions.id = NEW.active_profile_version_id
              AND versions.project_id = NEW.id
              AND (
                  SELECT status FROM profile_lifecycle_events events
                  WHERE events.profile_version_id = versions.id
                  ORDER BY events.rowid DESC LIMIT 1
              ) = 'Approved'
              AND versions.id = (
                  SELECT approved_events.profile_version_id
                  FROM profile_lifecycle_events approved_events
                  JOIN profile_versions approved_versions
                    ON approved_versions.id = approved_events.profile_version_id
                  WHERE approved_versions.project_id = NEW.id
                    AND approved_events.status = 'Approved'
                  ORDER BY approved_events.rowid DESC
                  LIMIT 1
              )
            )
          )
        )
        BEGIN
            SELECT RAISE(ABORT, 'Active Profile version must be an approved same-project snapshot');
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER profile_approval_sets_active_version
        AFTER INSERT ON profile_lifecycle_events
        WHEN NEW.status = 'Approved'
        BEGIN
            UPDATE projects
            SET active_profile_version_id = NEW.profile_version_id
            WHERE id = (
                SELECT project_id FROM profile_versions
                WHERE id = NEW.profile_version_id
            );
        END
        """
    )

    connection = op.get_bind()
    projects = connection.exec_driver_sql(
        "SELECT id, name, created_at FROM projects ORDER BY created_at, id"
    ).mappings()
    for project in projects:
        version_id = str(uuid4())
        connection.exec_driver_sql(
            """
            INSERT INTO profile_versions(
                id, project_id, version_number, created_by, created_at, content_revision
            ) VALUES (?, ?, 1, 'johnathan', ?, ?)
            """,
            (version_id, project["id"], project["created_at"], "1"),
        )
        connection.exec_driver_sql(
            """
            INSERT INTO profile_lifecycle_events(
                id, profile_version_id, status, actor_id, reviewer, created_at
            ) VALUES (?, ?, 'Draft', 'johnathan', '', ?)
            """,
            (str(uuid4()), version_id, project["created_at"]),
        )
        connection.exec_driver_sql(
            """
            INSERT INTO profile_field_values(
                id, profile_version_id, profile_item_id, section, field_key, label,
                value, source, reviewer, last_reviewed_at, sort_order
            ) VALUES (?, ?, NULL, 'project_metadata', 'project_name', 'Project name',
                      ?, 'Project creation', 'Johnathan', ?, 0)
            """,
            (str(uuid4()), version_id, project["name"], project["created_at"]),
        )

    op.execute("DROP INDEX idx_mappings_record")
    op.execute("ALTER TABLE evidence_mappings RENAME TO evidence_mappings_legacy")
    op.execute(
        """
        CREATE TABLE evidence_mappings (
            id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(id),
            artifact_id TEXT NOT NULL,
            evidence_version_id TEXT NOT NULL,
            target_type TEXT NOT NULL CHECK(target_type IN ('assessment_record', 'profile')),
            assessment_id TEXT,
            record_id TEXT,
            profile_version_id TEXT,
            target_key TEXT,
            artifact_name_snapshot TEXT,
            uploaded_file_id_snapshot TEXT,
            rationale TEXT NOT NULL,
            review_state TEXT NOT NULL DEFAULT 'Not reviewed',
            created_at TEXT NOT NULL,
            CHECK (
                (
                    target_type = 'assessment_record'
                    AND assessment_id IS NOT NULL AND record_id IS NOT NULL
                    AND profile_version_id IS NULL AND target_key IS NULL
                    AND artifact_name_snapshot IS NULL
                    AND uploaded_file_id_snapshot IS NULL
                ) OR (
                    target_type = 'profile'
                    AND assessment_id IS NULL AND record_id IS NULL
                    AND profile_version_id IS NOT NULL AND target_key IS NOT NULL
                    AND artifact_name_snapshot IS NOT NULL
                    AND uploaded_file_id_snapshot IS NOT NULL
                )
            ),
            FOREIGN KEY(artifact_id, project_id)
                REFERENCES evidence_artifacts(id, project_id),
            FOREIGN KEY(evidence_version_id, artifact_id, project_id)
                REFERENCES evidence_versions(id, artifact_id, project_id),
            FOREIGN KEY(assessment_id, project_id)
                REFERENCES assessments(id, project_id),
            FOREIGN KEY(profile_version_id, project_id)
                REFERENCES profile_versions(id, project_id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO evidence_mappings(
            id, project_id, artifact_id, evidence_version_id, target_type, assessment_id,
            record_id, profile_version_id, target_key, artifact_name_snapshot,
            uploaded_file_id_snapshot, rationale, review_state, created_at
        )
        SELECT legacy.id, assessments.project_id, legacy.artifact_id, versions.id,
               'assessment_record',
               legacy.assessment_id, legacy.record_id, NULL, NULL, NULL, NULL, legacy.rationale,
               legacy.review_state, legacy.created_at
        FROM evidence_mappings_legacy legacy
        JOIN assessments ON assessments.id = legacy.assessment_id
        JOIN evidence_versions versions
          ON versions.artifact_id = legacy.artifact_id AND versions.version_number = 1
        """
    )
    op.execute("DROP TABLE evidence_mappings_legacy")
    op.execute(
        "CREATE UNIQUE INDEX uq_assessment_evidence_mapping "
        "ON evidence_mappings(artifact_id, assessment_id, record_id) "
        "WHERE target_type = 'assessment_record'"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_profile_evidence_mapping "
        "ON evidence_mappings(evidence_version_id, profile_version_id, target_key) "
        "WHERE target_type = 'profile'"
    )
    op.execute(
        "CREATE INDEX idx_mappings_record ON evidence_mappings(assessment_id, record_id)"
    )
    op.execute(
        "CREATE INDEX idx_mappings_profile ON evidence_mappings(profile_version_id, target_key)"
    )
    op.execute(
        """
        CREATE TRIGGER profile_evidence_mappings_locked_after_draft_insert
        BEFORE INSERT ON evidence_mappings
        WHEN NEW.target_type = 'profile' AND (
            COALESCE((
                SELECT status FROM profile_lifecycle_events
                WHERE profile_version_id = NEW.profile_version_id
                ORDER BY rowid DESC LIMIT 1
            ), '') != 'Draft'
            OR NOT EXISTS (
                SELECT 1
                FROM profile_field_values values_row
                LEFT JOIN profile_items items ON items.id = values_row.profile_item_id
                WHERE values_row.profile_version_id = NEW.profile_version_id
                  AND (
                    (
                      values_row.profile_item_id IS NULL
                      AND NEW.target_key =
                        'field:' || values_row.section || ':' || values_row.field_key
                    ) OR (
                      values_row.profile_item_id IS NOT NULL
                      AND NEW.target_key =
                        'item:' || items.client_key || ':' || values_row.field_key
                    )
                  )
            )
        )
        BEGIN
            SELECT RAISE(ABORT, 'Profile mapping target is invalid or immutable');
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER profile_evidence_mappings_locked_after_draft_update
        BEFORE UPDATE ON evidence_mappings
        WHEN (OLD.target_type = 'profile' OR NEW.target_type = 'profile') AND (
            (
                OLD.target_type = 'profile'
                AND COALESCE((
                    SELECT status FROM profile_lifecycle_events
                    WHERE profile_version_id = OLD.profile_version_id
                    ORDER BY rowid DESC LIMIT 1
                ), '') != 'Draft'
            ) OR (
                NEW.target_type = 'profile'
                AND (
                    COALESCE((
                        SELECT status FROM profile_lifecycle_events
                        WHERE profile_version_id = NEW.profile_version_id
                        ORDER BY rowid DESC LIMIT 1
                    ), '') != 'Draft'
                    OR NOT EXISTS (
                        SELECT 1
                        FROM profile_field_values values_row
                        LEFT JOIN profile_items items ON items.id = values_row.profile_item_id
                        WHERE values_row.profile_version_id = NEW.profile_version_id
                          AND (
                            (
                              values_row.profile_item_id IS NULL
                              AND NEW.target_key =
                                'field:' || values_row.section || ':' || values_row.field_key
                            ) OR (
                              values_row.profile_item_id IS NOT NULL
                              AND NEW.target_key =
                                'item:' || items.client_key || ':' || values_row.field_key
                            )
                          )
                    )
                )
            )
        )
        BEGIN
            SELECT RAISE(ABORT, 'Profile mapping target is invalid or immutable');
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER profile_evidence_mappings_locked_after_draft_delete
        BEFORE DELETE ON evidence_mappings
        WHEN OLD.target_type = 'profile' AND COALESCE((
            SELECT status FROM profile_lifecycle_events
            WHERE profile_version_id = OLD.profile_version_id
            ORDER BY rowid DESC LIMIT 1
        ), '') != 'Draft'
        BEGIN
            SELECT RAISE(ABORT, 'Approved or reviewed Profile snapshots are immutable');
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER profile_scope_environment_must_be_environment_insert
        BEFORE INSERT ON profile_items
        WHEN NEW.item_type = 'scope_item' AND NOT EXISTS (
            SELECT 1 FROM profile_items environment
            WHERE environment.id = NEW.environment_item_id
              AND environment.profile_version_id = NEW.profile_version_id
              AND environment.item_type = 'environment'
        )
        BEGIN
            SELECT RAISE(ABORT, 'Scope inventory requires a same-version environment');
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER profile_scope_environment_must_be_environment_update
        BEFORE UPDATE ON profile_items
        WHEN NEW.item_type = 'scope_item' AND NOT EXISTS (
            SELECT 1 FROM profile_items environment
            WHERE environment.id = NEW.environment_item_id
              AND environment.profile_version_id = NEW.profile_version_id
              AND environment.item_type = 'environment'
        )
        BEGIN
            SELECT RAISE(ABORT, 'Scope inventory requires a same-version environment');
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER profile_mapped_field_cannot_delete
        BEFORE DELETE ON profile_field_values
        WHEN EXISTS (
            SELECT 1
            FROM evidence_mappings mappings
            LEFT JOIN profile_items items ON items.id = OLD.profile_item_id
            WHERE mappings.target_type = 'profile'
              AND mappings.profile_version_id = OLD.profile_version_id
              AND mappings.target_key = CASE
                WHEN OLD.profile_item_id IS NULL
                  THEN 'field:' || OLD.section || ':' || OLD.field_key
                ELSE 'item:' || items.client_key || ':' || OLD.field_key
              END
        )
        BEGIN
            SELECT RAISE(ABORT, 'Mapped Profile fields cannot be deleted');
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER profile_mapped_field_identity_cannot_change
        BEFORE UPDATE OF profile_version_id, profile_item_id, section, field_key
        ON profile_field_values
        WHEN EXISTS (
            SELECT 1
            FROM evidence_mappings mappings
            LEFT JOIN profile_items items ON items.id = OLD.profile_item_id
            WHERE mappings.target_type = 'profile'
              AND mappings.profile_version_id = OLD.profile_version_id
              AND mappings.target_key = CASE
                WHEN OLD.profile_item_id IS NULL
                  THEN 'field:' || OLD.section || ':' || OLD.field_key
                ELSE 'item:' || items.client_key || ':' || OLD.field_key
              END
        )
        BEGIN
            SELECT RAISE(ABORT, 'Mapped Profile field identities cannot change');
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER profile_mapped_item_key_cannot_change
        BEFORE UPDATE OF client_key ON profile_items
        WHEN EXISTS (
            SELECT 1 FROM evidence_mappings mappings
            WHERE mappings.target_type = 'profile'
              AND mappings.profile_version_id = OLD.profile_version_id
              AND mappings.target_key LIKE 'item:' || OLD.client_key || ':%'
        )
        BEGIN
            SELECT RAISE(ABORT, 'Mapped Profile item identities cannot change');
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER referenced_environment_cannot_delete
        BEFORE DELETE ON profile_items
        WHEN OLD.item_type = 'environment' AND EXISTS (
            SELECT 1 FROM profile_items inventory
            WHERE inventory.profile_version_id = OLD.profile_version_id
              AND inventory.environment_item_id = OLD.id
        )
        BEGIN
            SELECT RAISE(ABORT, 'Referenced environments cannot be deleted');
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER referenced_environment_cannot_change_identity
        BEFORE UPDATE OF id, profile_version_id, item_type ON profile_items
        WHEN OLD.item_type = 'environment' AND EXISTS (
            SELECT 1 FROM profile_items inventory
            WHERE inventory.profile_version_id = OLD.profile_version_id
              AND inventory.environment_item_id = OLD.id
        ) AND (
            NEW.id != OLD.id
            OR NEW.profile_version_id != OLD.profile_version_id
            OR NEW.item_type != 'environment'
        )
        BEGIN
            SELECT RAISE(ABORT, 'Referenced environment identity cannot change');
        END
        """
    )
    for table, version_expression in (
        ("profile_items", "NEW.profile_version_id"),
        ("profile_field_values", "NEW.profile_version_id"),
    ):
        op.execute(
            f"""
            CREATE TRIGGER {table}_invalidate_revision_insert
            AFTER INSERT ON {table}
            BEGIN
                INSERT INTO profile_content_changes(profile_version_id, revision_token)
                VALUES (
                    {version_expression},
                    profile_snapshot_revision(
                        {version_expression},
                        (
                            SELECT COUNT(*) + 1 FROM profile_content_changes
                            WHERE profile_version_id = {version_expression}
                        )
                    )
                );
            END
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER {table}_invalidate_revision_update
            AFTER UPDATE ON {table}
            BEGIN
                INSERT INTO profile_content_changes(profile_version_id, revision_token)
                VALUES (
                    OLD.profile_version_id,
                    profile_snapshot_revision(
                        OLD.profile_version_id,
                        (
                            SELECT COUNT(*) + 1 FROM profile_content_changes
                            WHERE profile_version_id = OLD.profile_version_id
                        )
                    )
                );
                INSERT INTO profile_content_changes(profile_version_id, revision_token)
                SELECT NEW.profile_version_id, profile_snapshot_revision(
                    NEW.profile_version_id,
                    (
                        SELECT COUNT(*) + 1 FROM profile_content_changes
                        WHERE profile_version_id = NEW.profile_version_id
                    )
                )
                WHERE NEW.profile_version_id != OLD.profile_version_id;
            END
            """
        )
        op.execute(
            f"""
            CREATE TRIGGER {table}_invalidate_revision_delete
            AFTER DELETE ON {table}
            BEGIN
                INSERT INTO profile_content_changes(profile_version_id, revision_token)
                VALUES (
                    OLD.profile_version_id,
                    profile_snapshot_revision(
                        OLD.profile_version_id,
                        (
                            SELECT COUNT(*) + 1 FROM profile_content_changes
                            WHERE profile_version_id = OLD.profile_version_id
                        )
                    )
                );
            END
            """
        )
    op.execute(
        """
        CREATE TRIGGER profile_mapping_invalidate_revision_insert
        AFTER INSERT ON evidence_mappings
        WHEN NEW.target_type = 'profile'
        BEGIN
            INSERT INTO profile_content_changes(profile_version_id, revision_token)
            VALUES (
                NEW.profile_version_id,
                profile_snapshot_revision(
                    NEW.profile_version_id,
                    (
                        SELECT COUNT(*) + 1 FROM profile_content_changes
                        WHERE profile_version_id = NEW.profile_version_id
                    )
                )
            );
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER profile_mapping_invalidate_revision_update
        AFTER UPDATE ON evidence_mappings
        WHEN OLD.target_type = 'profile' OR NEW.target_type = 'profile'
        BEGIN
            INSERT INTO profile_content_changes(profile_version_id, revision_token)
            SELECT OLD.profile_version_id, profile_snapshot_revision(
                OLD.profile_version_id,
                (
                    SELECT COUNT(*) + 1 FROM profile_content_changes
                    WHERE profile_version_id = OLD.profile_version_id
                )
            )
            WHERE OLD.target_type = 'profile';
            INSERT INTO profile_content_changes(profile_version_id, revision_token)
            SELECT NEW.profile_version_id, profile_snapshot_revision(
                NEW.profile_version_id,
                (
                    SELECT COUNT(*) + 1 FROM profile_content_changes
                    WHERE profile_version_id = NEW.profile_version_id
                )
            )
            WHERE NEW.target_type = 'profile'
              AND (
                  OLD.target_type != 'profile'
                  OR NEW.profile_version_id != OLD.profile_version_id
              );
        END
        """
    )
    op.execute(
        """
        CREATE TRIGGER profile_mapping_invalidate_revision_delete
        AFTER DELETE ON evidence_mappings
        WHEN OLD.target_type = 'profile'
        BEGIN
            INSERT INTO profile_content_changes(profile_version_id, revision_token)
            VALUES (
                OLD.profile_version_id,
                profile_snapshot_revision(
                    OLD.profile_version_id,
                    (
                        SELECT COUNT(*) + 1 FROM profile_content_changes
                        WHERE profile_version_id = OLD.profile_version_id
                    )
                )
            );
        END
        """
    )
    op.execute(
        """
        INSERT INTO profile_content_changes(profile_version_id, revision_token)
        SELECT versions.id, profile_snapshot_revision(versions.id, 1)
        FROM profile_versions versions
        WHERE NOT EXISTS (
            SELECT 1 FROM profile_content_changes changes
            WHERE changes.profile_version_id = versions.id
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER profile_mapping_invalidate_revision_delete")
    op.execute("DROP TRIGGER profile_mapping_invalidate_revision_update")
    op.execute("DROP TRIGGER profile_mapping_invalidate_revision_insert")
    for table in ("profile_field_values", "profile_items"):
        op.execute(f"DROP TRIGGER {table}_invalidate_revision_delete")
        op.execute(f"DROP TRIGGER {table}_invalidate_revision_update")
        op.execute(f"DROP TRIGGER {table}_invalidate_revision_insert")
    op.execute("DROP TRIGGER referenced_environment_cannot_change_identity")
    op.execute("DROP TRIGGER referenced_environment_cannot_delete")
    op.execute("DROP TRIGGER profile_mapped_item_key_cannot_change")
    op.execute("DROP TRIGGER profile_mapped_field_identity_cannot_change")
    op.execute("DROP TRIGGER profile_mapped_field_cannot_delete")
    op.execute("DROP TRIGGER profile_scope_environment_must_be_environment_update")
    op.execute("DROP TRIGGER profile_scope_environment_must_be_environment_insert")
    op.execute("DROP TRIGGER profile_evidence_mappings_locked_after_draft_delete")
    op.execute("DROP TRIGGER profile_evidence_mappings_locked_after_draft_update")
    op.execute("DROP TRIGGER profile_evidence_mappings_locked_after_draft_insert")
    op.execute("DROP TRIGGER projects_active_profile_must_be_approved")
    op.execute("DROP TRIGGER projects_active_profile_must_be_null_on_insert")
    op.execute("DROP TRIGGER profile_approval_sets_active_version")
    op.execute("DROP INDEX idx_mappings_profile")
    op.execute("DROP INDEX idx_mappings_record")
    op.execute("DROP INDEX uq_profile_evidence_mapping")
    op.execute("DROP INDEX uq_assessment_evidence_mapping")
    op.execute("ALTER TABLE evidence_mappings RENAME TO evidence_mappings_typed")
    op.execute(
        """
        CREATE TABLE evidence_mappings (
            id TEXT PRIMARY KEY,
            artifact_id TEXT NOT NULL REFERENCES evidence_artifacts(id),
            assessment_id TEXT NOT NULL REFERENCES assessments(id),
            record_id TEXT NOT NULL,
            rationale TEXT NOT NULL,
            created_at TEXT NOT NULL,
            review_state TEXT NOT NULL DEFAULT 'Not reviewed',
            UNIQUE (artifact_id, assessment_id, record_id)
        )
        """
    )
    op.execute(
        """
        INSERT INTO evidence_mappings(
            id, artifact_id, assessment_id, record_id, rationale, created_at, review_state
        )
        SELECT id, artifact_id, assessment_id, record_id, rationale, created_at, review_state
        FROM evidence_mappings_typed
        WHERE target_type = 'assessment_record'
        """
    )
    op.execute("DROP TABLE evidence_mappings_typed")
    op.execute(
        "CREATE INDEX idx_mappings_record ON evidence_mappings(assessment_id, record_id)"
    )

    for trigger in (
        "profile_lifecycle_cannot_delete",
        "profile_lifecycle_cannot_change",
        "profile_lifecycle_must_be_ordered",
        "profile_content_changes_cannot_delete",
        "profile_content_changes_cannot_change",
        "profile_values_locked_after_draft_delete",
        "profile_values_locked_after_draft_insert",
        "profile_values_locked_after_draft_update",
        "profile_items_locked_after_draft_delete",
        "profile_items_locked_after_draft_insert",
        "profile_items_locked_after_draft_update",
        "profile_versions_cannot_delete",
        "profile_versions_cannot_change",
    ):
        op.execute(f"DROP TRIGGER {trigger}")
    for index in (
        "idx_profile_lifecycle_version",
        "idx_profile_content_changes_version",
        "idx_profile_values_version",
        "uq_profile_item_field_identity",
        "uq_profile_top_level_field_identity",
        "idx_profile_items_version",
        "idx_profile_versions_project",
    ):
        op.execute(f"DROP INDEX {index}")
    for table in (
        "profile_lifecycle_events",
        "profile_content_changes",
        "profile_field_values",
        "profile_items",
        "profile_versions",
    ):
        op.execute(f"DROP TABLE {table}")
    op.execute("ALTER TABLE projects DROP COLUMN active_profile_version_id")
    op.execute("DROP INDEX uq_assessments_project_identity")
    op.execute("DROP INDEX uq_evidence_versions_identity")
    op.execute("DROP INDEX uq_evidence_artifacts_project_identity")
    op.execute("DROP INDEX uq_evidence_artifacts_uploaded_file_id")
    op.execute("ALTER TABLE evidence_artifacts DROP COLUMN uploaded_file_id")
