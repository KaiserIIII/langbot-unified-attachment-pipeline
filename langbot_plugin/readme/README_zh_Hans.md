# LangBot 统一附件流水线

[English](../README.md)

这是一个可直接安装的 LangBot Parser 插件，用一条稳定的流水线完成文档提取和图片语义识别。普通文档在本地解析；只有图片或扫描 PDF 页面需要视觉理解时，才会调用你在 LangBot 中配置的视觉模型。

## 支持格式

- 文本与网页：TXT、Markdown、HTML
- Word：DOCX 和旧版 DOC
- 表格：XLSX、XLSM、XLS、CSV、TSV
- 演示文稿：PPTX、PPTM 和旧版 PPT
- 文档：原生 PDF 和扫描 PDF
- 图片：PNG、JPEG、WebP、GIF、BMP、TIFF

主视觉模型发生连接错误、超时，或者返回拒绝语、上传提示、空内容、提示词复述时，插件会自动调用备用视觉模型。识别结果会同时描述物体、场景、布局、对象关系和可读文字，不只是 OCR。

## 安装

从 LangBot Space 安装 `KaiserIIII/UnifiedAttachmentPipeline`，然后在目标知识库或摄入流程中启用它的 Parser 组件。

本地构建：

```powershell
cd langbot_plugin
python -m langbot_plugin.cli build -o dist
```

## 配置

1. 需要识别图片或扫描 PDF 时保持“启用视觉解析”。
2. 选择一个支持图片输入的“主视觉模型”。
3. 如果免费网关偶尔不可用，再选择一个不同的“备用视觉模型”。
4. 只有文件特别大或模型特别慢时，才需要调整超时和数量限制。

没有配置视觉模型时，图片解析会明确失败，不会假装已经看懂。带文字的常见文档不需要调用大模型。

## 隐私与安全

普通文档的解析留在本机。图片和扫描 PDF 渲染页会发送给插件设置中选中的 LangBot 模型，因此相应模型提供商会接收这些视觉输入。文件内容始终被当作不可信数据，不会作为可执行指令。

插件包不包含部署地址、模型 UUID、API 密钥、聊天导出、真实附件、个人知识或运行数据库。

## 架构与许可证

插件是 Apache-2.0 开源核心 [`langbot-unified-attachment-pipeline`](https://github.com/KaiserIIII/langbot-unified-attachment-pipeline) 的轻量 LangBot 适配层，并在安装包中附带匹配版本的核心源码，安装不依赖在线 Git 拉取。项目没有复制或再分发 GeneralParsers 源码。

使用 Apache License 2.0，详见仓库 `LICENSE` 和插件 `NOTICE`。
