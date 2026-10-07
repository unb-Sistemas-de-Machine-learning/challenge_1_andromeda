"""Export the pinned writing classifier and quantize it for CPU inference.

Run with: python scripts/optimize_writing_model.py
Requires the optional ``mobile`` dependencies from pyproject.toml.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import onnx
import onnxruntime.quantization.onnx_quantizer as onnx_quantizer
import torch
from onnxruntime.quantization import QuantType, quantize_dynamic
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from news_analysis.pipeline.version import WRITING_MODEL_NAME, WRITING_MODEL_REVISION


class LogitsOnly(torch.nn.Module):
    def __init__(self, model: torch.nn.Module):
        super().__init__()
        self.model = model

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor, token_type_ids: torch.Tensor) -> torch.Tensor:
        return self.model(input_ids=input_ids, attention_mask=attention_mask,
                          token_type_ids=token_type_ids).logits


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('.data/models/optimized/writing_bertimbau'))
    parser.add_argument('--scratch', type=Path, default=Path('.data/models/writing-bertimbau-build'))
    parser.add_argument('--cache-dir', default=None)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    scratch = args.scratch.resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    options = {'revision': WRITING_MODEL_REVISION, 'cache_dir': args.cache_dir,
               'local_files_only': True}
    tokenizer = AutoTokenizer.from_pretrained(WRITING_MODEL_NAME, use_fast=True, **options)
    model = AutoModelForSequenceClassification.from_pretrained(WRITING_MODEL_NAME, **options).eval()
    inputs = tokenizer('Texto de exemplo para exportação.', return_tensors='pt')
    names = ('input_ids', 'attention_mask', 'token_type_ids')
    values = tuple(inputs.get(name, torch.zeros_like(inputs['input_ids'])) for name in names)
    fp32 = scratch / 'model.fp32.onnx'
    int8 = output / 'model.int8.onnx'
    with torch.inference_mode():
        torch.onnx.export(LogitsOnly(model), values, str(fp32), input_names=list(names),
                          output_names=['logits'], opset_version=17, dynamo=False,
                          dynamic_axes={name: {0: 'batch', 1: 'sequence'} for name in names})
    del model
    # The model is below ONNX's 2 GB in-memory limit. Avoid a temporary
    # external-data file, which ONNX Runtime cannot canonicalize in some
    # sandboxed Windows environments.
    onnx_quantizer.save_and_reload_model_with_shape_infer = onnx.shape_inference.infer_shapes
    quantize_dynamic(str(fp32), str(int8), weight_type=QuantType.QInt8,
                     op_types_to_quantize=['MatMul', 'Gather'])
    tokenizer.save_pretrained(output)
    with int8.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    manifest = {'model': WRITING_MODEL_NAME, 'revision': WRITING_MODEL_REVISION,
                'format': 'onnx-int8-dynamic-matmul-gather', 'fp32_bytes': fp32.stat().st_size,
                'int8_bytes': int8.stat().st_size, 'sha256': digest, 'max_length': 512}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    main()
