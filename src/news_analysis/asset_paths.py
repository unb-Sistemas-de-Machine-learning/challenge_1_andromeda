"""Paths of compressed model artifacts and their writable extraction cache."""
import os
from pathlib import Path

ASSETS = Path(__file__).resolve().parent / 'assets'
BUNDLES = ASSETS / 'bundles'
MODEL_CACHE = Path(os.environ.get('NEWS_ANALYSIS_MODEL_DIR', '.data/models/bundled')).resolve()
WRITING_ONNX = MODEL_CACHE / 'writing_bertimbau' / 'model.int8.onnx'
