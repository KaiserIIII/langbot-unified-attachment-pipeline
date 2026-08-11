from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class ParseResult:
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    error: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.text.strip()) and not self.error


@dataclass(slots=True)
class Receipt:
    name: str
    received_at: str
    sha256: str
    raw_path: str
    parsed_path: str
    parse_status: str
    index_status: str
    parser_metadata: dict[str, Any] = field(default_factory=dict)
    parse_error: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Receipt":
        return cls(**value)
