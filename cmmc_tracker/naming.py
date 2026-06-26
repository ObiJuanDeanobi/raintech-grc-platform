from __future__ import annotations

import re
from pathlib import Path


INVALID_FILENAME_CHARS = r'<>:"/\|?*'


def sanitize_filename_part(value: str, fallback: str = "Unnamed") -> str:
    value = value or ""
    for char in INVALID_FILENAME_CHARS:
        value = value.replace(char, " ")
    value = re.sub(r"[\x00-\x1f]", " ", value)
    value = re.sub(r"\s+", " ", value).strip(" ._")
    return value or fallback


def normalize_extension(filename_or_ext: str | None) -> str:
    if not filename_or_ext:
        return ""
    suffix = Path(filename_or_ext).suffix
    ext = suffix if suffix else filename_or_ext
    ext = ext.strip()
    if not ext:
        return ""
    if not ext.startswith("."):
        ext = "." + ext
    safe = "".join(char for char in ext if char not in INVALID_FILENAME_CHARS and ord(char) >= 32)
    safe = safe.replace(" ", "")
    return safe if safe.startswith(".") else f".{safe.lstrip('.')}"


def generated_evidence_filename(
    objective_id: str,
    evidence_title: str,
    extension: str | None,
    existing_names: set[str] | None = None,
) -> str:
    existing_names = existing_names if existing_names is not None else set()
    base = f"{sanitize_filename_part(objective_id)}-{sanitize_filename_part(evidence_title, 'Evidence')}"
    ext = normalize_extension(extension)
    candidate = f"{base}{ext}"
    index = 1
    while candidate.lower() in {name.lower() for name in existing_names}:
        candidate = f"{base}-{index:03d}{ext}"
        index += 1
    existing_names.add(candidate)
    return candidate
