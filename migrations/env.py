from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, event, pool

from api.database import register_profile_revision_function

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    event.listen(
        connectable,
        "connect",
        lambda dbapi_connection, _connection_record: register_profile_revision_function(
            dbapi_connection, allow_migration_ledger_bootstrap=True
        ),
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()
        register_profile_revision_function(connection.connection.driver_connection)


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
