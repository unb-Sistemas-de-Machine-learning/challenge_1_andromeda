"""Extract checked, bundled ONNX models on first use without a network request."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import time
import zipfile
from pathlib import Path

from news_analysis.asset_paths import BUNDLES, MODEL_CACHE


def _sha256(path: Path) -> str:
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _ready(target: Path, spec: dict) -> bool:
    marker = target / '.bundle.sha256'
    if not marker.is_file() or marker.read_text(encoding='ascii') != spec['archive_sha256']:
        return False
    return all((target / name).is_file() for name in spec['files'])


def ensure_model(name: str) -> Path:
    """Return a verified local model directory, extracting it only if needed."""
    if name != 'writing_bertimbau':
        raise ValueError('Unknown bundled model')
    manifest = json.loads((BUNDLES / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('format') != 'zip-parts-v1':
        raise ValueError('Unsupported model bundle format')
    spec = manifest['models'][name]
    target = MODEL_CACHE / name
    if _ready(target, spec):
        return target
    MODEL_CACHE.mkdir(parents=True, exist_ok=True)
    lock = MODEL_CACHE / f'.{name}.lock'
    deadline = time.monotonic() + 300
    while True:
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(descriptor)
            break
        except FileExistsError:
            if _ready(target, spec):
                return target
            if time.monotonic() >= deadline:
                raise TimeoutError(f'Timed out waiting for model extraction: {name}')
            time.sleep(0.2)
    try:
        if _ready(target, spec):
            return target
        with tempfile.TemporaryDirectory(prefix=f'.{name}-', dir=MODEL_CACHE) as temporary:
            work = Path(temporary)
            archive = work / 'model.zip'
            with archive.open('wb') as output:
                for index, part_spec in enumerate(spec['parts']):
                    expected_name = f'{name}.zip.part{index:03d}'
                    if part_spec['name'] != expected_name:
                        raise ValueError('Unexpected model bundle part')
                    part = BUNDLES / expected_name
                    if part.stat().st_size != part_spec['bytes'] or _sha256(part) != part_spec['sha256']:
                        raise ValueError(f'Model bundle part checksum mismatch: {expected_name}')
                    with part.open('rb') as source:
                        shutil.copyfileobj(source, output)
            if archive.stat().st_size != spec['archive_bytes'] or _sha256(archive) != spec['archive_sha256']:
                raise ValueError('Model bundle archive checksum mismatch')
            staged = work / name
            staged.mkdir()
            with zipfile.ZipFile(archive) as zipped:
                if set(zipped.namelist()) != set(spec['files']):
                    raise ValueError('Model bundle file list mismatch')
                for filename, expected_hash in spec['files'].items():
                    if Path(filename).name != filename or filename in ('.', '..'):
                        raise ValueError('Unsafe model bundle filename')
                    with zipped.open(filename) as source, (staged / filename).open('wb') as output:
                        shutil.copyfileobj(source, output)
                    if _sha256(staged / filename) != expected_hash:
                        raise ValueError(f'Model file checksum mismatch: {filename}')
            (staged / '.bundle.sha256').write_text(spec['archive_sha256'], encoding='ascii')
            backup = work / 'previous'
            if target.exists():
                target.rename(backup)
            try:
                staged.rename(target)
            except Exception:
                if backup.exists():
                    backup.rename(target)
                raise
        return target
    finally:
        lock.unlink(missing_ok=True)
