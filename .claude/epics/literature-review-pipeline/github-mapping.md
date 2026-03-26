# GitHub Issue Mapping

Epic: #1 - https://github.com/caiusy/literature-review-agent/issues/1

Tasks:
- #2: 安装依赖 — marker-pdf, fastmcp, httpx - https://github.com/caiusy/literature-review-agent/issues/2
- #3: 创建 MCP server — search_papers, download_paper, convert_pdf - https://github.com/caiusy/literature-review-agent/issues/3
- #4: 配置 opencode.json 注册 MCP server - https://github.com/caiusy/literature-review-agent/issues/4
- #5: 重写 search-agent — 调 MCP tool + LLM 筛选 - https://github.com/caiusy/literature-review-agent/issues/5
- #6: 重写 literature-reviewer — 读 Markdown 全文 + 提取笔记 - https://github.com/caiusy/literature-review-agent/issues/6
- #7: 重写 synthesis-agent — 大规模支持 + 增强对比表 - https://github.com/caiusy/literature-review-agent/issues/7
- #8: 编写 architecture.md + implementation-log.md - https://github.com/caiusy/literature-review-agent/issues/8
- #9: 端到端测试 — 用真实关键词跑完全流程 - https://github.com/caiusy/literature-review-agent/issues/9

Dependency chain:
- #2 (安装依赖) → #3 (MCP server) → #4 (opencode.json)
- #4 → #5 (search-agent) | #6 (literature-reviewer) | #7 (synthesis-agent)  [并行]
- #5 + #6 + #7 → #9 (端到端测试)
- #8 (文档) 贯穿全程

Synced: 2026-03-26T14:22:24Z
