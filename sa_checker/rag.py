"""In-process hybrid retrieval for synthetic/local patient records.

Dense embeddings and BM25 are held in memory for the active process. No
patient text is written to a database or sent to a remote service.
"""

from __future__ import annotations

import re
from typing import Optional

import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
RRF_K = 60

_encoder: Optional[SentenceTransformer] = None
_dense_store: dict[str, tuple[np.ndarray, list[str]]] = {}
_bm25_store: dict[str, tuple[BM25Okapi, list[str]]] = {}


def _enc() -> SentenceTransformer:
    global _encoder
    if _encoder is None:
        _encoder = SentenceTransformer(MODEL_NAME)
    return _encoder


def init_collection() -> None:
    """Compatibility hook: storage is intentionally process-local."""


def _chunk(notes: str) -> list[str]:
    chunks: list[str] = []
    visit_header = ""

    for raw_line in notes.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("[Visit"):
            visit_header = line
            chunks.append(line)
            continue
        if ":" in line:
            chunks.append(line)
            if visit_header:
                chunks.append(f"{visit_header}\n{line}")
            value = line.split(":", 1)[-1].strip()
            if len(value) > 120:
                for sentence in re.split(r"(?<=[.!?])\s+", value):
                    sentence = sentence.strip()
                    if len(sentence) > 20:
                        chunks.append(sentence)
                        if visit_header:
                            chunks.append(f"{visit_header}\n{sentence}")
        elif len(line) > 15:
            chunks.append(line)

    return list(dict.fromkeys(chunks))


def _tokenize(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", value.casefold())


def index_patient(patient_id: str, patient_notes: str) -> int:
    chunks = _chunk(patient_notes)
    if not chunks:
        _dense_store.pop(patient_id, None)
        _bm25_store.pop(patient_id, None)
        return 0

    embeddings = _enc().encode(
        chunks,
        show_progress_bar=False,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    _dense_store[patient_id] = (embeddings, chunks)
    _bm25_store[patient_id] = (
        BM25Okapi([_tokenize(chunk) for chunk in chunks]),
        chunks,
    )
    return len(chunks)


def _dense_search(patient_id: str, query: str, top_k: int) -> list[str]:
    stored = _dense_store.get(patient_id)
    if not stored:
        return []
    embeddings, chunks = stored
    query_vector = _enc().encode(
        query,
        show_progress_bar=False,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    scores = embeddings @ query_vector
    ranked = np.argsort(scores)[::-1]
    return [chunks[index] for index in ranked[:top_k] if scores[index] >= 0.10]


def _bm25_search(patient_id: str, query: str, top_k: int) -> list[str]:
    stored = _bm25_store.get(patient_id)
    if not stored:
        return []
    index, chunks = stored
    scores = index.get_scores(_tokenize(query))
    ranked = np.argsort(scores)[::-1]
    return [chunks[index] for index in ranked[:top_k] if scores[index] > 0]


def _rrf(dense_hits: list[str], bm25_hits: list[str]) -> list[str]:
    scores: dict[str, float] = {}
    for hits in (dense_hits, bm25_hits):
        for rank, text in enumerate(hits, start=1):
            scores[text] = scores.get(text, 0.0) + 1.0 / (RRF_K + rank)
    return sorted(scores, key=scores.__getitem__, reverse=True)


def retrieve(patient_id: str, criterion: str, top_k: int = 8) -> list[str]:
    dense_hits = _dense_search(patient_id, criterion, top_k)
    bm25_hits = _bm25_search(patient_id, criterion, top_k)
    return _rrf(dense_hits, bm25_hits)[:top_k]
