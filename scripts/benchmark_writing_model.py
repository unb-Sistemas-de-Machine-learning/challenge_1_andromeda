"""Small reproducible comparison of the pinned PyTorch and optimized ONNX models."""
from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path

import onnxruntime as ort
import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from news_analysis.pipeline.version import WRITING_MODEL_NAME, WRITING_MODEL_REVISION


SAMPLES = (
    'O governo divulgou novos dados sobre a campanha de vacinação nesta semana.',
    'Pesquisadores publicaram um estudo e explicaram os métodos e as limitações dos resultados. ' * 5,
    'URGENTE! Compartilhe agora esta notícia surpreendente que todos precisam conhecer! ' * 15,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model-dir', type=Path, default=Path('.data/models/writing-bertimbau-onnx'))
    args = parser.parse_args()
    options = {'revision': WRITING_MODEL_REVISION, 'local_files_only': True}
    torch.set_num_threads(min(4, torch.get_num_threads()))
    tokenizer = AutoTokenizer.from_pretrained(WRITING_MODEL_NAME, use_fast=True, **options)
    model = AutoModelForSequenceClassification.from_pretrained(WRITING_MODEL_NAME, **options).eval()
    ort_options = ort.SessionOptions()
    ort_options.intra_op_num_threads = min(4, torch.get_num_threads())
    sessions = {name: ort.InferenceSession(str(args.model_dir / filename),
                                          sess_options=ort_options, providers=['CPUExecutionProvider'])
                for name, filename in [('fp32', 'model.fp32.onnx'), ('int8', 'model.int8.onnx')]}
    comparisons = []
    for sample in SAMPLES:
        encoded = tokenizer(sample, return_tensors='pt', truncation=True, max_length=512)
        arrays = {item.name: encoded.get(item.name, torch.zeros_like(encoded['input_ids'])).numpy()
                  for item in sessions['int8'].get_inputs()}
        torch_inputs = {name: encoded[name] for name in encoded if name in {'input_ids', 'attention_mask', 'token_type_ids'}}
        with torch.inference_mode():
            baseline = torch.softmax(model(**torch_inputs).logits, dim=-1)[0, 1].item()
        variants = {}
        for name, session in sessions.items():
            optimized = float(torch.softmax(torch.tensor(session.run(None, arrays)[0]), dim=-1)[0, 1])
            durations = []
            for _ in range(4):
                start = time.perf_counter()
                session.run(None, arrays)
                durations.append((time.perf_counter() - start) * 1000)
            variants[name] = {'score': round(optimized, 6),
                              'absolute_difference': round(abs(baseline - optimized), 6),
                              'median_ms': round(statistics.median(durations), 1)}
        comparisons.append({'tokens': int(encoded['input_ids'].shape[1]),
                            'baseline': round(baseline, 6), 'variants': variants})
    print(json.dumps({'model_bytes': (args.model_dir / 'model.int8.onnx').stat().st_size,
                      'comparisons': comparisons}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
