from pathlib import Path
from typing import Protocol


class FileStorage(Protocol):
    def save(self, project_id: str, artifact_id: str, filename: str, content: bytes) -> str:
        """Store a file and return its stable relative path."""

    def read(self, relative_path: str) -> bytes:
        """Read bytes previously stored at a stable relative path."""

    def stage(
        self, project_id: str, artifact_id: str, filename: str, content: bytes
    ) -> tuple[str, str]:
        """Write temporary bytes and return temporary and final relative paths."""

    def promote(self, staged_path: str, final_path: str) -> None:
        """Atomically move staged bytes into their final managed path."""

    def delete(self, relative_path: str) -> None:
        """Remove managed bytes if they exist."""


class LocalFileStorage:
    def __init__(self, root: Path) -> None:
        self.root = root

    def save(self, project_id: str, artifact_id: str, filename: str, content: bytes) -> str:
        safe_name = Path(filename).name
        relative = Path(project_id) / f"{artifact_id}-{safe_name}"
        destination = self.root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return relative.as_posix()

    def read(self, relative_path: str) -> bytes:
        return (self.root / relative_path).read_bytes()

    def stage(
        self, project_id: str, artifact_id: str, filename: str, content: bytes
    ) -> tuple[str, str]:
        safe_name = Path(filename).name
        final = Path(project_id) / f"{artifact_id}-{safe_name}"
        staged = Path(".staging") / f"{artifact_id}-{safe_name}"
        destination = self.root / staged
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(content)
        return staged.as_posix(), final.as_posix()

    def promote(self, staged_path: str, final_path: str) -> None:
        source = self.root / staged_path
        destination = self.root / final_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        source.replace(destination)

    def delete(self, relative_path: str) -> None:
        path = self.root / relative_path
        path.unlink(missing_ok=True)
