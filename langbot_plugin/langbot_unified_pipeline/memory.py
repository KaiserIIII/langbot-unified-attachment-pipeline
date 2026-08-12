from __future__ import annotations

import datetime as dt
import re
import sqlite3
from pathlib import Path
from typing import Any


_CREDENTIAL_PATTERNS = (
    re.compile(r"\b(?:api[_ -]?key|secret|password|passwd|token|cookie|session|sessdata)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"\bBearer\s+[A-Za-z0-9._~+/-]{16,}=*", re.IGNORECASE),
    re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"),
    re.compile(r"\b(?:sk|pk)-[A-Za-z0-9_-]{16,}\b"),
)


def contains_credential_material(text: str) -> bool:
    value = str(text or "")
    return any(pattern.search(value) for pattern in _CREDENTIAL_PATTERNS)


class VersionedMemoryStore:
    def __init__(self, database: str | Path) -> None:
        self.database = Path(database)
        self.database.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def remember(
        self,
        fact_key: str,
        text: str,
        *,
        captured_at: dt.datetime | None = None,
        source: str = "user-direct",
        confidence: str = "high",
    ) -> int:
        fact_key = str(fact_key or "").strip()
        text = str(text or "").strip()
        if not fact_key or not text:
            raise ValueError("fact_key and text are required")
        if contains_credential_material(text):
            raise ValueError("credential material cannot be stored")
        captured_at = captured_at or dt.datetime.now(dt.timezone.utc)
        if captured_at.tzinfo is None:
            captured_at = captured_at.replace(tzinfo=dt.timezone.utc)
        timestamp = captured_at.astimezone(dt.timezone.utc).isoformat(timespec="seconds")

        connection = sqlite3.connect(self.database)
        try:
            cursor = connection.execute(
                "INSERT INTO facts (fact_key, text, captured_at, source, confidence, is_current) VALUES (?, ?, ?, ?, ?, 0)",
                (fact_key, text, timestamp, source, confidence),
            )
            row_id = int(cursor.lastrowid)
            newest = connection.execute(
                "SELECT id FROM facts WHERE fact_key = ? ORDER BY captured_at DESC, id DESC LIMIT 1",
                (fact_key,),
            ).fetchone()
            connection.execute("UPDATE facts SET is_current = 0 WHERE fact_key = ?", (fact_key,))
            connection.execute("UPDATE facts SET is_current = 1 WHERE id = ?", (newest[0],))
            connection.commit()
            return row_id
        finally:
            connection.close()

    def current(self, fact_key: str) -> dict[str, Any] | None:
        connection = sqlite3.connect(self.database)
        try:
            connection.row_factory = sqlite3.Row
            row = connection.execute(
                "SELECT id, fact_key, text, captured_at, source, confidence FROM facts "
                "WHERE fact_key = ? AND is_current = 1 LIMIT 1",
                (fact_key,),
            ).fetchone()
        finally:
            connection.close()
        return dict(row) if row else None

    def history(self, fact_key: str) -> list[dict[str, Any]]:
        connection = sqlite3.connect(self.database)
        try:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                "SELECT id, fact_key, text, captured_at, source, confidence, is_current FROM facts "
                "WHERE fact_key = ? ORDER BY captured_at DESC, id DESC",
                (fact_key,),
            ).fetchall()
        finally:
            connection.close()
        return [dict(row) for row in rows]

    def _initialize(self) -> None:
        connection = sqlite3.connect(self.database)
        try:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS facts ("
                "id INTEGER PRIMARY KEY AUTOINCREMENT, "
                "fact_key TEXT NOT NULL, "
                "text TEXT NOT NULL, "
                "captured_at TEXT NOT NULL, "
                "source TEXT NOT NULL, "
                "confidence TEXT NOT NULL, "
                "is_current INTEGER NOT NULL DEFAULT 0)"
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS facts_current_idx ON facts(fact_key, is_current, captured_at DESC)"
            )
            connection.commit()
        finally:
            connection.close()
