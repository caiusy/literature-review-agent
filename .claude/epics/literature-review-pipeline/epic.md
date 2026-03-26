---
name: literature-review-pipeline
status: in-progress
created: 2026-03-26T14:16:04Z
updated: 2026-03-27T00:35:00Z
progress: 91%
prd: .claude/prds/literature-review-pipeline.md
github: https://github.com/caiusy/literature-review-agent/issues/1
---

# Epic: literature-review-pipeline

## Overview

将现有项目重构为 MCP server 驱动的文献综述流水线。核心设计原则：确定性工作（检索、下载、PDF转换）下沉到 Python MCP server，推理性工作（筛选、阅读理解、综述）由 LLM agent 完成。这样最大化减少 token 消耗，同时保证 PDF 全文不截断。

## Architecture Decisions

1. **MCP server 而非脚本**：把检索/下载/转换封装为 MCP tool，agent 可直接调用，无需手动拼 shell 命令。MCP 是标准协议，可复用。
2. **marker-pdf 而非 LLM 直读 PDF**：marker-pdf 基于深度学习模型，转换质量最高，支持表格和公式。转出 Markdown 后 agent 读文本，不截断。
3. **合并检索+筛选到一个 agent**：减少 agent 数量，search-agent 同时负责调 MCP tool 检索和 LLM 筛选评分。
4. **无 orchestrator**：用户在对话中手动触发各步骤，保持简单，避免过度工程化。
5. **原始 PDF 与 Markdown 分离存储**：data/papers/ 存原始 PDF 存档，data/papers-md/ 存转换后的 Markdown。

## Technical Approach

### 数据流

```
用户输入关键词
    ↓
search-agent 调用 MCP:search_papers → data/search-results/raw.json
    ↓
search-agent LLM 筛选评分 → data/search-results/filtered.md
    ↓
search-agent 调用 MCP:download_paper (×N) → data/papers/*.pdf
    ↓
search-agent 调用 MCP:convert_pdf (×N) → data/papers-md/*.md
    ↓
literature-reviewer 读 data/papers-md/*.md → data/notes/*.md
    ↓
synthesis-agent 读 data/notes/*.md → outputs/review-overview.md
```

### 目录结构

```
literature-review-agent/
├── opencode.json                  # MCP server 配置
├── mcp-server/
│   ├── server.py                  # FastMCP server（3 个 tool）
│   └── requirements.txt           # marker-pdf, httpx, fastmcp
├── .opencode/agents/
│   ├── search-agent.md            # 检索 + 筛选 + 下载 + 转换
│   ├── literature-reviewer.md     # 阅读 Markdown + 提取笔记
│   └── synthesis-agent.md         # 综合对比 + 生成综述
├── data/
│   ├── search-results/            # 检索和筛选结果
│   ├── papers/                    # 原始 PDF 存档
│   ├── papers-md/                 # marker-pdf 转出的 Markdown
│   └── notes/                     # 每篇论文的结构化笔记
├── outputs/                       # 最终综述
└── docs/
    ├── architecture.md            # 系统架构文档
    └── implementation-log.md      # 实现过程教程级记录
```

### MCP Server（mcp-server/server.py）

用 FastMCP 框架，暴露 3 个 tool：

| Tool | 输入 | 输出 | 实现 |
|------|------|------|------|
| search_papers | keywords, limit, year_from | JSON 论文列表 | httpx 并行调 Semantic Scholar + arXiv API，去重 |
| download_paper | paper_id, url, output_dir | 文件路径 | httpx 下载 PDF，2s 间隔限流 |
| convert_pdf | pdf_path, output_dir | Markdown 路径 | marker-pdf Python API 转换 |

### Agent 职责

| Agent | 调用的 MCP tool | LLM 推理工作 | 输出 |
|-------|----------------|-------------|------|
| search-agent | search_papers, download_paper, convert_pdf | 相关性评分、筛选决策 | search-results/, papers/, papers-md/ |
| literature-reviewer | 无 | 阅读 Markdown、提取 9 字段笔记 | notes/*.md |
| synthesis-agent | 无 | 主题分组、对比分析、综述撰写 | outputs/review-overview.md |

## Implementation Strategy

按依赖关系分层实施：

**Layer 0（基础设施）**：安装依赖 → 创建 MCP server → 配置 opencode.json
**Layer 1（agent 层，可并行）**：重写 search-agent / literature-reviewer / synthesis-agent
**Layer 2（文档）**：编写 architecture.md + implementation-log.md
**Layer 3（验证）**：端到端测试

## Task Breakdown Preview

1. 安装依赖（marker-pdf, fastmcp, httpx）
2. 创建 MCP server（3 个 tool）
3. 配置 opencode.json 注册 MCP server
4. 重写 search-agent（调 MCP tool + LLM 筛选）
5. 重写 literature-reviewer（读 Markdown + 提取笔记）
6. 重写 synthesis-agent（大规模支持 + 增强对比表）
7. 编写 architecture.md + implementation-log.md
8. 端到端测试

**并行化**：任务 1→2→3 串行（依赖链）。任务 4/5/6 可并行（互不依赖）。任务 7 贯穿全程。任务 8 最后。

## Dependencies

- Python 3.13.9（已有）
- marker-pdf + PyTorch（需安装）
- fastmcp（需安装）
- httpx（需安装）
- Semantic Scholar API / arXiv API（免费）

## Success Criteria (Technical)

1. MCP server 启动 <5s，3 个 tool 均可调用
2. search_papers 返回 ≥30 篇去重后候选
3. download_paper 对 arXiv 论文成功率 ≥95%
4. convert_pdf 输出完整 Markdown，不截断
5. literature-reviewer 处理 15-30 篇笔记，每篇含 9 字段
6. synthesis-agent 输出含对比表的综述，覆盖所有论文
7. 端到端 ≤30 分钟（15-30 篇）
8. docs/ 达到教程级别

## Estimated Effort

- Layer 0（任务 1-3）：~2 小时
- Layer 1（任务 4-6，并行）：~1.5 小时
- Layer 2（任务 7）：~1 小时（贯穿全程）
- Layer 3（任务 8）：~1 小时
- 总计：~4-5 小时
