from __future__ import annotations

import io
import asyncio

from docx import Document
from PIL import Image
from reportlab.pdfgen.canvas import Canvas

from langbot_unified_pipeline.parsers import AsyncParserConfig, parse_attachment_async
from langbot_unified_pipeline import parsers


MARKER = "PUBLIC_ASYNC_TEST_ALPHA"


def _docx() -> bytes:
    output = io.BytesIO()
    document = Document()
    document.add_heading(MARKER, level=1)
    document.save(output)
    return output.getvalue()


def _image() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (64, 48), "red").save(output, format="PNG")
    return output.getvalue()


def _blank_pdf() -> bytes:
    output = io.BytesIO()
    canvas = Canvas(output)
    canvas.showPage()
    canvas.save()
    return output.getvalue()


def test_async_image_rejects_invalid_primary_and_uses_fallback():
    calls: list[str] = []

    async def primary(_data: bytes, _mime: str, _prompt: str) -> str:
        calls.append("primary")
        return "Please upload the image."

    async def fallback(_data: bytes, _mime: str, _prompt: str) -> str:
        calls.append("fallback")
        return f"A red rectangle containing {MARKER}."

    result = asyncio.run(
        parse_attachment_async(
            _image(),
            "sample.png",
            AsyncParserConfig(vision_primary=primary, vision_fallback=fallback),
        )
    )

    assert result.ok
    assert MARKER in result.text
    assert calls == ["primary", "fallback"]


def test_async_scanned_pdf_uses_page_vision():
    async def vision(_data: bytes, mime_type: str, _prompt: str) -> str:
        assert mime_type == "image/png"
        return f"Scanned page with {MARKER}."

    result = asyncio.run(
        parse_attachment_async(
            _blank_pdf(),
            "scan.pdf",
            AsyncParserConfig(vision_primary=vision),
        )
    )

    assert result.ok
    assert MARKER in result.text
    assert result.metadata["vision_pages"] == 1


def test_async_nonvisual_document_uses_existing_parser():
    result = asyncio.run(parse_attachment_async(_docx(), "sample.docx"))

    assert result.ok
    assert MARKER in result.text


def test_async_legacy_word_converts_only_once(monkeypatch):
    calls: list[str] = []

    def convert(_data: bytes, source: str, target: str) -> bytes:
        calls.append(f"{source}:{target}")
        return _docx()

    monkeypatch.setattr(parsers, "_convert_with_libreoffice", convert)

    result = asyncio.run(parse_attachment_async(b"legacy", "sample.doc"))

    assert result.ok
    assert MARKER in result.text
    assert calls == [".doc:.docx"]
