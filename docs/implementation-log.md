# 实现日志

本文档记录整个文献综述流水线的实现过程，包含每步的操作细节、设计决策理由、关键代码解释，以及 CCPM 各阶段的实际应用说明。

---

## CCPM 工作流概述

CCPM（Claude Code Project Manager）是一个基于文件的项目管理 skill，将软件交付分为 5 个阶段：

| 阶段 | 做什么 | 产出 |
|------|--------|------|
| **Plan** | 头脑风暴 → 写 PRD | `.claude/prds/<name>.md` |
| **Structure** | PRD → Epic → Tasks | `.claude/epics/<name>/epic.md` + 任务文件 |
| **Sync** | 推送到 GitHub Issues | GitHub issues + `github-mapping.md` |
| **Execute** | 逐个/并行执行任务 | 代码、配置、文档 |
| **Track** | 跟踪进度、standup | 状态报告 |

核心理念：**需求存在文件里，不在脑子里。** 每个功能从 PRD 开始，变成技术 Epic，分解为 GitHub Issues，由 agent 执行，全程可追溯。

---

## Plan 阶段：PRD 编写

### 做了什么

通过多轮对话确认需求，产出 `.claude/prds/literature-review-pipeline.md`。

### CCPM 操作说明

1. **Preflight 检查**：确认 `.claude/prds/` 目录存在，feature name 是 kebab-case
2. **头脑风暴**：向用户提问 5 个关键问题（问题定义、交互模式、筛选策略、规模、边界）
3. **写 PRD**：按模板填充所有 section，确保无占位符文本
4. **质量门**：User Stories 有验收标准，Success Criteria 可量化，Out of Scope 明确列出

### 关键决策

| 决策 | 选项 | 选择 | 理由 |
|------|------|------|------|
| 核心问题 | 管理混乱 / 端到端自动化 | 手动综述太慢 | 用户明确表示效率是第一痛点 |
| 交互模式 | CLI 单次 / 分步 / 对话式 | 分步交互 | 用户需要在每步之间有控制权 |
| 筛选方式 | 全自动 / 人工 / 混合 | 全自动 | 减少人工干预，提高效率 |
| 论文规模 | 3-5 / 5-15 / 15-30 | 15-30 篇 | 中大规模系统性综述 |

---

## Structure 阶段：Epic 分解

### 做了什么

将 PRD 转为技术 Epic（`.claude/epics/literature-review-pipeline/epic.md`），然后分解为 8 个任务文件。

### CCPM 操作说明

1. **PRD → Epic**：读取 PRD，产出技术实现方案，包含架构决策、技术方案、任务预览
2. **Epic → Tasks**：每个任务一个 `.md` 文件，包含 frontmatter（status、depends_on、parallel）和正文（Description、Acceptance Criteria、Technical Details）
3. **并行化分析**：标记哪些任务可以并行执行（`parallel: true`），哪些有依赖关系

### 任务依赖图

```
#2 安装依赖
  └→ #3 创建 MCP server
       └→ #4 配置 opencode.json
            ├→ #5 重写 search-agent     ┐
            ├→ #6 重写 literature-reviewer│ 并行
            └→ #7 重写 synthesis-agent   ┘
                 └→ #9 端到端测试

#8 编写文档（贯穿全程）
```

### 重构决策

第一版方案有 5 个 agent（含 filter-agent、fetch-agent、orchestrator），经过讨论重构为：

| 变更 | 理由 |
|------|------|
| 去掉 filter-agent | 筛选合并到 search-agent，减少 agent 数量 |
| 去掉 fetch-agent | 下载由 MCP tool 处理，不需要 LLM 推理 |
| 去掉 orchestrator | 用户手动触发各步骤，保持简单 |
| 新增 MCP server | 确定性工作下沉，减少 token 消耗 |
| marker-pdf 替代 LLM 直读 PDF | 全文不截断，转换质量更高 |

---

## Sync 阶段：GitHub 同步

### 做了什么

将 Epic 和 8 个 Tasks 推送到 GitHub Issues（#1-#9），创建 labels，重命名本地文件。

