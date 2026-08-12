# Unified Attachment Pipeline for LangBot

[简体中文](readme/README_zh_Hans.md)

An installable LangBot Parser plugin for reliable document extraction and semantic image understanding. It gives LangBot one consistent attachment path for local files and uses configured vision models only when an image or scanned PDF page needs visual analysis.

## Supported files

- Text and web: TXT, Markdown, HTML
- Word: DOCX and legacy DOC
- Spreadsheets: XLSX, XLSM, XLS, CSV, TSV
- Presentations: PPTX, PPTM and legacy PPT
- Documents: native and scanned PDF
- Images: PNG, JPEG, WebP, GIF, BMP and TIFF

Modern documents are parsed locally. Images and low-text PDF pages use the selected primary vision model; connection errors, timeouts, refusals, upload instructions, empty responses, and prompt echoes automatically fall through to the selected fallback model.

## Installation

Install `KaiserIIII/UnifiedAttachmentPipeline` from LangBot Space, then enable its Parser component for the target knowledge base or ingestion flow.

For a local package build:

```powershell
cd langbot_plugin
python -m langbot_plugin.cli build -o dist
```

## Configuration

1. Keep **Enable vision** on when images or scanned PDFs must be understood.
2. Select a vision-capable **Primary vision model**.
3. Select a different **Fallback vision model** if the primary gateway can be unavailable.
4. Adjust timeouts and limits only for unusually large files or slow providers.

If no visual model is configured, image parsing fails explicitly instead of pretending that the image was understood. Text-bearing documents do not require an LLM.

## Privacy and security

Document bytes remain local for native parsing. Images and rendered scanned-PDF pages are sent to the LangBot model selected in plugin settings, so that model provider receives those visual inputs. File content is untrusted data and is never treated as executable instructions.

No deployment endpoint, model UUID, API key, chat export, attachment, personal knowledge, or runtime database is included in this package.

## Architecture

The plugin is a thin adapter over the Apache-2.0 [`langbot-unified-attachment-pipeline`](https://github.com/KaiserIIII/langbot-unified-attachment-pipeline) core. The matching core source is bundled in the package so installation does not depend on a live Git checkout. GeneralParsers source is not copied or redistributed.

## License

Apache License 2.0. See the repository `LICENSE` and this package's `NOTICE`.
