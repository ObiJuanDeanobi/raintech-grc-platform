import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config


class Database:
    def __init__(self, path: Path, managed_storage_root: Path) -> None:
        self.path = path
        self.managed_storage_root = managed_storage_root

    def migrate(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        migrations = Path(__file__).resolve().parents[1] / "migrations"
        config.set_main_option("script_location", str(migrations))
        config.set_main_option("sqlalchemy.url", f"sqlite:///{self.path.as_posix()}")
        config.set_main_option("raintech.managed_storage_root", str(self.managed_storage_root))
        command.upgrade(config, "head")

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
