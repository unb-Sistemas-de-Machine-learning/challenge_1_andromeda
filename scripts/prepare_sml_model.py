"""Download and materialize the local SML outside the analysis request path.

This is an explicit operator command. Runtime inference uses local_files_only and
will never invoke this script or contact Hugging Face automatically.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", default="google/flan-t5-small")
    parser.add_argument("--revision", required=True)
    args = parser.parse_args()

    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

    args.output.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(args.model, revision=args.revision)
    model = AutoModelForSeq2SeqLM.from_pretrained(args.model, revision=args.revision)
    tokenizer.save_pretrained(args.output)
    model.save_pretrained(args.output, safe_serialization=True)

    files = {}
    for path in sorted(args.output.rglob("*")):
        if path.is_file() and path.name != "manifest.json":
            files[str(path.relative_to(args.output))] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest = {"model": args.model, "revision": args.revision, "root": str(args.output), "files": files}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(args.output / "manifest.json")


if __name__ == "__main__":
    main()
