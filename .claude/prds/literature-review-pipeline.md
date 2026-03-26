---
name: literature-review-pipeline
description: MCP server 驱动的端到端文献综述流水线：关键词→检索→筛选→PDF下载→全文转Markdown→阅读提取→对比综述
status: backlog
created: 2026-03-26T14:16:04Z
---

# PRD: literature-review-pipeline

## Executive Summary

构建一个 MCP server 驱动的分步交互式文献综述流水线。确定性工作（API 检索、PDF 下载、PDF→Markdown 转换）由 Python MCP server 完成，推理性工作（筛选评估、信息提取、综述撰写）由 LLM agent 完成。用户输入关键词后，分步执行检索→筛选→下载→转换→阅读→综述，每步可介入调整。目标规模 15-30 篇，原始 PDF 完整存档，全文不截断。

全过程使用 CCPM skill 管理，并产出教程级别的实现文档，记录每个组件的工作原理、设计决策和 CCPM 各阶段的实际应用。

## Problem Statement

手动文献综述耗时巨大：多平台检索、逐篇下载、阅读提取、整理对比，15-30 篇规模通常需要数天。

当前项目 V1 仅能处理 1-3 篇已有论文，存在以下问题：
- 无自动检索能力（论文需手动放入 data/papers/）
- agent 直接读 PDF，长论文会被 LLM 上下文截断
- 检索、下载等确定性工作消耗大量 LLM token
- 无筛选机制
- 不支持 15-30 篇规模

## User Stories

1. **作为研究者**，我输入关键词，系统通过 MCP tool 自动从 Semantic Scholar 和 arXiv 检索候选论文，返回结构化结果列表。
   - 验收标准：MCP tool search_papers 返回 30-60 篇候选，含 title/authors/year/abstract/url/citations，保存到 data/search-results/。

2. **作为研究者**，系统自动评估候选论文的相关性并筛选出 Top 15-30 篇，我可以查看筛选结果并手动调整。
   - 验收标准：search-agent 输出 data/search-results/filtered.md，每篇含评分和筛选理由，按分数降序排列。

3. **作为研究者**，系统自动下载筛选后论文的 PDF 全文并存档，然后用 marker-pdf 转为 Markdown 供 agent 阅读。
   - 验收标准：PDF 存入 data/papers/，Markdown 存入 data/papers-md/，不可获取的论文标记为 abstract-only。

4. **作为研究者**，系统逐篇阅读 Markdown 全文（不截断）并提取结构化笔记。
   - 验收标准：每篇论文生成 data/notes/<id>.md，含 9 个标准字段，无虚构内容。

5. **作为研究者**，系统对所有论文进行主题分组和交叉对比，输出包含优劣对比表和研究建议的综述报告。
   - 验收标准：outputs/review-overview.md 包含主题综述、对比表（覆盖所有论文）、5-8 条研究建议。

6. **作为研究者**，我可以在每步之间查看中间结果、调整参数或手动修改文件后继续。
   - 验收标准：每步完成后 agent 报告结果摘要，用户在对话中手动触发下一步。

7. **作为学习者**，我能通过实现文档理解整个系统的架构、每个组件的原理、以及 CCPM 的工作流程。
   - 验收标准：docs/implementation-log.md 记录每步实现细节和 CCPM 阶段标注；docs/architecture.md 包含系统架构图和组件说明。

## Functional Requirements

### FR1: Python MCP Server（3 个 tool）

**tool: search_papers**
- 输入：keywords (string), limit (int, 默认 30), year_from (int, 可选)
- 行为：并行查询 Semantic Scholar API 和 arXiv API，按 DOI/标题去重
- 输出：JSON 数组，每项含 id, title, authors, year, venue, citations, abstract, url, source, open_access_url

**tool: download_paper**
- 输入：paper_id (string), url (string), output_dir (string, 默认 data/papers)
- 行为：下载 PDF 到指定目录，2 秒间隔避免限流
- 输出：下载后的文件路径，或失败原因

**tool: convert_pdf**
- 输入：pdf_path (string), output_dir (string, 默认 data/papers-md)
- 行为：用 marker-pdf 将 PDF 转为 Markdown，完整保留全文
- 输出：生成的 Markdown 文件路径

### FR2: search-agent（检索 + 筛选）
- 调用 search_papers MCP tool 获取候选列表
- LLM 对每篇论文评估相关性（0-10 分），结合引用量、年份、来源质量综合打分
- 保留 Top 15-30 篇，输出筛选报告
- 对筛选后的论文，逐篇调用 download_paper + convert_pdf

### FR3: literature-reviewer（阅读 + 提取）
- 读取 data/papers-md/*.md（Markdown 全文，非 PDF）
- 提取 9 字段结构化笔记：title, authors, year/venue, research question, method, data/benchmark, key findings, limitations, relevance
- 对 abstract-only 论文基于摘要提取，标注信息不完整
- 支持指定单篇论文路径，便于并行调用

### FR4: synthesis-agent（综合 + 综述）
- 读取 data/notes/*.md 全部笔记
- 主题分组 → 组内对比 → 跨组综合
- 输出：主题综述、方法论趋势、对比表（覆盖所有论文）、5-8 条研究建议
- 综述长度随论文数量适配（15-20 篇 1500-2500 词，20-30 篇 2500-3500 词）

### FR5: 分步交互
- 用户在对话中手动触发各 agent（无 orchestrator）
- 典型流程：用户说"搜索 X 主题" → search-agent → 用户确认 → "阅读论文" → literature-reviewer → 用户确认 → "生成综述" → synthesis-agent
- 每步产出持久化到文件，可从任意步骤重跑

### FR6: 教程级文档
- docs/implementation-log.md：按时间顺序记录每步实现，含代码解释和 CCPM 阶段标注
- docs/architecture.md：系统架构图、数据流、组件职责、接口定义

## Non-Functional Requirements

- 单次完整流水线（15-30 篇）≤30 分钟
- 所有中间产物持久化，流程中断可恢复
- 不依赖付费 API（Semantic Scholar 和 arXiv 免费）
- marker-pdf 本地运行，不依赖外部服务
- MCP server 启动时间 <5 秒

## Success Criteria

1. MCP server 的 3 个 tool 均可正常调用
2. 输入关键词后能检索到 ≥30 篇候选论文
3. 筛选后保留 15-30 篇，每篇有评分和理由
4. PDF 下载成功率 ≥80%（arXiv 论文 ≥95%）
5. marker-pdf 转换后的 Markdown 保留论文全文，不截断
6. 每篇论文的结构化笔记包含 9 个标准字段
7. 综述报告包含对比表，覆盖所有已处理论文
8. 实现文档达到教程级别，新人可据此理解整个系统

## Constraints & Assumptions

- Python 3.13.9 已安装（via miniconda3）
- 需要安装 marker-pdf（含 PyTorch 依赖，约 2-3GB）
- Semantic Scholar API 速率限制 100 req/5min
- arXiv API 速率限制较宽松
- marker-pdf 首次运行需下载模型（约 1GB）
- 假设大部分目标论文可在 arXiv 或开放获取渠道找到

## Out of Scope

- 引用格式管理（BibTeX、APA 等）
- 全文翻译
- 付费数据库访问
- LaTeX 输出
- Web UI
- 实时协作

## Dependencies

- marker-pdf（PDF→Markdown）
- fastmcp（Python MCP server 框架）
- httpx（异步 HTTP 客户端）
- Semantic Scholar API
- arXiv API
- OpenCode agent 系统 + MCP 集成
