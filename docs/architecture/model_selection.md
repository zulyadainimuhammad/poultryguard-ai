# Model Selection

## Purpose

This document records the rationale for selecting Qwen2.5-1.5B-Instruct as the primary language model and `all-MiniLM-L6-v2` as the embedding model for PoultryGuard AI. It documents the evaluation criteria, candidate models considered, and the constraints that drove the final decisions.

---

## Background

Model selection for an offline, CPU-only, 8 GB RAM system is fundamentally a hardware-constrained optimisation problem. The primary objective is not maximum benchmark performance but the best achievable answer quality within strict memory and latency budgets on the ADTC Standard Laptop.

The ADTC Standard Laptop specification:
- Intel Core i5 10th–12th Gen or AMD Ryzen 5
- 8 GB RAM (shared with OS, UI, and RAG pipeline)
- Integrated graphics only (no CUDA, no Metal, no ROCm)
- Ubuntu 22.04 LTS

Effective RAM budget for the model after OS (~2 GB) and application overhead (~0.5 GB):
- Available for model: ~5 GB
- Available for FAISS index + embeddings + context: ~0.5 GB
- Safety headroom: ~0.5 GB

---

## Design Decisions

| Decision | Rationale |
|---|---|
| GGUF format | Native llama.cpp format; enables quantisation, memory-mapped loading, and CPU-optimised kernels |
| Q4_K_M quantisation | Best quality-to-size ratio in the 4-bit family; K-quant mixed precision preserves attention layers at higher precision |
| 1.5B parameter model | Fits comfortably in 5 GB RAM budget at Q4_K_M; leaves headroom for RAG and OS |
| Qwen2.5 architecture | Strong instruction-following at small scale; multilingual capability relevant for African language future work |
| Local embedding model | Avoids any network dependency; `all-MiniLM-L6-v2` is 22 MB and runs in ~50 ms per batch on CPU |

---

## LLM Candidate Evaluation

| Model | Parameters | Q4_K_M Size | RAM Usage | CPU Tokens/s (i5) | Instruction Following | Selected |
|---|---|---|---|---|---|---|
| Qwen2.5-1.5B-Instruct | 1.5B | ~1.0 GB | ~1.5 GB | ~12–18 | Excellent for size | ✅ |
| Phi-3-mini-4k-instruct | 3.8B | ~2.4 GB | ~3.0 GB | ~6–9 | Very good | Backup |
| Llama-3.2-1B-Instruct | 1.2B | ~0.8 GB | ~1.2 GB | ~15–20 | Good | Considered |
| Gemma-2-2B-it | 2.6B | ~1.6 GB | ~2.2 GB | ~8–12 | Good | Considered |
| Mistral-7B-Instruct-v0.3 | 7B | ~4.4 GB | ~5.5 GB | ~3–5 | Excellent | Too slow |
| TinyLlama-1.1B-Chat | 1.1B | ~0.7 GB | ~1.0 GB | ~20–25 | Poor | Rejected |

### Selection Rationale: Qwen2.5-1.5B-Instruct

Qwen2.5-1.5B-Instruct was selected because:

1. **Instruction following quality** — Qwen2.5 models demonstrate significantly better instruction adherence at the 1.5B scale compared to Llama 3.2 1B and TinyLlama, which is critical for structured advisory responses.
2. **Multilingual foundation** — Qwen2.5 was trained on a multilingual corpus including African languages, supporting future localisation work.
3. **Context window** — Supports up to 32K tokens natively; configured to 2048 for this application to minimise RAM usage.
4. **RAM efficiency** — Q4_K_M quantisation yields ~1.5 GB loaded RAM, leaving ample headroom.
5. **llama.cpp compatibility** — Fully supported by llama.cpp with optimised CPU kernels.
6. **Active maintenance** — Alibaba Cloud actively maintains Qwen2.5; GGUF conversions are available on Hugging Face.

### Backup Model: Phi-3-mini-4k-instruct

If Qwen2.5-1.5B-Instruct proves insufficient for answer quality in evaluation, Phi-3-mini-4k-instruct (3.8B) is the designated backup. It fits within the RAM budget on devices with 8 GB RAM but leaves less headroom and will be slower.

---

## GGUF Quantisation Reference

| Quantisation | Bits | Quality | Size (1.5B) | Notes |
|---|---|---|---|---|
| Q2_K | 2 | Poor | ~0.6 GB | Not recommended; significant quality loss |
| Q4_0 | 4 | Good | ~0.9 GB | Uniform 4-bit; faster but lower quality than K-quants |
| Q4_K_M | 4 | Very good | ~1.0 GB | Mixed precision K-quant; **selected** |
| Q5_K_M | 5 | Excellent | ~1.2 GB | Marginal quality gain; acceptable if RAM allows |
| Q8_0 | 8 | Near-lossless | ~1.6 GB | Use only if RAM budget permits |
| F16 | 16 | Lossless | ~3.0 GB | Exceeds practical CPU RAM budget |

