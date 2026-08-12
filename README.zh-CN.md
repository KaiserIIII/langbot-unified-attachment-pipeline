# LangBot 统一附件流水线

[English](README.md)

这是一个本地优先、与框架解耦的附件摄入和版本化长期记忆核心，面向 LangBot 类个人 Agent，也可以单独使用其中的解析器、归档器、索引回调和 SQLite 记忆库。

仓库的 [`langbot_plugin/`](langbot_plugin/readme/README_zh_Hans.md) 目录包含可直接安装的 LangBot Parser 插件。它把常见格式解析器接入 LangBot，并支持主视觉模型失败后自动调用备用模型，可通过 LangBot Plugin SDK 构建为 `.lbpkg`。

它重点解决四类常见问题：

- 附件尚未解析完成，助手就先回复“已理解”；
- 视觉模型返回拒绝语或“请上传图片”，系统却把它当成识别结果；
- 同名旧文件覆盖最新收到的文件；
- 密钥、Cookie 或会话材料被误写入长期记忆。

## 数据流水线

```text
聊天附件
  -> 校验文件名和字节
  -> 保存不可变原件与 SHA-256 收件记录
  -> 通用解析或受限视觉回退
  -> 保存与摘要绑定的解析文本
  -> 调用可选的 RAG 索引回调
  -> 向 Agent 提供最新版本上下文
  -> 将稳定事实写入版本化长期记忆
```

归档目录按规范化后的原始文件名分组。系统根据直接收件时间选择 `current` 版本，并且只加载与该 SHA-256 匹配的解析文本。除非用户明确询问历史版本，否则同名旧内容不会进入上下文。

## 支持格式

| 类型 | 扩展名 | 行为 |
|---|---|---|
| 文本 | TXT、Markdown | 兼容常见编码的纯文本提取 |
| 网页 | HTML、HTM | 提取可见文本，删除脚本和样式 |
| Word | DOCX | 提取段落和表格 |
| 旧版 Word | DOC | 通过 LibreOffice 或 Microsoft Office 只读转换 |
| 表格 | XLSX、XLSM、CSV、TSV | 按工作表提取 Markdown 表格，并限制最大行数 |
| 旧版表格 | XLS | 通过 LibreOffice 或 Microsoft Office 只读转换 |
| 演示文稿 | PPTX、PPTM | 提取幻灯片文字和表格 |
| 旧版演示文稿 | PPT | 通过 LibreOffice 或 Microsoft Office 只读转换 |
| PDF | PDF | 优先原生文本；扫描页可选受限渲染与视觉识别 |
| 图片 | PNG、JPEG、WebP、GIF、BMP、TIFF | 先验证图片，再调用必需的语义视觉回调 |

旧版 Office 需要 `PATH` 中存在 LibreOffice，或在 Windows 安装 Microsoft Office 并启用 `windows-office` 依赖。未配置视觉回调时，图片会明确失败，不会伪装成“已看懂”。扫描 PDF 的视觉识别需要 `pdf-vision` 依赖。

## 快速开始

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install --no-deps -e .
```

Windows 请使用 `.venv\Scripts\python.exe`。

```python
from pathlib import Path

from langbot_unified_pipeline import AttachmentPipeline, ParserConfig


def index_document(document_id: str, text: str, metadata: dict) -> None:
    # 替换为本地 LangRAG、Chroma 或其他索引适配器。
    print(document_id, metadata["name"], len(text))


pipeline = AttachmentPipeline(
    Path("runtime-data"),
    parser_config=ParserConfig(),
    indexer=index_document,
)

receipt = pipeline.ingest("notes.txt", b"A durable project note")
context = pipeline.context_for_query("What was in notes.txt?")
```

图片可以配置主视觉模型和备用模型。两者的输出都会经过校验；拒绝语、上传指引、空输出和高度重合的提示词复述都会被拒绝。

## 接入 LangBot

需要直接安装时，请在 LangBot Space 使用 `KaiserIIII/UnifiedAttachmentPipeline`，或从 `langbot_plugin/` 目录构建插件包。下面内容用于需要自行编排核心库的低层接入场景。

在入站消息边界调用本流水线：

1. 解码每个文件或图片组件。
2. 调用 `ingest`，在第一次模型回复前等待解析结果。
3. 将成功解析的当前轮内容放入最高优先级上下文。
4. 后续对话先调用 `context_for_query`，再执行通用 RAG 检索。
5. 归档台账必须位于普通检索结果之前，并明确规定当前摘要绑定证据优先。

`indexer` 回调刻意保持精简，因此可以接入 LangRAG、Chroma、BM25 或其他本地索引，而不需要在公开仓库里写入任何部署 ID。

## 长期记忆

`VersionedMemoryStore` 会保留事实的每次修订，但只有时间最新的版本标记为当前事实。旧版本仍可用于历史问题。疑似凭据的内容会在数据库写入前被拒绝。

```python
from langbot_unified_pipeline import VersionedMemoryStore

memory = VersionedMemoryStore("runtime-data/memory.db")
memory.remember("study.destination", "Current preference is undecided")
current = memory.current("study.destination")
```

## 安全边界

- 原始附件不可变，并使用 SHA-256 标识。
- 所有运行数据都限制在配置的归档根目录内。
- 文档内容一律是不可信数据，不能作为工具指令执行。
- 损坏、加密、空白、超限、不支持以及视觉输出无效的输入会失败关闭。
- API 密钥、Bearer Token、JWT、Cookie、会话和密码不会写入记忆。
- 示例配置只包含占位符。

如果使用外部视觉模型或生成模型，被选中的私有上下文会离开本机。请明确配置并理解这一边界。详见 [SECURITY.md](SECURITY.md)。

## 开发与测试

```bash
python -m pip install -e ".[test,pdf-vision]"
pytest --cov=langbot_unified_pipeline --cov-report=term-missing
```

测试只在内存中生成匿名文档。本仓库不包含聊天导出、真实附件、数据库、本机路径、账号 ID、私有端点或模型配置。

## 来源与许可证

本仓库是独立实现。由于审核的 GeneralParsers 上游快照没有可识别许可证，本仓库不复制或再分发其源码。LangBot 兼容性参照 Apache-2.0 项目进行审核，详见 [NOTICE](NOTICE)。

本项目使用 Apache License 2.0 发布。
