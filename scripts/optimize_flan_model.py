"""Build the bundled FLAN-T5 ONNX model from a locally cached pinned revision.

The encoder stays FP32 because quantizing it made short generation tests fail.
Only the decoder and cached decoder are quantized. No model files are fetched.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import onnx
import onnxruntime.quantization.onnx_quantizer as onnx_quantizer
from huggingface_hub import snapshot_download
from onnxruntime.quantization import QuantType, quantize_dynamic
from optimum.exporters.onnx import main_export


MODEL = 'google/flan-t5-small'
REVISION = '0fc9ddf78a1e988dac52e2dac162b0ede4fd74ab'
DATA_FILES = ('config.json', 'generation_config.json', 'special_tokens_map.json',
              'tokenizer_config.json', 'tokenizer.json')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('.data/models/optimized/flan_t5_small'))
    parser.add_argument('--scratch', type=Path, default=Path('.data/models/flan-t5-small-build'))
    args = parser.parse_args()
    output = args.output.resolve()
    scratch = args.scratch.resolve()
    output.mkdir(parents=True, exist_ok=True)
    scratch.mkdir(parents=True, exist_ok=True)

    source = snapshot_download(MODEL, revision=REVISION, local_files_only=True)
    main_export(source, output=scratch, task='text2text-generation-with-past',
                local_files_only=True, do_validation=True)
    for name in DATA_FILES:
        shutil.copyfile(scratch / name, output / name)
    shutil.copyfile(scratch / 'encoder_model.onnx', output / 'encoder_model.onnx')
    onnx_quantizer.save_and_reload_model_with_shape_infer = onnx.shape_inference.infer_shapes
    for name in ('decoder_model.onnx', 'decoder_with_past_model.onnx'):
        quantize_dynamic(str(scratch / name), str(output / name),
                         weight_type=QuantType.QInt8, op_types_to_quantize=['MatMul', 'Gather'])

    files = {}
    for path in sorted(output.iterdir()):
        if path.is_file() and path.name != 'manifest.json':
            with path.open('rb') as stream:
                files[path.name] = hashlib.file_digest(stream, 'sha256').hexdigest()
    manifest = {'model': MODEL, 'revision': REVISION,
                'format': 'onnx-encoder-fp32-decoder-int8', 'files': files}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'output': str(output), 'bytes': sum(path.stat().st_size for path in output.iterdir()
                                                          if path.is_file()), 'manifest': manifest}, indent=2))


if __name__ == '__main__':
    main()
