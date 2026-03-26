# 系统架构文档

## 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户（OpenCode 对话）                    │
│                                                         │
│  "搜索 X 主题"    "阅读论文"    "生成综述"                    │
└────┬──────────────────┬──────────────────┬──────────────┘
     │                  │                  │
     ▼                  ▼                  ▼
┌─────────┐     ┌──────────────┐    ┌──────────────┐
│ search  │     │  literature  │    │  synthesis   │
│ -agent  │     │  -reviewer   │    │  -agent      │
│         │     │              │    │              │
│ 检索+筛选 │     │ 阅读+提取笔记  │    │ 对比+生成综述  │
│ +下载+转换│     │              │    │              │
└────┬────┘     └──────┬───────┘    └──────┬───────┘
     │                 │                   │
     │ 调用 MCP tools   │ 读文件             │ 读文件
     ▼                 ▼                   ▼
┌─────────────────────────────────────────────────────────┐
│                   文件系统（数据层）                        │
│                                                         │
│  data/search-results/   检索和筛选结果                     │
│  data/papers/           原始 PDF 存档                     │
│  data/papers-md/        marker-pdf 转出的 Markdown         │
│  data/notes/            每篇论文的结构化笔记                 │
│  outputs/               最终综述报告                       │
└────▲────────────────────────────────────────────────────┘
     │
     │ search_papers / download_paper / convert_pdf
     │
┌────┴────────────────────────────────────────────────────┐
│              MCP Server (literature-tools)               │
│              mcp-server/server.py                        │
│                                                         │
│  ┌──────────────┐ ┌───────────────┐ ┌────────────────┐  │
│  │search_papers │ │download_paper │ │ convert_pdf    │  │
│  │              │ │               │ │                │  │
│  │ Semantic     │ │ httpx 下载     │ │ marker-pdf     │  │
│  │ Scholar API  │ │ PDF 文件       │ │ PDF→Markdown   │  │
│  │ + arXiv API  │ │               │ │                │  │
│  └──────────────┘ └───────────────┘ └────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 设计原则

**确定性工作下沉，推理性工作上浮。**

- MCP Server 处理不需要 LLM 推理的工作：API 调用、文件下载、格式转换
- Agent 处理需要 LLM 推理的工作：相关性评估、信息提取、综述撰写
- 这样做的好处：减少 token 消耗，提高可靠性，中间产物可复用

## 数据流

```
用户输入关键词
    │
    ▼
search-agent
    ├─ 调用 MCP:search_papers(keywords) ──→ data/search-results/raw.json
    ├─ LLM 评分筛选 ──→ data/search-results/filtered.md
    ├─ 调用 MCP:download_paper(×N) ──→ data/papers/*.pdf
    ├─ 调用 MCP:convert_pdf(×N) ──→ data/papers-md/*.md
    └─ 生成状态报告 ──→ data/search-results/fetch-status.md
    │
    ▼ 用户确认
    │
literature-reviewer
    ├─ 读取 data/papers-md/*.md
    └─ 生成笔记 ──→ data/notes/*.md
    │
    ▼ 用户确认
    │
synthesis-agent
    ├─ 读取 data/notes/*.md
    └─ 生成综述 ──→ outputs/review-overview.md
```

## 目录结构

```
literature-review-agent/
├── opencode.json                  # MCP server 注册配置
├── mcp-server/
│   ├── server.py                  # FastMCP server（3 个 tool）
│   └── requirements.txt           # Python 依赖
├── .opencode/
│   ├── agents/
│   │   ├── search-agent.md        # 检索 + 筛选 + 下载 + 转换
│   │   ├── literature-reviewer.md # 阅读 Markdown + 提取笔记
│   │   └── synthesis-agent.md     # 综合对比 + 生成综述
│   └── skills/ccpm/               # CCPM 项目管理 skill
├── .claude/                       # CCPM 管理文件
│   ├── prds/                      # 产品需求文档
│   └── epics/                     # Epic 和 Task 文件
├── data/
│   ├── search-results/            # 检索和筛选结果
│   ├── papers/                    # 原始 PDF 存档（不删除）
│   ├── papers-md/                 # marker-pdf 转出的 Markdown
│   └── notes/                     # 每篇论文的结构化笔记
├── outputs/                       # 最终综述报告
└── docs/
    ├── architecture.md            # 本文件
    └── implementation-log.md      # 实现过程记录
```

## 组件详解

### MCP Server (`mcp-server/server.py`)

