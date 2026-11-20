"""Content-addressed internal artifact paths, never client supplied destinations."""

from __future__ import annotations

import hashlib
import re
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select

from .database import Artifact, Database, as_dict


class ArtifactStore:
    def __init__(self, root: Path, database: Database) -> None:
        self.root = root.resolve()
        self.database = database
        self.root.mkdir(parents=True, exist_ok=True)

    def save(
        self, run_id: str, name: str, content: str | bytes, media_type: str, kind: str
    ) -> dict[str, Any]:
        if not re.fullmatch(r"[a-f0-9]{32}", run_id):
            raise ValueError("Invalid internal run identifier")
        if Path(name).name != name or "\\" in name or "/" in name or name in {".", ".."}:
            raise ValueError("Artifact name must be a filename")
        data = content.encode("utf-8") if isinstance(content, str) else content
        if len(data) > 20_000_000:
            raise ValueError("Artifact exceeds the 20 MB limit")
        digest = hashlib.sha256(data).hexdigest()
        artifact_id = hashlib.sha256(f"{run_id}:{name}:{digest}".encode()).hexdigest()[:32]
        relative = f"{run_id}/{artifact_id}"
        destination = self.checked_path(relative, must_exist=False)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.exists():
            temporary = destination.with_suffix(f".{uuid.uuid4().hex}.tmp")
            with temporary.open("xb") as output:
                output.write(data)
            temporary.replace(destination)
        with self.database.sessions.begin() as session:
            row = session.get(Artifact, artifact_id)
            if row is None:
                row = Artifact(
                    id=artifact_id,
                    run_id=run_id,
                    name=name,
                    kind=kind,
                    media_type=media_type,
                    relative_path=relative,
                    size_bytes=len(data),
                    sha256=digest,
                )
                session.add(row)
                session.flush()
            return self.public(row)

    def checked_path(self, relative: str, *, must_exist: bool = True) -> Path:
        candidate = self.root / relative
        resolved = candidate.resolve(strict=must_exist)
        if not resolved.is_relative_to(self.root) or any(
            part.is_symlink()
            for part in [candidate, *candidate.parents]
            if part != self.root.parent
        ):
            raise ValueError("Artifact escapes storage root or contains a symlink")
        if must_exist and not resolved.is_file():
            raise ValueError("Artifact is not a regular file")
        return resolved

    def list(self, run_id: str) -> list[dict[str, Any]]:
        with self.database.sessions() as session:
            return [
                self.public(row)
                for row in session.scalars(select(Artifact).where(Artifact.run_id == run_id))
            ]

    @staticmethod
    def public(row: Artifact) -> dict[str, Any]:
        data = as_dict(row)
        data.pop("relative_path")
        data["download_url"] = f"/api/artifacts/{row.id}/download"
        return data
