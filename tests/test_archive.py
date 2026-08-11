from __future__ import annotations

import datetime as dt

from langbot_unified_pipeline.archive import AttachmentPipeline, safe_filename


def test_latest_same_name_receipt_is_authoritative(tmp_path):
    pipeline = AttachmentPipeline(tmp_path)
    older = pipeline.ingest(
        "sample.txt",
        b"STALE_MARKER",
        received_at=dt.datetime(2026, 8, 12, 7, tzinfo=dt.timezone.utc),
    )
    newest = pipeline.ingest(
        "sample.txt",
        b"LATEST_MARKER",
        received_at=dt.datetime(2026, 8, 12, 8, tzinfo=dt.timezone.utc),
    )

    context = pipeline.context_for_query("What was in sample.txt?")

    assert "LATEST_MARKER" in context
    assert "STALE_MARKER" not in context
    assert f"sha256={newest.sha256}" in context
    assert f"sha256={older.sha256}" not in context
    assert "version=current" in context


def test_history_query_labels_old_version(tmp_path):
    pipeline = AttachmentPipeline(tmp_path)
    pipeline.ingest(
        "sample.txt",
        b"OLD_VALUE",
        received_at=dt.datetime(2026, 8, 12, 7, tzinfo=dt.timezone.utc),
    )
    pipeline.ingest(
        "sample.txt",
        b"NEW_VALUE",
        received_at=dt.datetime(2026, 8, 12, 8, tzinfo=dt.timezone.utc),
    )

    context = pipeline.context_for_query("Show all versions and history of sample.txt")

    assert "NEW_VALUE" in context
    assert "OLD_VALUE" in context
    assert "version=current" in context
    assert "version=historical" in context

    chinese_context = pipeline.context_for_query("显示 sample.txt 的所有历史版本")
    assert "OLD_VALUE" in chinese_context


def test_indexer_receives_digest_bound_metadata(tmp_path):
    calls = []
    pipeline = AttachmentPipeline(tmp_path, indexer=lambda doc_id, text, metadata: calls.append((doc_id, text, metadata)))

    receipt = pipeline.ingest("notes.txt", b"indexed content")

    assert receipt.index_status == "completed"
    assert calls == [(receipt.sha256, "indexed content", {
        "name": "notes.txt",
        "received_at": receipt.received_at,
        "sha256": receipt.sha256,
    })]


def test_invalid_attachment_receipt_is_recorded_without_indexing(tmp_path):
    calls = []
    pipeline = AttachmentPipeline(tmp_path, indexer=lambda *args: calls.append(args))
    receipt = pipeline.ingest("broken.png", b"not an image")
    assert receipt.parse_status == "failed"
    assert receipt.index_status == "not_indexed"
    assert receipt.parse_error == "invalid_image"
    assert calls == []


def test_failed_parse_cannot_reuse_same_digest_parsed_sidecar(tmp_path):
    pipeline = AttachmentPipeline(tmp_path)
    pipeline.ingest("sample.txt", b"same digest bytes")
    failed = pipeline.ingest("sample.png", b"same digest bytes")
    assert failed.parse_status == "failed"
    assert failed.parsed_path == ""
    assert "DIGEST_BOUND_PARSED_CONTENT" not in pipeline.context_for_query("sample.png")


def test_corrupt_receipts_and_escaped_parsed_paths_are_ignored(tmp_path):
    pipeline = AttachmentPipeline(tmp_path)
    receipt = pipeline.ingest("sample.txt", b"content")
    receipt_file = next((tmp_path / "receipts").glob("**/*.json"))
    receipt_file.write_text(
        '{"name":"sample.txt","received_at":"2026-08-12T08:00:00+00:00",'
        f'"sha256":"{receipt.sha256}","raw_path":"archive/raw",'
        '"parsed_path":"../outside.txt","parse_status":"completed",'
        '"index_status":"not_indexed","parser_metadata":{},"parse_error":""}',
        encoding="utf-8",
    )
    (tmp_path / "receipts" / "corrupt.json").write_text("not json", encoding="utf-8")
    assert "DIGEST_BOUND_PARSED_CONTENT" not in pipeline.context_for_query("sample.txt")


def test_invalid_receipt_timestamp_does_not_break_other_results(tmp_path):
    pipeline = AttachmentPipeline(tmp_path)
    pipeline.ingest("sample.txt", b"valid content")
    bad = tmp_path / "receipts" / "bad-time.json"
    bad.write_text(
        '{"name":"sample.txt","received_at":"not-a-time","sha256":"bad",'
        '"raw_path":"archive/raw","parsed_path":"","parse_status":"failed",'
        '"index_status":"not_indexed","parser_metadata":{},"parse_error":"bad"}',
        encoding="utf-8",
    )
    assert "valid content" in pipeline.context_for_query("sample.txt")


def test_safe_filename_removes_parent_components_and_control_punctuation():
    assert safe_filename("../folder/bad:name?.txt") == "badname.txt"
    assert safe_filename("...") == "attachment.bin"
