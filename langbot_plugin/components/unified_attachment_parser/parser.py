from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any, Awaitable, Callable

from langbot_plugin.api.definition.components.parser.parser import Parser
from langbot_plugin.api.entities.builtin.provider.message import ContentElement, Message
from langbot_plugin.api.entities.builtin.rag.models import (
    ParseContext,
    ParseResult,
    TextSection,
)
from langbot_unified_pipeline import (
    AsyncParserConfig,
    parse_attachment_async,
)
from langbot_unified_pipeline.parsers import SUPPORTED_EXTENSIONS


DEFAULT_VISION_PROMPT = (
    "Describe every visible object, the scene and layout, relationships between objects, "
    "and all readable text. Separate direct observations from uncertainty. Do not ask the "
    "user to upload the image because it is already attached."
)

MIME_SUFFIXES = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-excel.sheet.macroenabled.12": ".xlsm",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.ms-powerpoint.presentation.macroenabled.12": ".pptm",
    "application/vnd.ms-powerpoint": ".ppt",
    "text/csv": ".csv",
    "text/tab-separated-values": ".tsv",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/html": ".html",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
}


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return min(maximum, max(minimum, parsed))


def _normalized_filename(filename: str, mime_type: str) -> str:
    clean_mime = (mime_type or "").split(";", 1)[0].strip().casefold()
    mime_suffix = MIME_SUFFIXES.get(clean_mime)
    name = Path(filename or "attachment").name
    current_suffix = Path(name).suffix.casefold()
    if current_suffix in SUPPORTED_EXTENSIONS:
        return name
    if mime_suffix:
        stem = Path(name).stem if Path(name).suffix else name
        return f"{stem}{mime_suffix}"
    return name


def _response_text(response: Message) -> str:
    if isinstance(response.content, str):
        return response.content
    if isinstance(response.content, list):
        return "\n".join(
            element.text
            for element in response.content
            if element.type == "text" and element.text
        )
    return ""


def _sections(text: str, filename: str) -> list[TextSection]:
    if not text.strip():
        return []
    matches = list(re.finditer(r"(?m)^#{1,6}\s+(.+)$", text))
    if not matches:
        return [TextSection(content=text, heading=filename, level=0)]
    sections: list[TextSection] = []
    if text[: matches[0].start()].strip():
        sections.append(
            TextSection(
                content=text[: matches[0].start()].strip(),
                heading=filename,
                level=0,
            )
        )
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[match.start():end].strip()
        page_match = re.fullmatch(r"Page\s+(\d+)", match.group(1), re.IGNORECASE)
        sections.append(
            TextSection(
                content=block,
                heading=match.group(1).strip(),
                level=len(match.group(0)) - len(match.group(0).lstrip("#")),
                page=int(page_match.group(1)) if page_match else None,
            )
        )
    return sections


class UnifiedAttachmentParser(Parser):
    async def parse(self, context: ParseContext) -> ParseResult:
        config = self.plugin.get_config() or {}
        vision_enabled = bool(config.get("enable_vision", True))
        primary_uuid = config.get("vision_llm_model_uuid") if vision_enabled else None
        fallback_uuid = config.get("vision_fallback_llm_model_uuid") if vision_enabled else None

        def vision_callback(
            model_uuid: str | None,
            timeout_seconds: int,
        ) -> Callable[[bytes, str, str], Awaitable[str]] | None:
            if not model_uuid:
                return None

            async def invoke(image: bytes, _mime_type: str, prompt: str) -> str:
                response = await self.plugin.invoke_llm(
                    llm_model_uuid=model_uuid,
                    messages=[
                        Message(
                            role="user",
                            content=[
                                ContentElement.from_image_base64(
                                    base64.b64encode(image).decode("ascii")
                                ),
                                ContentElement.from_text(prompt),
                            ],
                        )
                    ],
                    extra_args={"max_tokens": 4096},
                    timeout=timeout_seconds,
                )
                return _response_text(response)

            return invoke

        prompt = str(config.get("vision_prompt") or DEFAULT_VISION_PROMPT).strip()
        parser_config = AsyncParserConfig(
            max_bytes=_bounded_int(config.get("max_file_mb"), 20, 1, 200) * 1024 * 1024,
            max_rows_per_sheet=_bounded_int(config.get("max_rows_per_sheet"), 500, 1, 5000),
            max_pdf_vision_pages=_bounded_int(config.get("max_pdf_vision_pages"), 24, 1, 100),
            vision_prompt=prompt,
            vision_primary=vision_callback(
                primary_uuid,
                _bounded_int(config.get("primary_timeout_seconds"), 45, 5, 600),
            ),
            vision_fallback=vision_callback(
                fallback_uuid,
                _bounded_int(config.get("fallback_timeout_seconds"), 480, 5, 900),
            ),
        )
        normalized_name = _normalized_filename(context.filename, context.mime_type)
        parsed = await parse_attachment_async(
            context.file_content,
            normalized_name,
            parser_config,
        )
        if not parsed.ok:
            raise ValueError(f"attachment_parse_failed:{parsed.error or 'empty_content'}")
        metadata = {
            **context.metadata,
            **parsed.metadata,
            "source_filename": context.filename,
            "normalized_filename": normalized_name,
            "source_mime_type": context.mime_type,
            "parser": "KaiserIIII/UnifiedAttachmentPipeline",
        }
        return ParseResult(
            text=parsed.text,
            sections=_sections(parsed.text, normalized_name),
            metadata=metadata,
        )
