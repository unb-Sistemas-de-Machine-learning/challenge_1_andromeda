"""Package the two optimized model directories into ordinary Git-sized ZIP parts.

Example: python scripts/pack_models.py --source src/news_analysis/assets
Only the resulting ``assets/bundles`` directory belongs in Git.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import zipfile
from pathlib import Path

from news_analysis.asset_paths import ASSETS

MODELS = ('writing_bertimbau', 'flan_t5_small')
PART_BYTES = 48 * 1024 * 1024


def digest(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path('.data/models/optimized'))
    parser.add_argument('--output', type=Path, default=ASSETS / 'bundles')
    args = parser.parse_args()
    source = args.source.resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    manifest = {'format': 'zip-parts-v1', 'part_bytes': PART_BYTES, 'models': {}}

    scratch = Path('.data/models/package-tmp').resolve()
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=scratch) as temporary:
        for model_name in MODELS:
            model_dir = source / model_name
            files = sorted(path for path in model_dir.iterdir() if path.is_file())
            if not files or not any(path.suffix == '.onnx' for path in files):
                raise ValueError(f'Optimized model files missing: {model_dir}')
            archive = Path(temporary) / f'{model_name}.zip'
            with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED,
                                 compresslevel=6, allowZip64=True) as zipped:
                for path in files:
                    zipped.write(path, arcname=path.name)
            parts = []
            with archive.open('rb') as stream:
                index = 0
                while True:
                    block = stream.read(PART_BYTES)
                    if not block:
                        break
                    name = f'{model_name}.zip.part{index:03d}'
                    part = output / name
                    part.write_bytes(block)
                    parts.append({'name': name, 'bytes': len(block),
                                  'sha256': hashlib.sha256(block).hexdigest()})
                    index += 1
            manifest['models'][model_name] = {
                'archive_sha256': digest(archive),
                'archive_bytes': archive.stat().st_size,
                'files': {path.name: digest(path) for path in files},
                'parts': parts,
            }
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({name: {'parts': len(item['parts']), 'archive_bytes': item['archive_bytes']}
                      for name, item in manifest['models'].items()}, indent=2))


if __name__ == '__main__':
    main()
