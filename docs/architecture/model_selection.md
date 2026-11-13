# Model and Provider Selection

**Last reviewed:** 13 November 2026

This document distinguishes the model components used by the active prototype from the earlier ADTC/local-inference design.

## Current implementation

| Function | Current selection | Execution location |
|---|---|---|
| Text embeddings | `sentence-transformers/all-MiniLM-L6-v2` | Local; model must be present in the Sentence Transformers cache |
| Vector similarity | FAISS `IndexFlatIP` | Local CPU |
| Answer generation | Groq API; configured default `openai/gpt-oss-120b` | Remote API; internet and `GROQ_API_KEY` required |

The encoder normalises vectors before indexing and query search. With normalised vectors, FAISS inner-product ranking corresponds to cosine similarity. The retrieval score indicates vector similarity only; it is not a factual confidence score.

## Runtime behaviour

1. The index builder embeds curated Markdown chunks with the Sentence Transformer model.
2. The FAISS index and aligned chunk metadata are saved under `vector_store/`.
3. At query time, the same local encoder creates a query vector.
4. FAISS retrieves the top matching chunks.
5. The answer generator sends the question and retrieved evidence to Groq.
6. The UI displays the generated response and supporting source metadata.

The encoder uses local-only model loading. The model must be cached before building or querying the index. The Groq generation step is not offline.

## Earlier local LLM proposal

The repository contains historical design material for Qwen2.5-1.5B-Instruct in GGUF format with llama.cpp. That proposal is **not the current answer-generation implementation** and no active `llama-cpp-python` inference path is used by the Streamlit assistant at this stage.

A local LLM may be evaluated later if offline operation becomes a product requirement. Any replacement should be compared using:
- Poultry-domain answer quality and groundedness.
- Unsafe-response and abstention tests.
- Latency and peak memory on target farmer hardware.
- Language coverage and local relevance.
- Operational cost and offline deployment complexity.

## Evaluation requirements

Do not choose or promote a model based solely on parameter count or public benchmark claims. Before changing the embedding or generation provider:

- Build a representative poultry question set with expert-reviewed expected evidence.
- Measure retrieval recall/ranking and source coverage.
- Evaluate answer correctness, unsupported claims, uncertainty handling and veterinary safety.
- Record latency, resource use, availability and cost.
- Version the model identifier, configuration and evaluation results.

## Limitations

No independent benchmark of the current embedding/provider combination is claimed in this document. No clinical or veterinary diagnostic performance is claimed.
