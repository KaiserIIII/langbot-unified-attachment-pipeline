# LangBot Plugin Publication Design

## Status

Approved through the user's instruction to choose and execute the most suitable LangBot publication approach.

## Objective

Publish the repository as both a framework-neutral attachment parsing library and an installable LangBot Parser plugin owned by `KaiserIIII`. The plugin must parse common text, document, spreadsheet, presentation, PDF, and image formats, including semantic image understanding and scanned-PDF fallback through configured LangBot vision models.

## Architecture

The existing `src/langbot_unified_pipeline` package remains the source of truth for parsing, validation, vision-output filtering, archiving, and version-aware memory. A new async parsing API accepts awaitable vision callbacks while preserving the current synchronous API.

The market package lives under `langbot_plugin/`. It contains a LangBot `BasePlugin` entry point, one `Parser` component, a manifest, localized documentation, an icon, pinned runtime dependencies, and a vendored copy of this repository's own core package. Keeping the market package in a dedicated directory makes `lbp build` deterministic and prevents repository tests, design documents, and development artifacts from entering the `.lbpkg` file.

No GeneralParsers source is redistributed. Its local installation is used only as a behavioral reference because the reviewed snapshot has no recognized license.

## Components

### Async Core Parser

`parse_attachment_async(data, filename, config)` mirrors `parse_attachment`. Non-visual formats use the existing parsers. Image and low-text PDF paths await a primary vision callback and then an optional fallback callback. Vision outputs pass through the existing refusal, upload-instruction, emptiness, and prompt-echo filters.

The synchronous API remains unchanged for current library users and archive ingestion.

### LangBot Parser Adapter

`UnifiedAttachmentParser.parse(ParseContext)`:

1. resolves a usable filename extension from the MIME type when the incoming filename is missing or misleading;
2. reads plugin limits and selected model UUIDs;
3. sends images to the configured primary LangBot vision model and then the configured fallback model;
4. calls the async core parser;
5. maps the internal result into LangBot `ParseResult` and `TextSection` objects;
6. returns explicit parser metadata and raises a clear error when extraction cannot succeed.

Model invocation uses the installed SDK's async `invoke_llm(llm_model_uuid=..., messages=..., extra_args=...)` contract. No event-loop nesting or synchronous blocking bridge is permitted.

### Marketplace Package

The package has an English root `README.md`, Simplified Chinese `readme/README_zh_Hans.md`, `manifest.yaml`, component YAML, Apache-2.0 notices, and `requirements.txt` with exact versions. The manifest author is `KaiserIIII`, repository is the live public GitHub URL, and version is `0.2.0`.

## Data Flow

```text
LangBot ParseContext
  -> MIME/filename normalization
  -> payload and type validation
  -> native document extraction
  -> optional async vision primary/fallback
  -> vision-output sanitation
  -> internal ParseResult
  -> LangBot ParseResult + sections + provenance metadata
  -> LangBot knowledge-engine ingestion
```

## Error Handling

- Empty, oversized, corrupt, encrypted, unsupported, and unparseable inputs fail explicitly.
- Invalid or refusal-like vision output triggers the configured fallback.
- If both visual models fail, the parser reports a bounded extraction error instead of claiming success.
- Model UUIDs and API credentials are configuration only and never included in source, logs, package metadata, or test fixtures.
- Document text is treated as untrusted content and never executed as instructions.

## Testing

Automated tests cover manifest discovery, MIME normalization, TXT, DOCX, XLSX, PPTX, native PDF, images, scanned PDFs, primary-to-fallback vision behavior, invalid visual responses, and LangBot result conversion. Existing core, archive, memory, Windows Office, wheel-isolation, and privacy scans remain green.

The final verification builds the `.lbpkg`, inspects its archive contents, imports it with LangBot SDK 0.5.0, performs parser smoke tests, and scans the repository and package for private identifiers and credential-shaped data. Publishing occurs only after these checks.

## Publication and Attribution

New commits use `KaiserIIII <1727168348@qq.com>` as their Git author. Existing history is not rewritten. After push, the GitHub Contributors API is checked for `KaiserIIII`; if GitHub does not associate the verified email, future commits use GitHub's account-specific noreply address.

`lbp publish` uploads the validated package to LangBot Space as a draft. A draft or review submission is reported accurately and is not described as publicly listed until marketplace approval completes.
