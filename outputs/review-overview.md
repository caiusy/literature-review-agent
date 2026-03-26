# Literature Review Overview

## Scope

- Papers scanned: 1
- Notes generated: 1
- Source directory: `data/papers`
- Notes directory: `data/notes`

## Paper list

1. `2305.14314v1.pdf` → `data/notes/2305.14314v1.md`
   - Title: *QLoRA: Efficient Finetuning of Quantized LLMs*
   - Theme: 大模型高效微调、参数高效训练、低资源部署
   - Core idea: 通过 4-bit 量化冻结基座模型，并仅训练 LoRA 适配器，在显著降低显存占用的同时保持接近全精度微调的效果。

## Cross-paper synthesis

当前只有一篇论文，因此总览以单篇结论为主：

- QLoRA 证明了量化训练与参数高效微调可以有效结合。
- 论文的工程价值很强，直接降低了 65B 级模型微调的硬件门槛。
- 方法论上，核心创新集中在 NF4、Double Quantization 和 Paged Optimizers。
- 评估层面，论文同时强调了聊天 benchmark 的局限性，提醒不能只看单一分数。

## Reusable takeaways

1. 在有限显存条件下，优先考虑量化 + PEFT 组合而非全参数微调。
2. 高质量指令数据的重要性可能高于单纯扩大数据量。
3. 评估大模型对话能力时，应结合人工评测、强模型评测和失败案例分析。

## Generated files

- `data/notes/2305.14314v1.md`
- `outputs/review-overview.md`
