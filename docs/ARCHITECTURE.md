# Architecture

## Runtime flow

1. The API loads an explicitly synthetic patient from `data/demo_patients.json`.
2. Structured visits are assembled into a local text representation.
3. Text is divided into field-level and visit-context chunks.
4. `all-MiniLM-L6-v2` creates local normalized embeddings.
5. Dense cosine ranking and BM25 keyword ranking run in memory.
6. Reciprocal Rank Fusion produces the evidence context for each criterion.
7. A loopback-only Ollama model assigns `MET`, `NOT MET`, or `UNCLEAR`.
8. Post-processing verifies citation presence, citation relevance, and simple numeric
   thresholds before a result can remain `MET`.
9. The API returns a pre-screen category and a per-criterion audit trail.

## Trust boundaries

- **Browser to API:** same-origin loopback traffic.
- **API to Ollama:** HTTP restricted to a loopback hostname.
- **Patient retrieval:** process memory only.
- **Policy update:** separate, explicitly network-enabled maintenance command.

## Deliberate exclusions

- No remote LLM provider.
- No generic endpoint that accepts an arbitrary filesystem path.
- No externally reachable bind address in the supplied launcher.
- No claim that a model-generated answer is an adjudication decision.
