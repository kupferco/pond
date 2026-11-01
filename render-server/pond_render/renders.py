"""The render catalog: one folder per render in the store, with a meta.json record."""

from __future__ import annotations

import json
import secrets
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone

from .storage import Store

RENDERS_PREFIX = "renders"


def new_render_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{stamp}-{secrets.token_hex(2)}"


def record_key(render_id: str) -> str:
    return f"{RENDERS_PREFIX}/{render_id}/meta.json"


def file_key(render_id: str, name: str) -> str:
    return f"{RENDERS_PREFIX}/{render_id}/{name}"


@dataclass
class RenderRecord:
    id: str
    kind: str  # "cad" | "svg" | "sim"
    created_at: str
    status: str  # "ok" | "error"
    title: str | None = None
    bbox: dict | None = None
    volume_mm3: float | None = None
    solids: int | None = None
    faces: int | None = None
    views: list[str] = field(default_factory=list)
    files: dict[str, str] = field(default_factory=dict)  # file name -> store key
    error: str | None = None
    log: str | None = None
    duration_s: float | None = None
    metrics: dict | None = None  # sim: the runner summary (signals, climb, contacts ...)
    model: str | None = None  # sim: generator name and params
    params: dict | None = None

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2)

    @classmethod
    def from_json(cls, raw: bytes | str) -> "RenderRecord":
        data = json.loads(raw)
        known = {k: data.get(k) for k in cls.__dataclass_fields__ if k in data}
        return cls(**known)

    def summary(self, store: Store) -> dict:
        """What list_renders/get_render report, with links resolved."""
        out = {
            "id": self.id,
            "kind": self.kind,
            "created_at": self.created_at,
            "status": self.status,
            "title": self.title,
        }
        if self.bbox:
            out["bbox_mm"] = self.bbox
        if self.volume_mm3 is not None:
            out["volume_mm3"] = round(self.volume_mm3, 2)
        if self.solids is not None:
            out["solids"] = self.solids
        if self.views:
            out["views"] = self.views
        if self.model:
            out["model"] = self.model
        if self.params:
            out["params"] = self.params
        if self.metrics:
            out["sim"] = self.metrics
        out["files"] = {name: store.url(key) for name, key in self.files.items()}
        if self.error:
            out["error"] = self.error
        return out


def save_record(store: Store, record: RenderRecord) -> None:
    store.put(record_key(record.id), record.to_json().encode(), "application/json")


def load_record(store: Store, render_id: str) -> RenderRecord | None:
    if not render_id or "/" in render_id or ".." in render_id:
        return None
    raw = store.get(record_key(render_id))
    return RenderRecord.from_json(raw) if raw else None


def list_records(store: Store, limit: int = 20) -> list[RenderRecord]:
    ids = store.list_dirs(RENDERS_PREFIX + "/")
    records: list[RenderRecord] = []
    for render_id in sorted(ids, reverse=True)[: max(1, limit)]:
        rec = load_record(store, render_id)
        if rec:
            records.append(rec)
    return records
