# LangBot Unified Attachment Pipeline

[简体中文](README.zh-CN.md)

A local-first, framework-neutral core for reliable chat attachment ingestion and version-aware long-term memory. It was designed for LangBot-style personal agents, but its parser, archive, index callback, and SQLite memory store can be used independently.

An installable LangBot Parser plugin is included in [`langbot_plugin/`](langbot_plugin/README.md). It exposes the common-format parser directly to LangBot, supports primary-to-fallback vision model routing, and can be built as a `.lbpkg` with the LangBot Plugin SDK.

The project addresses four failure modes common in personal agents:

- an attachment is acknowledged before parsing finishes;
- an image model returns a refusal or upload instruction that is mistaken for analysis;
- an older document with the same filename overrides the newest receipt;
- credentials or session material are accidentally promoted into long-term memory.

## Data Flow

```text
chat attachment
  -> validate bytes and filename
  -> archive immutable original + SHA-256 receipt
  -> parse or run bounded vision fallback
  -> persist digest-bound parsed text
  -> invoke an optional RAG index callback
  -> expose newest-version context to the agent
  -> promote durable facts through version-aware memory
```

The archive ledger groups records by normalized original filename. A `current` record is selected by the direct receipt timestamp, and its parsed content is loaded only from the matching digest. Older same-name content is omitted unless the user explicitly requests history.

## Supported Formats

| Family | Extensions | Behavior |
|---|---|---|
| Text | TXT, Markdown | Encoding-aware plain-text extraction |
| Web | HTML, HTM | Visible text extraction; scripts and styles removed |
| Word | DOCX | Paragraphs and tables |
| Legacy Word | DOC | Read-only conversion through LibreOffice or Microsoft Office |
| Sheets | XLSX, XLSM, CSV, TSV | Sheet-aware Markdown tables with row limits |
| Legacy Sheets | XLS | Read-only conversion through LibreOffice or Microsoft Office |
| Slides | PPTX, PPTM | Slide text and tables |
| Legacy Slides | PPT | Read-only conversion through LibreOffice or Microsoft Office |
| PDF | PDF | Native text first; optional bounded page rendering for scanned pages |
| Images | PNG, JPEG, WebP, GIF, BMP, TIFF | Image validation plus a required semantic vision callback |

Legacy Office support requires either LibreOffice on `PATH` or the `windows-office` extra with locally installed Microsoft Office. Image understanding never pretends success without a configured vision callback. Scanned-PDF vision requires the `pdf-vision` extra.

## Quick Start

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps -e .
```

On Windows, use `.venv\Scripts\python.exe` instead.

```python
from pathlib import Path

from langbot_unified_pipeline import AttachmentPipeline, ParserConfig


def index_document(document_id: str, text: str, metadata: dict) -> None:
    # Replace with a local LangRAG, Chroma, or other index adapter.
    print(document_id, metadata["name"], len(text))


pipeline = AttachmentPipeline(
    Path("runtime-data"),
    parser_config=ParserConfig(),
    indexer=index_document,
)

receipt = pipeline.ingest("notes.txt", b"A durable project note")
context = pipeline.context_for_query("What was in notes.txt?")
```

For images, provide primary and optional fallback callbacks. Both outputs are validated; refusals, upload instructions, empty output, and high-overlap prompt echoes are rejected.

```python
config = ParserConfig(
    vision_primary=lambda image, mime, prompt: call_your_model(image, mime, prompt),
    vision_fallback=lambda image, mime, prompt: call_backup_model(image, mime, prompt),
)
```

## LangBot Integration

For the ready-to-install plugin, use `KaiserIIII/UnifiedAttachmentPipeline` from LangBot Space or build the package from `langbot_plugin/`. The notes below describe lower-level custom integration with this core library.

Use the pipeline at the inbound-message boundary:

1. Decode each file or image component.
2. Call `ingest` and wait for its parse result before the first model response.
3. Put successful current-turn parsed text in a highest-priority context block.
4. On later turns, call `context_for_query` before generic RAG retrieval.
5. Keep the archive-ledger block ahead of generic retrieval results and instruct the model that current digest-bound evidence wins.

The `indexer` callback is deliberately narrow so an installation can connect LangRAG, Chroma, BM25, or another local index without embedding deployment-specific identifiers in this repository.

## Long-Term Memory

`VersionedMemoryStore` keeps every fact revision while marking only the newest timestamp as current. Older facts remain available for historical questions. Credential-shaped content is rejected before a database write.

```python
from langbot_unified_pipeline import VersionedMemoryStore

memory = VersionedMemoryStore("runtime-data/memory.db")
memory.remember("study.destination", "Current preference is undecided")
current = memory.current("study.destination")
```

## Security Model

- Originals are immutable and addressed by SHA-256.
- Paths are confined beneath the configured archive root.
- Parsed document content is untrusted data, never executable instructions.
- Corrupt, encrypted, empty, oversized, unsupported, and invalid-vision inputs fail closed.
- API keys, bearer tokens, JWTs, cookies, sessions, and passwords are excluded from memory.
- The example configuration contains placeholders only.

If an external model is used for vision or answer generation, selected private content leaves the local machine. Configure that boundary deliberately. See [SECURITY.md](SECURITY.md).

## Development

```bash
python -m pip install -e ".[test,pdf-vision]"
pytest --cov=langbot_unified_pipeline --cov-report=term-missing
```

Tests generate anonymous documents in memory. No chat export, user attachment, database, local path, account identifier, endpoint, or model configuration is included.

## Provenance and License

This repository is an independent implementation. It does not redistribute the GeneralParsers source because the reviewed upstream snapshot did not contain a recognized license. LangBot compatibility was reviewed against the Apache-2.0 project listed in [NOTICE](NOTICE).

Released under the Apache License 2.0.
