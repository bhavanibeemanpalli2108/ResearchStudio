"""Explicit allow-list serializer, avoiding arbitrary checkpoint constructors."""

from __future__ import annotations

import dataclasses
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Interrupt


class CheckpointJSON:
    def _encode(self, value: Any) -> Any:
        if isinstance(value, BaseException):
            # Checkpoint the fact of a failure without reconstructing an
            # arbitrary exception class or persisting secret-bearing messages.
            return {"__rp_type": "error", "name": type(value).__name__}
        if isinstance(value, Interrupt):
            return {"__rp_type": "interrupt", "fields": self._encode(dataclasses.asdict(value))}
        if isinstance(value, tuple):
            return {"__rp_type": "tuple", "items": [self._encode(v) for v in value]}
        if isinstance(value, dict):
            return {str(k): self._encode(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._encode(v) for v in value]
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        raise TypeError(f"Unsupported checkpoint type: {type(value).__name__}")

    def _decode(self, value: Any) -> Any:
        if isinstance(value, list):
            return [self._decode(v) for v in value]
        if isinstance(value, dict):
            if value.get("__rp_type") == "error" and set(value) == {"__rp_type", "name"}:
                return f"Saved task failure: {value['name']}"
            if value.get("__rp_type") == "tuple" and set(value) == {"__rp_type", "items"}:
                return tuple(self._decode(v) for v in value["items"])
            if value.get("__rp_type") == "interrupt" and set(value) == {"__rp_type", "fields"}:
                fields = self._decode(value["fields"])
                allowed = {f.name for f in dataclasses.fields(Interrupt)}
                return Interrupt(**{k: v for k, v in fields.items() if k in allowed})
            return {k: self._decode(v) for k, v in value.items()}
        return value

    def dumps(self, obj: Any) -> bytes:
        return json.dumps(self._encode(obj), ensure_ascii=False, allow_nan=False).encode("utf-8")

    def loads(self, data: bytes) -> Any:
        return self._decode(json.loads(data))

    def dumps_typed(self, obj: Any) -> tuple[str, bytes]:
        return "rp-json-v1", self.dumps(obj)

    def loads_typed(self, data: tuple[str, bytes]) -> Any:
        kind, payload = data
        if kind != "rp-json-v1":
            raise ValueError("Unsupported checkpoint encoding")
        return self.loads(payload)


@contextmanager
def checkpoints(path: Path) -> Iterator[SqliteSaver]:
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), check_same_thread=False, timeout=30)
    connection.execute("PRAGMA journal_mode=WAL")
    try:
        yield SqliteSaver(connection, serde=CheckpointJSON())
    finally:
        connection.close()
