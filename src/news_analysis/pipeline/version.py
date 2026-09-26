from __future__ import annotations

import hashlib
import importlib.metadata
import json

from news_analysis.pipeline.aggregation import INTENDED_WEIGHTS
from news_analysis.pipeline.models import PipelineVersion

RULES_VERSION = "analysis-rules-v1"
FACT_CHECK_MAPPING_VERSION = "fact-check-rating-map-v1"
WRITING_MODEL_NAME = "vzani/portuguese-fake-news-classifier-bertimbau-combined"
WRITING_MODEL_REVISION = "main"


def dependency_versions() -> dict[str, str]:
    packages = ["fastapi", "pydantic", "httpx", "trafilatura", "transformers", "torch"]
    versions: dict[str, str] = {}
    for package in packages:
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "not-installed"
    return versions


def derive_pipeline_id(
    *,
    rules_version: str = RULES_VERSION,
    fact_check_mapping_version: str = FACT_CHECK_MAPPING_VERSION,
    intended_weights: dict[str, float] | None = None,
    writing_model_revision: str | None = WRITING_MODEL_REVISION,
    deps: dict[str, str] | None = None,
) -> str:
    payload = {
        "rules_version": rules_version,
        "fact_check_mapping_version": fact_check_mapping_version,
        "intended_weights": intended_weights or INTENDED_WEIGHTS,
        "writing_model_name": WRITING_MODEL_NAME,
        "writing_model_revision": writing_model_revision,
        "dependency_versions": deps or dependency_versions(),
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return f"pipeline-{digest}"


def current_pipeline_version() -> PipelineVersion:
    deps = dependency_versions()
    return PipelineVersion(
        id=derive_pipeline_id(deps=deps),
        rules_version=RULES_VERSION,
        fact_check_mapping_version=FACT_CHECK_MAPPING_VERSION,
        writing_model_name=WRITING_MODEL_NAME,
        writing_model_revision=WRITING_MODEL_REVISION,
        dependency_versions=deps,
    )
