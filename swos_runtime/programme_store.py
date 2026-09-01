"""SQLite persistence for scoped Research Programme Memory v2."""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

from .models import canonical_digest, canonical_json, utc_timestamp


class StoreIntegrityError(RuntimeError):
    """Raised when the append-only event chain or projection is invalid."""


class StoreLockTimeout(RuntimeError):
    """Raised when SQLite cannot acquire the bounded write lock."""


class _ClosingConnection(sqlite3.Connection):
    """Close connections after the standard SQLite context-manager commit."""

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            return super().__exit__(exc_type, exc_value, traceback)
        finally:
            self.close()


@dataclass(frozen=True)
class StorePreflight:
    ok: bool
    path: str
    reasons: tuple[str, ...] = ()


class ProgrammeStore:
    """A local SQLite store with explicit migrations and rebuildable views."""

    SCHEMA_VERSION = "2.0.0"

    def __init__(self, path: str | Path, *, lock_timeout_seconds: float = 2.0) -> None:
        self.path = Path(path)
        self.lock_timeout_seconds = lock_timeout_seconds
        if lock_timeout_seconds <= 0:
            raise ValueError("lock timeout must be positive")

    def preflight(self) -> StorePreflight:
        reasons: list[str] = []
        parent = self.path.parent
        if not parent.exists():
            reasons.append("database parent does not exist")
        elif not os.access(parent, os.W_OK):
            reasons.append("database parent is not writable")
        if self.path.exists() and not os.access(self.path, os.R_OK | os.W_OK):
            reasons.append("database is not readable and writable")
        return StorePreflight(not reasons, str(self.path), tuple(reasons))

    def initialize(self) -> None:
        preflight = self.preflight()
        if not preflight.ok:
            raise OSError("; ".join(preflight.reasons))
        with self._connect() as connection:
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = WAL")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS schema_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS programme_state (
                    namespace_id TEXT NOT NULL,
                    programme_id TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'active',
                    PRIMARY KEY (namespace_id, programme_id)
                );
                CREATE TABLE IF NOT EXISTS bindings (
                    binding_id TEXT PRIMARY KEY,
                    namespace_id TEXT NOT NULL,
                    programme_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    label TEXT NOT NULL,
                    manifest_digest TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    retired_at TEXT,
                    UNIQUE (namespace_id, programme_id, project_id)
                );
                CREATE TABLE IF NOT EXISTS events (
                    event_id TEXT PRIMARY KEY,
                    namespace_id TEXT NOT NULL,
                    programme_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    item_id TEXT,
                    payload_json TEXT NOT NULL,
                    event_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    operation_id TEXT UNIQUE,
                    UNIQUE (namespace_id, programme_id, sequence)
                );
                CREATE TABLE IF NOT EXISTS projections (
                    namespace_id TEXT NOT NULL,
                    programme_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    item_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    last_event_hash TEXT NOT NULL,
                    PRIMARY KEY (namespace_id, programme_id, project_id, item_id)
                );
                CREATE TABLE IF NOT EXISTS assessments (
                    assessment_id TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL,
                    consumed INTEGER NOT NULL DEFAULT 0,
                    approval_json TEXT
                );
                CREATE TABLE IF NOT EXISTS receipts (
                    receipt_id TEXT PRIMARY KEY,
                    data_json TEXT NOT NULL
                );
                INSERT INTO schema_meta(key, value) VALUES ('schema_version', '2.0.0')
                ON CONFLICT(key) DO UPDATE SET value=excluded.value;
                """
            )

    def schema_version(self) -> str:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT value FROM schema_meta WHERE key='schema_version'"
            ).fetchone()
        if row is None:
            raise StoreIntegrityError("store is not initialized")
        return str(row[0])

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=self.lock_timeout_seconds,
            isolation_level=None,
            check_same_thread=False,
            factory=_ClosingConnection,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute(
            f"PRAGMA busy_timeout = {int(self.lock_timeout_seconds * 1000)}"
        )
        return connection

    @staticmethod
    def _scope_values(scope: Any) -> tuple[str, str, str]:
        return (
            str(scope.repository_namespace_id),
            str(scope.programme_id),
            str(scope.project_id),
        )

    @staticmethod
    def _scope_from_row(row: Mapping[str, Any]) -> dict[str, str]:
        return {
            "repository_namespace_id": str(row["namespace_id"]),
            "programme_id": str(row["programme_id"]),
            "project_id": str(row["project_id"]),
        }

    def _begin(self, connection: sqlite3.Connection) -> None:
        try:
            connection.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            if "locked" in str(exc).lower():
                raise StoreLockTimeout("bounded SQLite write lock timed out") from exc
            raise

    def _chain_head_locked(
        self, connection: sqlite3.Connection, scope: Any
    ) -> tuple[int, str]:
        namespace, programme, _ = self._scope_values(scope)
        row = connection.execute(
            """
            SELECT sequence, event_hash FROM events
            WHERE namespace_id=? AND programme_id=?
            ORDER BY sequence DESC LIMIT 1
            """,
            (namespace, programme),
        ).fetchone()
        return (0, "") if row is None else (int(row[0]), str(row[1]))

    def chain_head(self, scope: Any) -> str:
        with self._connect() as connection:
            return self._chain_head_locked(connection, scope)[1]

    def _event_document(
        self,
        scope: Any,
        event_type: str,
        item_id: str | None,
        payload: Mapping[str, Any],
        sequence: int,
        previous_hash: str,
        event_id: str,
        operation_id: str | None,
    ) -> dict[str, Any]:
        namespace, programme, project = self._scope_values(scope)
        return {
            "schema_version": "2.0.0",
            "event_id": event_id,
            "scope": {
                "repository_namespace_id": namespace,
                "programme_id": programme,
                "project_id": project,
            },
            "sequence": sequence,
            "previous_hash": previous_hash,
            "event_type": event_type,
            "item_id": item_id,
            "payload": dict(payload),
            "created_at": utc_timestamp(),
            "operation_id": operation_id,
        }

    def append_event(
        self,
        scope: Any,
        event_type: str,
        item_id: str | None,
        payload: Mapping[str, Any],
        *,
        operation_id: str | None = None,
        crash_after_event: bool = False,
    ) -> dict[str, Any]:
        if not event_type:
            raise ValueError("event type is required")
        with self._connect() as connection:
            self._begin(connection)
            try:
                if operation_id:
                    existing = connection.execute(
                        "SELECT event_json FROM events WHERE operation_id=?", (operation_id,)
                    ).fetchone()
                    if existing is not None:
                        connection.rollback()
                        return json.loads(existing[0])
                sequence, previous_hash = self._chain_head_locked(connection, scope)
                event_id = f"event-{uuid4()}"
                document = self._event_document(
                    scope,
                    event_type,
                    item_id,
                    payload,
                    sequence + 1,
                    previous_hash,
                    event_id,
                    operation_id,
                )
                event_hash = canonical_digest(document)
                document["event_hash"] = event_hash
                payload_json = canonical_json(dict(payload))
                connection.execute(
                    """
                    INSERT INTO events(
                      event_id, namespace_id, programme_id, project_id, sequence,
                      previous_hash, event_hash, event_type, item_id, payload_json,
                      event_json, created_at, operation_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id,
                        document["scope"]["repository_namespace_id"],
                        document["scope"]["programme_id"],
                        document["scope"]["project_id"],
                        sequence + 1,
                        previous_hash,
                        event_hash,
                        event_type,
                        item_id,
                        payload_json,
                        canonical_json(document),
                        document["created_at"],
                        operation_id,
                    ),
                )
                self._apply_projection_locked(connection, scope, document)
                if crash_after_event:
                    raise RuntimeError("crash injection requested; transaction rolled back")
                connection.commit()
                return document
            except Exception:
                connection.rollback()
                raise

    def _apply_projection_locked(
        self, connection: sqlite3.Connection, scope: Any, event: Mapping[str, Any]
    ) -> None:
        payload = event.get("payload", {})
        item_id = event.get("item_id") or payload.get("item_id")
        if not item_id or str(item_id).startswith("binding:"):
            return
        namespace, programme, project = self._scope_values(scope)
        current = connection.execute(
            """
            SELECT data_json FROM projections
            WHERE namespace_id=? AND programme_id=? AND project_id=? AND item_id=?
            """,
            (namespace, programme, project, item_id),
        ).fetchone()
        current_data = json.loads(current[0]) if current is not None else None
        event_type = str(event.get("event_type"))
        status = str(payload.get("status", "active"))
        candidate = payload.get("candidate")
        if event_type == "write" and isinstance(candidate, dict):
            data = dict(candidate)
            data.update(
                {
                    "item_id": candidate.get("item_id", item_id),
                    "status": "active",
                    "version_id": str(event["event_id"]),
                    "predecessor_id": None,
                    "successor_id": None,
                    "contradiction_ids": [],
                    "last_event_hash": event["event_hash"],
                    "candidate_digest": payload.get("candidate_digest"),
                }
            )
        elif event_type in {"correct", "supersede"} and isinstance(candidate, dict):
            if current_data is not None:
                current_data["status"] = "corrected" if event_type == "correct" else "superseded"
                current_data["successor_id"] = candidate.get("item_id")
                current_data["last_event_hash"] = event["event_hash"]
                self._upsert_projection_locked(connection, scope, current_data)
            data = dict(candidate)
            data.update(
                {
                    "item_id": candidate.get("item_id"),
                    "status": "active",
                    "version_id": str(event["event_id"]),
                    "predecessor_id": item_id,
                    "successor_id": None,
                    "contradiction_ids": [],
                    "last_event_hash": event["event_hash"],
                    "candidate_digest": canonical_digest(candidate),
                }
            )
        elif current_data is not None:
            data = dict(current_data)
            data["status"] = status
            data["last_event_hash"] = event["event_hash"]
            if event_type == "contradiction_opened":
                data.setdefault("contradiction_ids", []).append(str(payload.get("reason", "review")))
        else:
            data = {
                "item_id": item_id,
                "status": status,
                "category": "lifecycle",
                "statement": "",
                "confidence": 0.0,
                "data_classification": "public",
                "owner": "",
                "expiry": "9999-12-31T23:59:59Z",
                "version_id": str(event["event_id"]),
                "predecessor_id": None,
                "successor_id": None,
                "contradiction_ids": [],
                "last_event_hash": event["event_hash"],
                "candidate_digest": payload.get("candidate_digest"),
                "epg_node_ids": list(payload.get("epg_node_ids", [])),
                "sdl_decision_id": "",
                "visibility": "project",
                "origin": "lifecycle",
            }
        data["schema_version"] = "2.0.0"
        data["epg_node_ids"] = list(data.get("epg_node_ids", payload.get("epg_node_ids", [])))
        self._upsert_projection_locked(connection, scope, data)

    def _upsert_projection_locked(
        self, connection: sqlite3.Connection, scope: Any, data: Mapping[str, Any]
    ) -> None:
        namespace, programme, project = self._scope_values(scope)
        connection.execute(
            """
            INSERT INTO projections(namespace_id, programme_id, project_id, item_id,
                                    status, data_json, last_event_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(namespace_id, programme_id, project_id, item_id)
            DO UPDATE SET status=excluded.status, data_json=excluded.data_json,
                          last_event_hash=excluded.last_event_hash
            """,
            (
                namespace,
                programme,
                project,
                str(data["item_id"]),
                str(data["status"]),
                canonical_json(dict(data)),
                str(data["last_event_hash"]),
            ),
        )

    def register_binding(self, data: Mapping[str, Any], *, operation_id: str) -> dict[str, Any]:
        scope = data["scope"]
        namespace = scope["repository_namespace_id"]
        programme = scope["programme_id"]
        project = scope["project_id"]
        with self._connect() as connection:
            self._begin(connection)
            try:
                existing = connection.execute(
                    """
                    SELECT data_json FROM bindings
                    WHERE namespace_id=? AND programme_id=? AND project_id=?
                    """,
                    (namespace, programme, project),
                ).fetchone()
                if existing is not None:
                    if canonical_digest(json.loads(existing[0])) == canonical_digest(data):
                        connection.rollback()
                        return {"status": "noop", "binding": json.loads(existing[0])}
                    raise StoreIntegrityError("binding collision for registered scope")
                connection.execute(
                    "INSERT OR IGNORE INTO programme_state(namespace_id, programme_id, status) VALUES (?, ?, 'active')",
                    (namespace, programme),
                )
                connection.execute(
                    """
                    INSERT INTO bindings(binding_id, namespace_id, programme_id, project_id,
                                         label, manifest_digest, data_json, status, created_at, retired_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        data["binding_id"],
                        namespace,
                        programme,
                        project,
                        data["label"],
                        data["manifest_digest"],
                        canonical_json(dict(data)),
                        data.get("status", "active"),
                        data.get("created_at", utc_timestamp()),
                        data.get("retired_at"),
                    ),
                )
                sequence, previous_hash = self._chain_head_locked(connection, type("S", (), {"repository_namespace_id": namespace, "programme_id": programme, "project_id": project})())
                event_id = f"event-{uuid4()}"
                document = self._event_document(
                    type("S", (), {"repository_namespace_id": namespace, "programme_id": programme, "project_id": project})(),
                    "status_change",
                    f"binding:{data['binding_id']}",
                    {"binding": dict(data), "status": "active", "item_id": f"binding:{data['binding_id']}"},
                    sequence + 1,
                    previous_hash,
                    event_id,
                    operation_id,
                )
                document["event_hash"] = canonical_digest(document)
                connection.execute(
                    """
                    INSERT INTO events(event_id, namespace_id, programme_id, project_id, sequence,
                        previous_hash, event_hash, event_type, item_id, payload_json, event_json, created_at, operation_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        event_id, namespace, programme, project, sequence + 1,
                        previous_hash, document["event_hash"], "status_change",
                        document["item_id"], canonical_json(document["payload"]),
                        canonical_json(document), document["created_at"], operation_id,
                    ),
                )
                connection.commit()
                return {"status": "committed", "binding": dict(data), **document}
            except Exception:
                connection.rollback()
                raise

    def get_binding(self, scope: Any) -> dict[str, Any] | None:
        namespace, programme, project = self._scope_values(scope)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT data_json FROM bindings WHERE namespace_id=? AND programme_id=? AND project_id=?",
                (namespace, programme, project),
            ).fetchone()
        return None if row is None else json.loads(row[0])

    def transition_binding(
        self, scope: Any, status: str, *, operation_id: str, reason: str
    ) -> dict[str, Any]:
        if status not in {"active", "retired"}:
            raise ValueError("unsupported binding status")
        namespace, programme, project = self._scope_values(scope)
        with self._connect() as connection:
            self._begin(connection)
            try:
                row = connection.execute(
                    "SELECT data_json FROM bindings WHERE namespace_id=? AND programme_id=? AND project_id=?",
                    (namespace, programme, project),
                ).fetchone()
                if row is None:
                    raise StoreIntegrityError("binding is missing")
                data = json.loads(row[0])
                data["status"] = status
                data["retired_at"] = utc_timestamp() if status == "retired" else None
                connection.execute(
                    "UPDATE bindings SET data_json=?, status=?, retired_at=? WHERE namespace_id=? AND programme_id=? AND project_id=?",
                    (canonical_json(data), status, data["retired_at"], namespace, programme, project),
                )
                sequence, previous_hash = self._chain_head_locked(connection, scope)
                event_id = f"event-{uuid4()}"
                document = self._event_document(scope, "status_change", f"binding:{data['binding_id']}", {"status": status, "reason": reason, "item_id": f"binding:{data['binding_id']}"}, sequence + 1, previous_hash, event_id, operation_id)
                document["event_hash"] = canonical_digest(document)
                connection.execute(
                    "INSERT INTO events(event_id, namespace_id, programme_id, project_id, sequence, previous_hash, event_hash, event_type, item_id, payload_json, event_json, created_at, operation_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (event_id, namespace, programme, project, sequence + 1, previous_hash, document["event_hash"], "status_change", document["item_id"], canonical_json(document["payload"]), canonical_json(document), document["created_at"], operation_id),
                )
                connection.commit()
                return document
            except Exception:
                connection.rollback()
                raise

    def close_programme(self, scope: Any, *, operation_id: str) -> dict[str, Any]:
        namespace, programme, project = self._scope_values(scope)
        with self._connect() as connection:
            self._begin(connection)
            try:
                connection.execute(
                    "INSERT INTO programme_state(namespace_id, programme_id, status) VALUES (?, ?, 'closed') ON CONFLICT(namespace_id, programme_id) DO UPDATE SET status='closed'",
                    (namespace, programme),
                )
                sequence, previous_hash = self._chain_head_locked(connection, scope)
                event_id = f"event-{uuid4()}"
                document = self._event_document(scope, "status_change", None, {"status": "closed", "preserve_history": True}, sequence + 1, previous_hash, event_id, operation_id)
                document["event_hash"] = canonical_digest(document)
                connection.execute(
                    "INSERT INTO events(event_id, namespace_id, programme_id, project_id, sequence, previous_hash, event_hash, event_type, item_id, payload_json, event_json, created_at, operation_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (event_id, namespace, programme, project, sequence + 1, previous_hash, document["event_hash"], "status_change", None, canonical_json(document["payload"]), canonical_json(document), document["created_at"], operation_id),
                )
                connection.commit()
                return document
            except Exception:
                connection.rollback()
                raise

    def programme_status(self, scope: Any) -> str:
        namespace, programme, _ = self._scope_values(scope)
        with self._connect() as connection:
            row = connection.execute("SELECT status FROM programme_state WHERE namespace_id=? AND programme_id=?", (namespace, programme)).fetchone()
        return "active" if row is None else str(row[0])

    def has_programme_history(self, scope: Any) -> bool:
        namespace, programme, _ = self._scope_values(scope)
        with self._connect() as connection:
            row = connection.execute("SELECT 1 FROM events WHERE namespace_id=? AND programme_id=? LIMIT 1", (namespace, programme)).fetchone()
        return row is not None

    def get_projection(self, scope: Any, item_id: str | None) -> dict[str, Any] | None:
        if not item_id:
            return None
        namespace, programme, project = self._scope_values(scope)
        with self._connect() as connection:
            row = connection.execute("SELECT data_json FROM projections WHERE namespace_id=? AND programme_id=? AND project_id=? AND item_id=?", (namespace, programme, project, item_id)).fetchone()
        return None if row is None else json.loads(row[0])

    def list_projections(self, scope: Any) -> list[dict[str, Any]]:
        namespace, programme, project = self._scope_values(scope)
        with self._connect() as connection:
            rows = connection.execute("SELECT data_json FROM projections WHERE namespace_id=? AND programme_id=? AND project_id=? ORDER BY item_id", (namespace, programme, project)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def events(self, scope: Any) -> list[dict[str, Any]]:
        namespace, programme, _ = self._scope_values(scope)
        with self._connect() as connection:
            rows = connection.execute("SELECT event_json FROM events WHERE namespace_id=? AND programme_id=? ORDER BY sequence", (namespace, programme)).fetchall()
        return [json.loads(row[0]) for row in rows]

    def verify_chain(self, scope: Any) -> list[str]:
        errors: list[str] = []
        events = self.events(scope)
        previous = ""
        for expected_sequence, event in enumerate(events, start=1):
            if event.get("sequence") != expected_sequence:
                errors.append(f"sequence gap at {expected_sequence}")
            if event.get("previous_hash") != previous:
                errors.append(f"previous hash mismatch at {expected_sequence}")
            actual_hash = event.get("event_hash")
            body = dict(event)
            body.pop("event_hash", None)
            if actual_hash != canonical_digest(body):
                errors.append(f"event hash mismatch at {expected_sequence}")
            previous = str(actual_hash or "")
        return errors

    def assert_integrity(self, scope: Any) -> None:
        errors = self.verify_chain(scope)
        if errors:
            raise StoreIntegrityError("; ".join(errors))

    def rebuild_projection(self, scope: Any) -> dict[str, dict[str, Any]]:
        self.assert_integrity(scope)
        namespace, programme, project = self._scope_values(scope)
        with self._connect() as connection:
            self._begin(connection)
            try:
                connection.execute("DELETE FROM projections WHERE namespace_id=? AND programme_id=? AND project_id=?", (namespace, programme, project))
                for event in self.events(scope):
                    self._apply_projection_locked(connection, scope, event)
                connection.commit()
            except Exception:
                connection.rollback()
                raise
        return {row["item_id"]: row for row in self.list_projections(scope)}

    def save_assessment(self, data: Mapping[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute("INSERT OR REPLACE INTO assessments(assessment_id, data_json, consumed, approval_json) VALUES (?, ?, 0, NULL)", (data["assessment_id"], canonical_json(dict(data))))

    def get_assessment(self, assessment_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT data_json, consumed FROM assessments WHERE assessment_id=?", (assessment_id,)).fetchone()
        if row is None:
            return None
        data = json.loads(row[0])
        data["consumed"] = bool(row[1])
        return data

    def consume_assessment(self, assessment_id: str, approval: Mapping[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute("UPDATE assessments SET consumed=1, approval_json=? WHERE assessment_id=?", (canonical_json(dict(approval)), assessment_id))

    def save_receipt(self, data: Mapping[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute("INSERT INTO receipts(receipt_id, data_json) VALUES (?, ?)", (data["receipt_id"], canonical_json(dict(data))))

    def tamper_for_test(self, scope: Any, *, sequence: int, field: str, value: str) -> None:
        namespace, programme, _ = self._scope_values(scope)
        if field not in {"payload_json", "event_json"}:
            raise ValueError("test tampering field is not allowed")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT event_json FROM events WHERE namespace_id=? AND programme_id=? AND sequence=?",
                (namespace, programme, sequence),
            ).fetchone()
            if row is None:
                return
            event = json.loads(row[0])
            if field == "payload_json":
                event["payload"] = json.loads(value)
                connection.execute(
                    "UPDATE events SET payload_json=?, event_json=? WHERE namespace_id=? AND programme_id=? AND sequence=?",
                    (value, canonical_json(event), namespace, programme, sequence),
                )
            else:
                connection.execute(
                    "UPDATE events SET event_json=? WHERE namespace_id=? AND programme_id=? AND sequence=?",
                    (value, namespace, programme, sequence),
                )
