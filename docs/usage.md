# 使用方式

## 1. 一个 query 对应一个目录

现在推荐的运行单位是一个 query，例如：

- `bev-detection`
- `efficient-llm-finetuning`
- `multimodal-rag`

每个 query 都有独立目录：

```text
data/queries/<query-slug>/
├── search-results/
├── papers/
├── papers-md/
├── notes/
└── outputs/
```

例如 `bev-detection`：

```text
data/queries/bev-detection/
├── search-results/
├── papers/
├── papers-md/
├── notes/
└── outputs/
```

## 2. 你怎么用

如果你要查 **BEV 检测**，推荐先做单篇测试，就这样说：

```text
搜索 bev detection 相关论文，query_slug 用 bev-detection，时间范围 2021 之后，单篇测试，选 1 篇最合适的开放获取论文
```

然后下一步：

```text
阅读 query_slug=bev-detection 的所有论文并提取笔记
```

最后：

```text
generate / synthesize query_slug=bev-detection 的文献综述
```

如果只是单篇测试，最终产物会是简要总结，而不是多篇对比综述。

## 3. 三步流水线

### 第一步：搜索 + 下载 + 转 Markdown

默认使用 **fast mode** 做 PDF 转 Markdown，适合单篇测试，通常可在 1 分钟内完成转换。
如需更高版面保真度，可改用 layout mode（更慢）。

你对我说：

```text
搜索 bev detection 相关论文，query_slug 用 bev-detection，时间范围 2021 之后，单篇测试，选 1 篇最合适的开放获取论文
```

预期产物：
- `data/queries/bev-detection/search-results/raw.json`
- `data/queries/bev-detection/search-results/filtered.md`
- `data/queries/bev-detection/search-results/fetch-status.md`
- `data/queries/bev-detection/papers/*.pdf`
- `data/queries/bev-detection/papers-md/*.md`

### 第二步：阅读并提取笔记

你对我说：

```text
阅读 query_slug=bev-detection 的所有论文并提取笔记
```

预期产物：
- `data/queries/bev-detection/notes/*.md`

### 第三步：生成综述

你对我说：

```text
生成 query_slug=bev-detection 的文献综述
```

预期产物：
- `data/queries/bev-detection/outputs/review-overview.md`

## 4. 当前说明

我已经为你创建好了示例目录：

- `data/queries/bev-detection/`

后面你每做一个新主题，就新建一个新的 query_slug。
