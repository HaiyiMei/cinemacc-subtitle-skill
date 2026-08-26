#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CASE_DIR = ROOT / "evals" / "harbor-lights"
CASE = json.loads((CASE_DIR / "case.json").read_text(encoding="utf-8"))
TOOL_PATH = ROOT / "skills" / "cinemacc-subtitle" / "scripts" / "srt_tools.py"
SPEC = importlib.util.spec_from_file_location("srt_tools", TOOL_PATH)
assert SPEC and SPEC.loader
srt_tools = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(srt_tools)


def evaluate(package: Path) -> None:
    expected = CASE["expectedBundle"]
    source = CASE_DIR / CASE["input"]["source"]
    with zipfile.ZipFile(package) as archive:
        if archive.namelist() != expected["entries"]:
            raise ValueError(f"unexpected ZIP entries: {archive.namelist()}")
        manifest = json.loads(archive.read("cinemacc.json"))
        for key, value in expected["manifest"].items():
            if manifest.get(key) != value:
                raise ValueError(
                    f"manifest {key!r}: expected {value!r}, got {manifest.get(key)!r}"
                )
        for key in expected["requiredNonEmptyManifestFields"]:
            if not isinstance(manifest.get(key), str) or not manifest[key].strip():
                raise ValueError(f"manifest {key!r} must be a non-empty string")
        if archive.read("dialogue.srt") != source.read_bytes():
            raise ValueError(
                "dialogue.srt does not preserve the downloaded source bytes"
            )
        translation = archive.read("translation.srt")
        if translation == source.read_bytes():
            raise ValueError("translation.srt is unchanged source text")
        reference_package = CASE_DIR / CASE["reference"]["package"]
        if package.resolve() == reference_package.resolve():
            reference_translation = CASE_DIR / CASE["reference"]["translation"]
            if translation != reference_translation.read_bytes():
                raise ValueError("reference package translation is stale")

    with tempfile.TemporaryDirectory() as temporary_directory:
        target = Path(temporary_directory) / "translation.srt"
        target.write_bytes(translation)
        if srt_tools.validate(source, target, scan=True, require_player_format=True):
            raise ValueError("translation.srt failed structural validation")

    print(f"PASS: {CASE['id']}")
    print(f"package: {package}")
    print(f"sha256: {srt_tools.sha256_file(package)}")


if __name__ == "__main__":
    candidate = (
        Path(sys.argv[1])
        if len(sys.argv) == 2
        else CASE_DIR / CASE["reference"]["package"]
    )
    if len(sys.argv) > 2:
        raise SystemExit(f"usage: {Path(sys.argv[0]).name} [candidate.cinemacc.zip]")
    try:
        evaluate(candidate)
    except Exception as error:
        raise SystemExit(f"FAIL: {error}") from error