### CCPM 操作说明

1. **安全检查**：确认 remote 不是 CCPM 模板仓库
2. **创建 labels**：`epic`、`epic:literature-review-pipeline`、`feature`、`task`
3. **创建 Epic issue**：strip frontmatter，用 `gh issue create` 推送
4. **创建 Task issues**：逐个推送，打上 `task` 和 `epic:*` label
5. **重命名文件**：`001.md` → `2.md`（对应 GitHub issue #2）
6. **更新 frontmatter**：写入 `github:` URL 和真实的 `depends_on` issue 号
7. **创建 github-mapping.md**：记录本地文件与 GitHub issue 的映射关系

### 遇到的问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `gh issue create --json` 报错 | gh CLI 版本不支持 `--json` flag | 改为解析返回的 URL 提取 issue number |
| macOS `sed -i` 报错 | macOS sed 的 `-i` 需要备份后缀，`\c` 语法不同 | 改用 Edit 工具直接修改文件 |

---

## Execute 阶段：任务执行

### 任务 #2：安装依赖

**做了什么**：
```bash
mkdir -p mcp-server data/search-results data/papers-md
pip install marker-pdf fastmcp httpx
```

**为什么选这些依赖**：

| 依赖 | 作用 | 选型理由 |
|------|------|----------|
| marker-pdf | PDF → Markdown 转换 | 基于深度学习，转换质量最高，支持表格和公式 |
| fastmcp | Python MCP server 框架 | 官方推荐，API 简洁，支持 stdio 传输 |
| httpx | 异步 HTTP 客户端 | 支持 async/await，比 requests 更适合并发场景 |

**marker-pdf 的依赖链**：marker-pdf 自动安装了 PyTorch（~80MB wheel）、surya-ocr（OCR 引擎）、transformers 等。首次运行时还会下载模型文件（~1GB）。

**验证**：
```python
import marker   # OK
import fastmcp  # OK
import httpx    # OK
```

### 任务 #3：创建 MCP server

**做了什么**：创建 `mcp-server/server.py`，实现 3 个 tool。

**FastMCP 核心 API 解释**：

```python
from fastmcp import FastMCP, Context

# 创建 server 实例
# name 会显示在 OpenCode 的 MCP 连接列表中
mcp = FastMCP(name="literature-tools")

# 用装饰器注册 tool
# FastMCP 自动从类型注解生成 JSON Schema
# Context 参数会被自动注入，不暴露给调用方
@mcp.tool
async def search_papers(
    keywords: str,          # → JSON Schema: {"type": "string"}
    limit: int = 30,        # → {"type": "integer", "default": 30}
    year_from: int | None = None,  # → {"type": "integer", "nullable": true}
    ctx: Context = None,    # 自动注入，不出现在 schema 中
) -> str:
    """Search academic papers."""  # → tool 的 description
    ...
    return json.dumps(result)  # 返回字符串给调用方

# stdio 传输：通过 stdin/stdout 与 OpenCode 通信
if __name__ == "__main__":
    mcp.run(transport="stdio")
```

**search_papers 实现要点**：

1. **并行查询**：用 `asyncio.gather` 同时查 Semantic Scholar 和 arXiv
2. **Semantic Scholar API**：
   - Endpoint: `GET /graph/v1/paper/search`
   - 支持 `S2_API_KEY` 环境变量避免限流
   - 429 时指数退避重试 3 次
3. **arXiv API**：
   - Endpoint: `GET /api/query`（返回 Atom XML）
   - 用正则解析 XML（避免引入 lxml 依赖）
4. **去重**：DOI 精确匹配 + 标题归一化后比较

**download_paper 实现要点**：
- `follow_redirects=True`：arXiv PDF URL 会 302 重定向
- 验证响应是 PDF（检查 content-type 和 `%PDF-` 文件头）
- 已存在的文件自动跳过（幂等性）
- 每次下载后 `asyncio.sleep(2)` 限流

**convert_pdf 实现要点**：
- 用 marker-pdf 的 Python API 而非 CLI（更灵活）
- `PdfConverter` + `create_model_dict()` 初始化转换器
- `text_from_rendered()` 提取 Markdown 文本
- 同步函数（非 async），FastMCP 自动在线程池中运行