用 FastMCP 框架实现的 stdio 传输 MCP server。OpenCode 启动时自动拉起，agent 可直接调用其 tool。

#### tool: search_papers

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| keywords | str | 必填 | 搜索关键词 |
| limit | int | 30 | 每个来源的最大结果数 |
| year_from | int \| None | None | 起始年份过滤 |

**返回**：JSON 字符串，包含：
- `query`: 搜索关键词
- `sources`: 查询的来源列表
- `total_before_dedup` / `total_after_dedup`: 去重前后数量
- `errors`: 错误信息列表
- `papers`: 论文对象数组，每项含 id/title/authors/year/venue/citations/abstract/url/source/open_access_url/doi/arxiv_id

**实现细节**：
- 并行查询 Semantic Scholar API 和 arXiv API
- Semantic Scholar 支持 `S2_API_KEY` 环境变量，429 时自动重试 3 次（指数退避）
- 去重策略：DOI 精确匹配 + 标题归一化（小写、去标点、合并空格）后比较

#### tool: download_paper

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| paper_id | str | 必填 | 论文 ID（用作文件名） |
| url | str | 必填 | PDF 直链 |
| output_dir | str | "data/papers" | 保存目录 |

**返回**：JSON 字符串，含 status (success/skipped/failed)、path、size_bytes。

**实现细节**：
- 已存在的文件自动跳过
- 验证响应是否为 PDF（检查 content-type 和文件头）
- 每次下载后暂停 2 秒避免限流

#### tool: convert_pdf

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| pdf_path | str | 必填 | PDF 文件路径 |
| output_dir | str | "data/papers-md" | 输出目录 |

**返回**：JSON 字符串，含 status、path、chars（字符数）、images（图片数）。

**实现细节**：
- 使用 marker-pdf 的 Python API（PdfConverter）
- 首次运行会自动下载模型（约 1GB）
- 已转换的文件自动跳过
- 完整保留论文全文，不截断

### Agent: search-agent

**触发方式**：用户在对话中说"搜索 X 主题"或类似指令。

**工作流**：
1. 调用 `search_papers` MCP tool 获取候选列表
2. LLM 对每篇论文进行四维度评分（相关性 40%、引用量 20%、年份 20%、来源质量 20%）
3. 按总分排序，保留 Top 15-30 篇
4. 对每篇调用 `download_paper` → `convert_pdf`
5. 生成筛选报告和下载状态报告

**输出文件**：
- `data/search-results/raw.json`
- `data/search-results/filtered.md`
- `data/search-results/fetch-status.md`
- `data/papers/*.pdf`
- `data/papers-md/*.md`

### Agent: literature-reviewer

**触发方式**：用户在对话中说"阅读论文"或类似指令。

**工作流**：
1. 扫描 `data/papers-md/` 目录
2. 跳过已有笔记的论文
3. 逐篇阅读 Markdown 全文，提取 9 字段结构化笔记
4. abstract-only 论文标注信息不完整

**输出文件**：`data/notes/*.md`

### Agent: synthesis-agent

**触发方式**：用户在对话中说"生成综述"或类似指令。

**工作流**：
1. 读取所有 `data/notes/*.md`
2. 快速扫描提取标题+方法做主题分组
3. 逐组深入分析
4. 跨组综合
5. 生成对比表和研究建议

**输出文件**：`outputs/review-overview.md`

## OpenCode 配置

`opencode.json` 注册 MCP server：

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "literature-tools": {
      "type": "local",
      "command": ["python3", "mcp-server/server.py"],
      "enabled": true
    }
  }
}
```

- `type: "local"` 表示 stdio 传输，OpenCode 启动子进程运行 server
- `command` 指定启动命令
- OpenCode 重启后自动连接 MCP server，agent 即可调用 tool

## 典型使用流程

```
1. 用户: "搜索 efficient LLM fine-tuning 相关论文"
   → search-agent 执行，产出筛选后的论文列表和 Markdown 文件

2. 用户: 查看 data/search-results/filtered.md，确认论文列表
   → 可手动增删论文

3. 用户: "阅读所有论文并提取笔记"
   → literature-reviewer 执行，产出结构化笔记

4. 用户: 查看 data/notes/，确认笔记质量
   → 可手动修改笔记

5. 用户: "生成文献综述"
   → synthesis-agent 执行，产出最终综述报告

6. 用户: 查看 outputs/review-overview.md
   → 在此基础上编辑正式综述
```