---

## Embedding Model Selection

### Requirement

The embedding model must:
- Run entirely offline on CPU
- Produce vectors suitable for semantic similarity search
- Load in under 5 seconds on the ADTC laptop
- Use less than 200 MB RAM
- Produce embeddings in under 100 ms per query

### Selected: `sentence-transformers/all-MiniLM-L6-v2`

| Property | Value |
|---|---|
| Architecture | MiniLM-L6 (6-layer transformer) |
| Embedding dimension | 384 |
| Model size on disk | ~22 MB |
| RAM usage | ~80 MB |
| Inference time (CPU, single query) | ~20–50 ms |
| Semantic similarity quality | Strong for English; adequate for domain-specific text |
| Licence | Apache 2.0 |

### Embedding Candidate Comparison

| Model | Dim | Size | CPU Latency | Quality | Selected |
|---|---|---|---|---|---|
| all-MiniLM-L6-v2 | 384 | 22 MB | ~30 ms | Good | ✅ |
| all-MiniLM-L12-v2 | 384 | 33 MB | ~50 ms | Better | Considered |
| all-mpnet-base-v2 | 768 | 420 MB | ~120 ms | Excellent | Too large |
| bge-small-en-v1.5 | 384 | 24 MB | ~30 ms | Good | Alternative |
| e5-small-v2 | 384 | 33 MB | ~40 ms | Good | Alternative |

`all-MiniLM-L6-v2` was selected for its combination of small size, fast CPU inference, and adequate semantic quality for the poultry domain. The embedding model will be cached locally after first download and never requires network access at runtime.

---

## llama.cpp Runtime Configuration

The following llama.cpp parameters are configured for the ADTC Standard Laptop:

```python
LlamaConfig(
    model_path="models/gguf/qwen2.5-1.5b-instruct-q4_k_m.gguf",
    n_ctx=2048,          # Context window — balances quality and RAM
    n_threads=4,         # CPU threads — matches typical i5 core count
    n_batch=512,         # Prompt processing batch size
    n_gpu_layers=0,      # CPU-only — no GPU offloading
    use_mmap=True,       # Memory-mapped loading — reduces RAM pressure
    use_mlock=False,     # Do not lock pages — allows OS to swap if needed
    verbose=False,       # Suppress llama.cpp console output
)
```

---

## Model File Distribution

GGUF model files are not stored in Git. The recommended acquisition path:

1. Download from Hugging Face: `Qwen/Qwen2.5-1.5B-Instruct-GGUF`
2. Select file: `qwen2.5-1.5b-instruct-q4_k_m.gguf`
3. Place at: `models/gguf/qwen2.5-1.5b-instruct-q4_k_m.gguf`

A setup script (`scripts/download_model.py`) will be provided in Sprint 5 to automate this step for developers with internet access. For offline deployment, the GGUF file is distributed on a USB drive alongside the application.

---

## Trade-offs

| Trade-off | Accepted Cost | Benefit |
|---|---|---|
| 1.5B vs 3.8B model | Lower reasoning depth | Fits in 8 GB RAM with headroom; faster inference |
| Q4_K_M vs Q8_0 | ~1–2% quality reduction | ~40% smaller model; faster load and inference |
| MiniLM-L6 vs mpnet-base | Lower embedding quality | 19× smaller; 4× faster; fits offline constraint |
| Fixed n_ctx=2048 | Shorter context window | Reduces RAM usage by ~500 MB vs 4096 context |

---

## Future Improvements

- Evaluate Qwen2.5-3B-Instruct Q4_K_M as hardware targets improve (requires ~2.5 GB RAM)
- Investigate multilingual embedding models (e.g., `paraphrase-multilingual-MiniLM-L12-v2`) for Hausa/Swahili support
- Add model integrity verification (SHA-256 checksum) to the setup script
- Benchmark answer quality on a poultry-domain evaluation set to validate model selection empirically

---

## References

- [Qwen2.5 Technical Report](https://arxiv.org/abs/2412.15115)
- [llama.cpp GGUF format](https://github.com/ggerganov/llama.cpp/blob/master/docs/gguf.md)
- [sentence-transformers all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)
- [GGUF quantisation types](https://github.com/ggerganov/llama.cpp/blob/master/docs/quantization.md)
- See also: `system_overview.md`, `rag_design.md`, `deployment.md`