### 任务 #4：配置 opencode.json

**做了什么**：在项目根目录创建 `opencode.json`。

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

**配置解释**：
- `$schema`：JSON Schema 验证，IDE 可提供自动补全
- `mcp.literature-tools`：server 名称，与 `FastMCP(name=...)` 对应
- `type: "local"`：stdio 传输，OpenCode 启动子进程
- `command`：启动命令，OpenCode 用 `spawn` 执行
- `enabled: true`：启动时自动连接

**OpenCode 如何使用 MCP**：
1. OpenCode 启动时读取 `opencode.json`
2. 对每个 `enabled: true` 的 MCP server，执行 `command` 启动子进程
3. 通过 stdin/stdout 与子进程通信（JSON-RPC 协议）
4. Agent 可在指令中调用 MCP tool，就像调用内置工具一样

### 任务 #5：重写 search-agent

**做了什么**：重写 `.opencode/agents/search-agent.md`。

**关键变化 vs V1**：
- V1：agent 自己用 webfetch 调 API → 消耗大量 token 解析响应
- V2：agent 调 MCP tool 拿结构化 JSON → LLM 只做评分筛选

**评分模型设计**：
```
总分 = 0.4×相关性 + 0.2×引用量 + 0.2×年份 + 0.2×来源质量
```
- 相关性权重最高（40%）：这是文献综述最核心的维度
- 引用量、年份、来源质量各 20%：辅助维度，避免遗漏高质量但低引用的新论文

### 任务 #6：重写 literature-reviewer

**关键变化 vs V1**：
- V1：读 `data/papers/` 下的 PDF → LLM 上下文截断
- V2：读 `data/papers-md/` 下的 Markdown → 全文保留，不截断
- 新增 abstract-only 模式：文件名含 `-abstract` 的论文基于摘要提取
- 新增 `paper_path` 参数：支持指定单篇，便于并行调用

### 任务 #7：重写 synthesis-agent

**关键变化 vs V1**：
- V1：直接读所有笔记一次性综合 → 15-30 篇可能超出上下文
- V2：分批处理策略（快速扫描 → 主题分组 → 逐组分析 → 跨组综合）
- 新增"方法论趋势"小节
- 对比表增加维度（Year、Limitations）
- 研究建议从 3-5 条扩展到 5-8 条
- 综述长度随论文数量适配

---

## Track 阶段：进度跟踪

CCPM 提供了一系列 bash 脚本用于跟踪进度：

| 命令 | 作用 |
|------|------|
| `bash .opencode/skills/ccpm/references/scripts/status.sh` | 项目总体状态 |
| `bash .opencode/skills/ccpm/references/scripts/standup.sh` | 每日站会报告 |
| `bash .opencode/skills/ccpm/references/scripts/in-progress.sh` | 正在进行的任务 |
| `bash .opencode/skills/ccpm/references/scripts/next.sh` | 下一个要做的任务 |
| `bash .opencode/skills/ccpm/references/scripts/blocked.sh` | 被阻塞的任务 |

任务完成时：
1. 更新本地文件 frontmatter：`status: closed`
2. 在 GitHub issue 上发评论并关闭
3. 更新 Epic 的 progress 百分比

---

## 技术选型总结

| 选择 | 备选方案 | 为什么选它 |
|------|----------|-----------|
| marker-pdf | PyMuPDF / pdfplumber / poppler | 基于深度学习，表格和公式转换质量最高 |
| FastMCP | 自写 MCP server / OpenCode plugin | 官方推荐框架，API 最简洁 |
| httpx | requests / aiohttp | 原生 async 支持，与 FastMCP 配合好 |
| MCP server | Python 脚本 / 纯 agent | 标准协议，tool 可被任何 agent 调用，减少 token |
| 分步交互 | orchestrator agent | 更简单，用户控制权更大 |
| CCPM | 手动管理 / GitHub Projects | 文件驱动，与代码同仓库，全程可追溯 |
