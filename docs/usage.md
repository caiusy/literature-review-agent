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

如果你要查 **BEV 检测**，推荐就这样说：

```text
搜索 bev detection 相关论文，query_slug 用 bev-detection，时间范围 2021 之后，保留 15 篇
```

然后下一步：

```text
阅读 query_slug=bev-detection 的所有论文并提取笔记
```

最后：

```text
generate / synthesize query_slug=bev-detection 的文献综述
```

## 3. 三步流水线

### 第一步：搜索 + 下载 + 转 Markdown

你对我说：

```text
搜索 bev detection 相关论文，query_slug 用 bev-detection，时间范围 2021 之后，保留 15 篇
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
