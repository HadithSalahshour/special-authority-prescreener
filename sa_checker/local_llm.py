"""Small, local-only Ollama client shared by the checker components."""

from __future__ import annotations

import os
from functools import lru_cache
from urllib.parse import urlparse

import ollama


DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_MODEL = "llama3.1:8b"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}


def model_name() -> str:
    return os.getenv("SA_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL


def ollama_url() -> str:
    url = os.getenv("SA_OLLAMA_URL", DEFAULT_OLLAMA_URL).strip()
    if urlparse(url).hostname not in LOCAL_HOSTS:
        raise RuntimeError(
            "SA_OLLAMA_URL must point to localhost. Remote model endpoints are "
            "disabled to keep clinical text on this machine."
        )
    return url


@lru_cache(maxsize=1)
def client() -> ollama.Client:
    return ollama.Client(host=ollama_url())


def chat(prompt: str, *, temperature: float = 0) -> str:
    response = client().chat(
        model=model_name(),
        options={"temperature": temperature},
        messages=[{"role": "user", "content": prompt}],
    )
    return response["message"]["content"]
