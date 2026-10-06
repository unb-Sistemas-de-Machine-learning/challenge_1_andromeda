from __future__ import annotations

import hashlib
import json
import threading
import time
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from news_analysis.explanation.models import ExplanationContext


@lru_cache(maxsize=2)
def _load_model(model_id: str, revision: str | None, cache_dir: str | None):
    """Download on first use, then reuse the tokenizer and model cache."""
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    options = {"cache_dir": cache_dir} if cache_dir else {}
    if revision:
        options["revision"] = revision
    tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=True, **options)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_id, **options)
    model.to("cpu")
    model.eval()
    return tokenizer, model


class ExplanationEngine(Protocol):
    model_id: str
    model_revision: str | None

    def generate(self, context: ExplanationContext) -> str:
        ...


class FlanT5SmallEngine:
    """Lazy, optional FLAN-T5 engine used only when explicitly enabled."""

    model_id = "google/flan-t5-small"
    prompt_version = "explanation-prompt-v4"

    def __init__(self, cache_dir: str | None = None, max_new_tokens: int = 80, max_input_tokens: int = 160,
                 model_id: str = "google/flan-t5-small", revision: str | None = None,
                 manifest_path: str | None = None, timeout_seconds: float = 8.0):
        self.cache_dir = cache_dir
        self.max_new_tokens = max_new_tokens
        self.max_input_tokens = max_input_tokens
        self.model_id = model_id
        self.revision = revision
        self.manifest_path = manifest_path
        self.timeout_seconds = timeout_seconds
        self._tokenizer = None
        self._model = None
        self.model_revision: str | None = revision
        self.tokenizer_revision: str | None = revision
        self.artifact_manifest_sha256: str | None = None
        self._lock = threading.Lock()

    def _verify_manifest(self) -> None:
        if not self.manifest_path:
            return
        manifest_bytes = Path(self.manifest_path).read_bytes()
        self.artifact_manifest_sha256 = hashlib.sha256(manifest_bytes).hexdigest()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
        root = Path(manifest.get("root", self.cache_dir or "."))
        for relative, expected in manifest.get("files", {}).items():
            path = root / relative
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest.lower() != str(expected).lower():
                raise RuntimeError(f"model_integrity_mismatch:{relative}")

    def _load(self) -> None:
        if self._tokenizer is not None and self._model is not None:
            return
        self._verify_manifest()
        self._tokenizer, self._model = _load_model(self.model_id, self.revision, self.cache_dir)

    def prepare(self) -> None:
        """Load once, separately from the inference deadline (including downloads)."""
        if self._tokenizer is not None and self._model is not None:
            return
        with self._lock:
            self._load()

    def generate(self, context: ExplanationContext) -> str:
        from news_analysis.explanation.prompt import build_prompt
        import torch

        self.prepare()
        started = time.perf_counter()
        if not self._lock.acquire(timeout=max(0.0, self.timeout_seconds)):
            raise TimeoutError("sml_timeout")
        try:
            inputs = self._tokenizer(
                build_prompt(context),
                return_tensors="pt",
                truncation=False,
            )
            if inputs["input_ids"].shape[-1] > self.max_input_tokens:
                # Keep essential results instead of truncating away facts.
                inputs = self._tokenizer(
                    build_prompt(context, include_details=False),
                    return_tensors="pt",
                    truncation=False,
                )
            if inputs["input_ids"].shape[-1] > self.max_input_tokens:
                raise ValueError("sml_input_budget_too_small")
            remaining = self.timeout_seconds - (time.perf_counter() - started)
            if remaining <= 0:
                raise TimeoutError("sml_timeout")
            with torch.inference_mode():
                output = self._model.generate(
                    **inputs,
                    max_new_tokens=self.max_new_tokens,
                    max_time=remaining,
                    num_beams=1,
                    do_sample=False,
                    use_cache=True,
                    no_repeat_ngram_size=3,
                    repetition_penalty=1.1,
                )
            text = self._tokenizer.decode(output[0], skip_special_tokens=True).strip()
            # max_time finishes the current step; never publish a timed-out draft.
            if time.perf_counter() - started >= self.timeout_seconds:
                raise TimeoutError("sml_timeout")
            return text
        finally:
            self._lock.release()
