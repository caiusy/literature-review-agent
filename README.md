# literature-review-agent

Goal:
Build an OpenCode literature review workflow that can:
- search papers from keywords
- download and archive original PDFs
- convert PDFs to Markdown without truncation
- extract structured notes
- synthesize a short literature review

Current workflow:
- use one query per folder under `data/queries/<query-slug>/`
- keep raw search results, PDFs, Markdown, notes, and outputs isolated per topic
- use three agents:
  - `search-agent`: search / filter / download / convert
  - `literature-reviewer`: read Markdown and write per-paper notes
  - `synthesis-agent`: summarize multiple notes into a review

Recommended folder layout:
- `data/queries/<query-slug>/search-results/`
- `data/queries/<query-slug>/papers/`
- `data/queries/<query-slug>/papers-md/`
- `data/queries/<query-slug>/notes/`
- `data/queries/<query-slug>/outputs/`

Single-paper test flow:
1. search one topic and choose one paper
2. download PDF into the query folder
3. convert PDF to Markdown (default: fast mode with lightweight extraction)
4. extract one note
5. generate a short summary

Conversion modes:
- `fast` (default): lightweight PDF text extraction, suitable for 1-minute test runs
- `layout`: marker-pdf high-fidelity reconstruction, slower but preserves layout better

Example query:
- `bev-detection`

Example prompts in OpenCode:
- `@search-agent 搜索 bev detection 相关论文，query_slug 用 bev-detection，时间范围 2021 之后，单篇测试，选 1 篇最合适的开放获取论文`
- `@literature-reviewer 阅读 query_slug=bev-detection 的论文并提取笔记`
- `@synthesis-agent 生成 query_slug=bev-detection 的简要文献总结`
