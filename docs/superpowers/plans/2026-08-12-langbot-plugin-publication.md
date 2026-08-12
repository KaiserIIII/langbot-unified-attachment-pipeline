# LangBot Plugin Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add, verify, package, and publish an installable LangBot Parser plugin with async visual parsing and correct GitHub attribution.

**Architecture:** Preserve the synchronous framework-neutral core and add an awaitable parser path for LangBot model calls. Build a self-contained market package under `langbot_plugin/` with a thin SDK adapter and a vendored copy of the repository's Apache-2.0 core.

**Tech Stack:** Python 3.11+, pytest, LangBot Plugin SDK 0.5.0, PyYAML, python-docx, openpyxl, python-pptx, pypdf, pypdfium2, Pillow, BeautifulSoup.

## Global Constraints

- Do not rewrite existing Git history.
- Attribute new commits to `KaiserIIII <1727168348@qq.com>`.
- Do not redistribute GeneralParsers source.
- Do not include personal knowledge, local configurations, tokens, credentials, or private paths.
- Root market README is English; Simplified Chinese is `readme/README_zh_Hans.md`.
- Preserve the existing synchronous public API.
- Use test-first red-green cycles for production behavior.

---

### Task 1: Async Vision and Parsing Core

**Files:**
- Modify: `src/langbot_unified_pipeline/vision.py`
- Modify: `src/langbot_unified_pipeline/parsers.py`
- Modify: `src/langbot_unified_pipeline/__init__.py`
- Test: `tests/test_async_parsers.py`

**Interfaces:**
- Produces: `AsyncVisionCallback = Callable[[bytes, str, str], Awaitable[str]]`
- Produces: `parse_attachment_async(data: bytes, filename: str, config: AsyncParserConfig | None = None) -> Awaitable[ParseResult]`

- [ ] Write tests for image parsing, fallback, invalid output, scanned PDF, and ordinary documents.
- [ ] Run the new tests and confirm failure because the async API is absent.
- [ ] Add the minimal async vision runner and parser path without changing synchronous behavior.
- [ ] Run focused async and synchronous parser tests.
- [ ] Commit the independently passing async core.

### Task 2: LangBot Parser Adapter and Manifest

**Files:**
- Create: `langbot_plugin/manifest.yaml`
- Create: `langbot_plugin/main.py`
- Create: `langbot_plugin/components/unified_attachment_parser/parser.py`
- Create: `langbot_plugin/components/unified_attachment_parser/parser.yaml`
- Create: `langbot_plugin/tests/test_plugin.py`
- Create: `langbot_plugin/requirements.txt`
- Create: `langbot_plugin/.gitignore`

**Interfaces:**
- Consumes: `parse_attachment_async`
- Produces: `UnifiedAttachmentParser.parse(context: ParseContext) -> Awaitable[langbot ParseResult]`

- [ ] Write failing SDK contract tests for manifest loading, MIME resolution, result mapping, and vision fallback.
- [ ] Run focused tests and confirm expected missing-plugin failures.
- [ ] Implement the plugin entry point, Parser component, model invocation, and manifest.
- [ ] Vendor the project's own core package into the market package.
- [ ] Run SDK contract tests and the full core suite.
- [ ] Commit the installable adapter.

### Task 3: Marketplace Documentation and Package Build

**Files:**
- Create: `langbot_plugin/README.md`
- Create: `langbot_plugin/readme/README_zh_Hans.md`
- Create: `langbot_plugin/assets/icon.svg`
- Create: `langbot_plugin/LICENSE`
- Create: `langbot_plugin/NOTICE`
- Modify: `README.md`
- Modify: `README.zh-CN.md`

**Interfaces:**
- Produces: `dist/KaiserIIII-UnifiedAttachmentPipeline-0.2.0.lbpkg`

- [ ] Document installation, supported formats, visual model fallback, privacy boundary, and LangBot configuration in both languages.
- [ ] Build with `python -m langbot_plugin.cli build -o dist` from `langbot_plugin/`.
- [ ] Inspect every package member and validate manifest discovery and imports.
- [ ] Run repository and package privacy scans.
- [ ] Commit packaging and documentation.

### Task 4: End-to-End Verification and Publication

**Files:**
- Modify only files required by verified test or packaging defects.

**Interfaces:**
- Consumes: validated `.lbpkg`
- Produces: pushed GitHub commit and LangBot Space submission.

- [ ] Run the complete test suite with coverage.
- [ ] Run isolated wheel installation tests for supported Python versions available locally.
- [ ] Run LangBot SDK parser smoke tests across common file families and visual fallback.
- [ ] Push `main` to the existing public GitHub repository.
- [ ] Verify remote SHA, CI state, public README, privacy scan, and Contributors API.
- [ ] Check LangBot Space authentication and publish the package when authenticated.
- [ ] Report the exact marketplace status as draft, under review, approved, or blocked by login.
