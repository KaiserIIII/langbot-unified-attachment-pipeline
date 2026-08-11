from __future__ import annotations

import datetime as dt

import pytest

from langbot_unified_pipeline.memory import VersionedMemoryStore, contains_credential_material


def test_newer_fact_version_becomes_current_even_when_inserted_first(tmp_path):
    store = VersionedMemoryStore(tmp_path / "memory.db")
    newest = dt.datetime(2026, 8, 12, 8, tzinfo=dt.timezone.utc)
    older = dt.datetime(2026, 8, 12, 7, tzinfo=dt.timezone.utc)

    store.remember("preference.country", "new preference", captured_at=newest)
    store.remember("preference.country", "old preference", captured_at=older)

    assert store.current("preference.country")["text"] == "new preference"
    history = store.history("preference.country")
    assert [item["text"] for item in history] == ["new preference", "old preference"]
    assert [item["is_current"] for item in history] == [1, 0]


@pytest.mark.parametrize(
    "value",
    [
        "api_" + "key=" + "abcdefghijklmnop1234",
        "Authorization: " + "Bearer " + "abcdefghijklmnop1234",
        "pass" + "word: " + "this-is-a-secret-value",
        "SESS" + "DATA=" + "abcdefghijklmnop1234",
        ".".join(("eyJ" + "hbGciOiJIUzI1NiJ9", "eyJ" + "zdWIiOiIxMjMifQ", "signaturevalue")),
    ],
)
def test_credentials_are_detected_and_rejected(tmp_path, value):
    assert contains_credential_material(value)
    store = VersionedMemoryStore(tmp_path / "memory.db")
    with pytest.raises(ValueError, match="credential material"):
        store.remember("secret", value)


def test_normal_personal_fact_is_not_a_credential():
    assert not contains_credential_material("The preferred destination is currently undecided.")


def test_empty_fact_is_rejected(tmp_path):
    store = VersionedMemoryStore(tmp_path / "memory.db")
    with pytest.raises(ValueError, match="required"):
        store.remember("", "")


def test_missing_fact_returns_none_and_empty_history(tmp_path):
    store = VersionedMemoryStore(tmp_path / "memory.db")
    assert store.current("missing") is None
    assert store.history("missing") == []
