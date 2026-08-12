from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .models import Receipt
from .parsers import AttachmentParseError, ParserConfig, parse_attachment


Indexer = Callable[[str, str, dict[str, Any]], None]
_HISTORY_MARKERS = (
    "history",
    "historical",
    "older version",
    "old version",
    "previous version",
    "all versions",
    "历史版本",
    "旧版本",
    "以前版本",
    "所有版本",
)


def safe_filename(value: str) -> str:
    name = os.path.basename(str(value or "").replace("\\", "/")).lstrip(".")
    name = "".join(character for character in name if character.isalnum() or character in ".-_ ")
    name = re.sub(r"\s+", "_", name).strip("._")
    return name[:180] or "attachment.bin"


def _received_timestamp(value: str) -> float:
    try:
        return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    except (AttributeError, ValueError):
        return float("-inf")


class AttachmentPipeline:
    def __init__(
        self,
        root: str | Path,
        *,
        parser_config: ParserConfig | None = None,
        indexer: Indexer | None = None,
    ) -> None:
        self.root = Path(root).expanduser().resolve()
        self.parser_config = parser_config or ParserConfig()
        self.indexer = indexer

    def ingest(
        self,
        filename: str,
        data: bytes,
        *,
        received_at: dt.datetime | None = None,
    ) -> Receipt:
        received_at = received_at or dt.datetime.now(dt.timezone.utc)
        if received_at.tzinfo is None:
            received_at = received_at.replace(tzinfo=dt.timezone.utc)
        name = safe_filename(filename)
        digest = hashlib.sha256(data).hexdigest()
        date_folder = received_at.strftime("%Y-%m-%d")
        stem = f"{received_at:%H%M%S}-{digest[:12]}-{name}"
        raw_path = self.root / "archive" / date_folder / stem
        parsed_path = self.root / "parsed" / f"{digest}.txt"
        receipt_path = self.root / "receipts" / date_folder / f"{stem}.json"

        self._write_once(raw_path, data)
        parse_status = "failed"
        index_status = "not_indexed"
        parse_error = ""
        parser_metadata: dict[str, Any] = {}
        try:
            parsed = parse_attachment(data, name, self.parser_config)
            parser_metadata = parsed.metadata
            if parsed.ok:
                self._atomic_write(parsed_path, parsed.text.encode("utf-8"))
                parse_status = "completed"
                if self.indexer is not None:
                    self.indexer(
                        digest,
                        parsed.text,
                        {
                            "name": name,
                            "received_at": received_at.isoformat(timespec="seconds"),
                            "sha256": digest,
                        },
                    )
                    index_status = "completed"
            else:
                parse_status = "failed"
                parse_error = parsed.error or "parser_returned_no_text"
        except AttachmentParseError as exc:
            parse_error = str(exc)

        receipt = Receipt(
            name=name,
            received_at=received_at.isoformat(timespec="seconds"),
            sha256=digest,
            raw_path=raw_path.relative_to(self.root).as_posix(),
            parsed_path=(
                parsed_path.relative_to(self.root).as_posix()
                if parse_status == "completed" and parsed_path.is_file()
                else ""
            ),
            parse_status=parse_status,
            index_status=index_status,
            parser_metadata=parser_metadata,
            parse_error=parse_error,
        )
        self._atomic_write(
            receipt_path,
            json.dumps(receipt.as_dict(), indent=2, sort_keys=True).encode("utf-8"),
        )
        return receipt

    def receipts(self) -> list[Receipt]:
        records: list[Receipt] = []
        for path in self.root.glob("receipts/**/*.json"):
            try:
                records.append(Receipt.from_dict(json.loads(path.read_text(encoding="utf-8"))))
            except (OSError, UnicodeError, json.JSONDecodeError, TypeError):
                continue
        return records

    def context_for_query(self, query: str, *, max_items: int = 8) -> str:
        normalized = " ".join(str(query or "").casefold().split())
        if not normalized:
            return ""
        history = any(marker in normalized for marker in _HISTORY_MARKERS)
        candidates = [record for record in self.receipts() if record.name.casefold() in normalized]
        if not candidates:
            return ""
        candidates.sort(key=lambda item: _received_timestamp(item.received_at), reverse=True)

        newest_by_name: dict[str, Receipt] = {}
        for record in candidates:
            newest_by_name.setdefault(record.name.casefold(), record)
        selected: list[tuple[Receipt, str]] = []
        for record in candidates:
            version = "current" if record is newest_by_name[record.name.casefold()] else "historical"
            if version == "current" or history:
                selected.append((record, version))
        selected = selected[: max(1, min(max_items, 20))]

        lines = [
            "[ARCHIVED_ATTACHMENT_LEDGER]",
            "Entries marked current are the newest direct receipts for that filename. Parsed text is bound to the listed SHA-256.",
            "Current direct evidence outranks older same-name search results. Never combine content from different digests.",
        ]
        for record, version in selected:
            lines.append(
                f"- name={json.dumps(record.name)}; received={record.received_at}; "
                f"sha256={record.sha256}; version={version}; parse_status={record.parse_status}"
            )
            parsed = self._read_parsed(record)
            if parsed:
                lines.extend(("[DIGEST_BOUND_PARSED_CONTENT]", parsed, "[END_DIGEST_BOUND_PARSED_CONTENT]"))
        lines.append("[END_ARCHIVED_ATTACHMENT_LEDGER]")
        return "\n".join(lines)

    def _read_parsed(self, receipt: Receipt) -> str:
        if receipt.parse_status != "completed" or not receipt.parsed_path:
            return ""
        path = (self.root / receipt.parsed_path).resolve()
        if not path.is_relative_to(self.root) or not path.is_file():
            return ""
        try:
            return path.read_text(encoding="utf-8")[:12000].strip()
        except (OSError, UnicodeError):
            return ""

    @staticmethod
    def _write_once(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("xb") as handle:
                handle.write(data)
        except FileExistsError:
            if path.read_bytes() != data:
                raise RuntimeError("archive path collision")

    @staticmethod
    def _atomic_write(path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        try:
            temporary.write_bytes(data)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)
