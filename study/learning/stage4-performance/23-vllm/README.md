# 23 - 高性能推理 (vLLM)

## 目标

了解 vLLM 的部署和使用，理解推理加速的原理。

## 核心概念

- **vLLM** — 高性能 LLM 推理引擎，核心优化是 PagedAttention
- **Continuous Batching** — 动态合并请求，提升 GPU 利用率
- **PagedAttention** — 类似操作系统分页管理 KV cache，减少显存碎片
- **API 兼容** — vLLM 提供 OpenAI 兼容 API，可直接替换

## 实验设计

1. 用 vLLM 部署一个开源模型（如 Qwen2.5-1.5B，CPU 可跑）
2. 对比 vLLM 和直接 HuggingFace 推理的 tokens/s
3. 测试不同并发数下的吞吐量变化

## 前置条件

```bash
pip install vllm
# 或 CPU 模式（性能有限但可验证流程）
# VLLM_CPU_DEVICE=1 vllm serve Qwen/Qwen2.5-1.5B-Instruct
```

> 如果没有 GPU，本章可以用 Ollama 替代 vLLM 做实验，原理相似。

## 参考来源

- [vLLM Quickstart](https://docs.vllm.ai/en/latest/getting_started/quickstart.html)
- [vLLM 论文 (PagedAttention)](https://arxiv.org/abs/2309.06180)
- [SGLang](https://github.com/sgl-project/sglang) — vLLM 的替代方案
