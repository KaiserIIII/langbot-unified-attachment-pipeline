from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from langbot_unified_pipeline.parsers import parse_attachment


pytestmark = pytest.mark.skipif(os.name != "nt", reason="requires local Microsoft Office")
MARKER = "PUBLIC_LEGACY_OFFICE_ALPHA"


def _create_legacy_fixture(path: Path, kind: str) -> None:
    worker = Path(__file__).with_name("office_fixture_worker.py")
    result = subprocess.run(
        [sys.executable, str(worker), kind, str(path)],
        check=False,
        capture_output=True,
        timeout=120,
    )
    if result.returncode == 2:
        pytest.skip(f"Microsoft {kind} is unavailable")
    assert result.returncode == 0
    assert path.is_file()


@pytest.mark.parametrize(
    ("filename", "creator"),
    [("sample.doc", "word"), ("sample.xls", "excel"), ("sample.ppt", "powerpoint")],
    ids=["doc", "xls", "ppt"],
)
def test_real_legacy_office_round_trip(tmp_path, filename, creator):
    path = tmp_path / filename
    _create_legacy_fixture(path, creator)
    result = parse_attachment(path.read_bytes(), filename)
    assert result.ok
    assert MARKER in result.text
