from __future__ import annotations

import hashlib
import json
import threading
import time
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from news_analysis.asset_paths import FLAN_DIR, FLAN_MANIFEST
from news_analysis.bundled_models import ensure_model
from news_analysis.explanation.models import ExplanationContext


@lru_cache(maxsize=2)
def _load_model(model_id: str, revision: str | None, cache_dir: str | None):
    """Load the bundled optimized encoder and decoders without network access."""
    from optimum.onnxruntime import ORTModelForSeq2SeqLM
    from transformers import AutoTokenizer

    model_dir = Path(model_id).resolve()
    if not model_dir.is_dir():
        raise FileNotFoundError(f"Local explanation model not found: {model_dir}")
    tokenizer = AutoTokenizer.from_pretrained(model_dir, use_fast=True, local_files_only=True)
    model = ORTModelForSeq2SeqLM.from_pretrained(
        model_dir, local_files_only=True, use_merged=False, provider="CPUExecutionProvider")
    return tokenizer, model


class ExplanationEngine(Protocol):
    model_id: str
    model_revision: str | None

    def generate(self, context: ExplanationContext) -> str:
        ...


class FlanT5SmallEngine:
    """Lazy, optional FLAN-T5 engine used only when explicitly enabled."""

    model_id = "google/flan-t5-small"
    prompt_version = "rewrite-only-v1"

    def __init__(self, cache_dir: str | None = None, max_new_tokens: int = 80, max_input_tokens: int = 160,
                 model_id: str = str(FLAN_DIR),
                 revision: str | None = "0fc9ddf78a1e988dac52e2dac162b0ede4fd74ab",
                 manifest_path: str | None = str(FLAN_MANIFEST), timeout_seconds: float = 8.0):
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
        if manifest.get("model") != "google/flan-t5-small" or manifest.get("revision") != self.revision:
            raise RuntimeError("model_manifest_mismatch")
        root = Path(self.manifest_path).resolve().parent
        for relative, expected in manifest.get("files", {}).items():
            path = root / relative
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if digest.lower() != str(expected).lower():
                raise RuntimeError(f"model_integrity_mismatch:{relative}")

    def _load(self) -> None:
        if self._tokenizer is not None and self._model is not None:
            return
        if Path(self.model_id).resolve() == FLAN_DIR:
            ensure_model('flan_t5_small')
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

    def rewrite(self, text: str) -> str:
        """Edit only the already audited summary; no analysis data enters the model."""
        import torch

        self.prepare()
        prompt = (
            "Revise apenas a fluidez deste texto em português brasileiro. "
            "Preserve todas as informações, ressalvas e o grau de confiabilidade. "
            "Não acrescente fatos.\nTexto: " + text + "\nRevisão:"
        )
        started = time.perf_counter()
        if not self._lock.acquire(timeout=max(0.0, self.timeout_seconds)):
            raise TimeoutError("sml_timeout")
        try:
            inputs = self._tokenizer(prompt, return_tensors="pt", truncation=False)
            if inputs["input_ids"].shape[-1] > self.max_input_tokens:
                raise ValueError("sml_input_budget_too_small")
            remaining = self.timeout_seconds - (time.perf_counter() - started)
            if remaining <= 0:
                raise TimeoutError("sml_timeout")
            with torch.inference_mode():
                output = self._model.generate(
                    **inputs, max_new_tokens=self.max_new_tokens, max_time=remaining,
                    num_beams=1, do_sample=False, use_cache=True,
                )
            result = self._tokenizer.decode(output[0], skip_special_tokens=True).strip()
            if time.perf_counter() - started >= self.timeout_seconds:
                raise TimeoutError("sml_timeout")
            return result
        finally:
            self._lock.release()
