from pathlib import Path
from typing import Protocol


class FileStorage(Protocol):
    def save(self, project_id: str, artifact_id: str, filename: str, content: bytes) -> str:
        """Store a file and return its stable relative path."""


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
