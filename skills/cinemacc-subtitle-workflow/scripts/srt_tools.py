#!/usr/bin/env python3
"""Small deterministic helpers for SRT subtitle translation workflows."""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import os
import re
import shutil
import statistics
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any


TIMESTAMP_RE = re.compile(
    r"^\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}(?: .*)?$"
)
CHUNK_RE = re.compile(r"chunk-(\d+)-(\d+)\.srt$|chunk-(\d+)-(\d+)\..*\.srt$")
TAG_RE = re.compile(r"</?[A-Za-z][^>]*>|\{\\[^}]+\}", re.IGNORECASE)
CYRILLIC_RE = re.compile(r"[\u0400-\u04ff]")
LATIN_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9-]{2,}")
LANGUAGE_TAG_RE = re.compile(
    r"(?:[._-](?:en|eng|zh-CN|zh-TW|zh-Hans|zh-Hant))$", re.IGNORECASE
)
WORKBOOK_BASE_COLUMNS = ["number", "timestamp", "source", "refined"]
WORKBOOK_TRAILING_COLUMNS = ["confidence", "notes"]
DEFAULT_TARGETS = ["zh-CN", "zh-TW"]
QA_PROFILES = {
    "en": {"max_chars_per_line": 48, "max_cps": 20.0, "max_lines": 2},
    "zh-CN": {"max_chars_per_line": 22, "max_cps": 13.0, "max_lines": 2},
    "zh-TW": {"max_chars_per_line": 22, "max_cps": 13.0, "max_lines": 2},
}
DEFAULT_ALLOWED_LATIN = {
    "app",
    "dna",
    "fbi",
    "gps",
    "mit",
    "mj",
    "mri",
    "mrna",
    "nypd",
    "rna",
}
ENGLISH_SDH_RE = re.compile(
    r"^\s*(?:"
    r"[\[(][A-Za-z][A-Za-z0-9 .,'!?-]{2,}[\])]"
    r"|[A-Za-z][A-Za-z .'-]{1,24}:"
    r")"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized_cue_text(lines: list[str]) -> str:
    visible = TAG_RE.sub("", " ".join(lines)).casefold()
    return re.sub(r"[^\w]+", " ", visible, flags=re.UNICODE).strip()


def normalized_track_hash(cues: list[tuple[int, str, list[str]]]) -> str:
    text = "\n".join(normalized_cue_text(lines) for _, _, lines in cues)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def encode_workbook_cell(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n")


def decode_workbook_cell(value: str) -> str:
    output: list[str] = []
    index = 0
    while index < len(value):
        character = value[index]
        if character != "\\" or index + 1 >= len(value):
            output.append(character)
            index += 1
            continue
        escaped = value[index + 1]
        if escaped == "n":
            output.append("\n")
        elif escaped == "t":
            output.append("\t")
        elif escaped == "\\":
            output.append("\\")
        else:
            output.extend(("\\", escaped))
        index += 2
    return "".join(output)


def resolve_manifest(path: Path) -> tuple[Path, dict[str, Any]]:
    manifest_path = path / "manifest.json" if path.is_dir() else path
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{manifest_path}: invalid manifest JSON") from exc
    if not isinstance(manifest, dict) or manifest.get("version") != 1:
        raise ValueError(f"{manifest_path}: unsupported job manifest")
    return manifest_path, manifest


def path_from_manifest(manifest_path: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else manifest_path.parent / path


def read_text(path: Path) -> str:
    return (
        path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    )


def parse_srt(path: Path) -> list[tuple[int, str, list[str]]]:
    text = read_text(path).strip("\n")
    if not text:
        return []

    cues: list[tuple[int, str, list[str]]] = []
    for index, block in enumerate(
        [b for b in text.split("\n\n") if b.strip()], start=1
    ):
        lines = block.split("\n")
        if len(lines) < 2:
            raise ValueError(f"{path}: cue block {index} has fewer than 2 lines")
        try:
            cue_number = int(lines[0])
        except ValueError as exc:
            raise ValueError(
                f"{path}: cue block {index} has non-numeric cue number {lines[0]!r}"
            ) from exc
        timestamp = lines[1]
        if not TIMESTAMP_RE.match(timestamp):
            raise ValueError(
                f"{path}: cue {cue_number} has invalid timestamp {timestamp!r}"
            )
        cues.append((cue_number, timestamp, lines[2:]))
    return cues


def write_srt(
    path: Path,
    cues: list[tuple[int, str, list[str]]],
    crlf: bool = True,
    bom: bool = True,
) -> None:
    blocks = []
    for number, timestamp, body in cues:
        blocks.append("\n".join([str(number), timestamp, *body]))
    text = "\n\n".join(blocks) + "\n"
    if crlf:
        text = text.replace("\n", "\r\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = text.encode("utf-8")
    if bom:
        payload = bytes([0xEF, 0xBB, 0xBF]) + payload
    path.write_bytes(payload)


def file_format(path: Path) -> tuple[bool, int, int, int]:
    """Return BOM presence plus CRLF, bare-LF, and bare-CR counts."""

    raw = path.read_bytes()
    has_bom = raw.startswith(bytes([0xEF, 0xBB, 0xBF]))
    payload = raw[3:] if has_bom else raw
    crlf_count = payload.count(b"\r\n")
    remainder = payload.replace(b"\r\n", b"")
    return has_bom, crlf_count, remainder.count(b"\n"), remainder.count(b"\r")


def timestamp_bounds(timestamp: str) -> tuple[int, int]:
    """Return the visible SRT interval as integer milliseconds."""

    def to_milliseconds(value: str) -> int:
        hours, minutes, rest = value.split(":")
        seconds, milliseconds = rest.split(",")
        return (
            int(hours) * 3_600_000
            + int(minutes) * 60_000
            + int(seconds) * 1_000
            + int(milliseconds)
        )

    start, end_and_settings = timestamp.split(" --> ", maxsplit=1)
    end = end_and_settings.split(" ", maxsplit=1)[0]
    return to_milliseconds(start), to_milliseconds(end)


def inspect(path: Path) -> int:
    cues = parse_srt(path)
    if not cues:
        print("cues: 0")
        return 0
    has_bom, crlf_count, bare_lf_count, bare_cr_count = file_format(path)
    blank = [
        number for number, _, body in cues if not any(line.strip() for line in body)
    ]
    intervals = [timestamp_bounds(timestamp) for _, timestamp, _ in cues]
    overlaps = [
        (cues[index - 1][0], cues[index][0])
        for index in range(1, len(cues))
        if intervals[index][0] < intervals[index - 1][1]
    ]
    gaps = [
        (
            intervals[index][0] - intervals[index - 1][1],
            cues[index - 1][0],
            cues[index][0],
        )
        for index in range(1, len(cues))
        if intervals[index][0] >= intervals[index - 1][1]
    ]
    longest_gap = max(gaps, default=(0, cues[0][0], cues[0][0]))
    tag_counts = Counter(
        tag for _, _, body in cues for tag in TAG_RE.findall("\n".join(body))
    )
    speaker_labels: list[tuple[int, str]] = []
    sdh_lines: list[tuple[int, str]] = []
    for number, _, body in cues:
        for line in body:
            visible = TAG_RE.sub("", line)
            if re.match(r"^\s*[A-Za-z][A-Za-z .'-]{1,24}:", visible):
                speaker_labels.append((number, visible))
            if ENGLISH_SDH_RE.match(visible):
                sdh_lines.append((number, visible))
    print(f"cues: {len(cues)}")
    print(f"first: {cues[0][0]}")
    print(f"last: {cues[-1][0]}")
    print(
        f"sequential: {[n for n, _, _ in cues] == list(range(cues[0][0], cues[-1][0] + 1))}"
    )
    print(f"blank_cues: {blank}")
    print(f"starts_ms: {intervals[0][0]}")
    print(f"ends_ms: {intervals[-1][1]}")
    print(f"overlap_pair_count: {len(overlaps)}")
    print(f"overlap_pairs_sample: {overlaps[:20]}")
    print(
        "longest_gap_ms: "
        f"{longest_gap[0]} (between cues {longest_gap[1]} and {longest_gap[2]})"
    )
    print(f"max_body_lines: {max(len(body) for _, _, body in cues)}")
    print(f"formatting_tags: {dict(tag_counts)}")
    print(f"speaker_label_sample: {speaker_labels[:20]}")
    print(f"sdh_sample: {sdh_lines[:20]}")
    print(f"utf8_bom: {has_bom}")
    print(f"crlf: {crlf_count}")
    print(f"bare_lf: {bare_lf_count}")
    print(f"bare_cr: {bare_cr_count}")
    return 0


def split(path: Path, out_dir: Path, size: int, suffix: str) -> int:
    cues = parse_srt(path)
    out_dir.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(cues), size):
        chunk = cues[start : start + size]
        first, last = chunk[0][0], chunk[-1][0]
        write_srt(out_dir / f"chunk-{first:04d}-{last:04d}.{suffix}.srt", chunk)
    print(
        f"wrote {((len(cues) + size - 1) // size) if cues else 0} chunks to {out_dir}"
    )
    return 0


def init_job(
    source: Path,
    work_dir: Path,
    source_tag: str,
    targets: list[str] | None,
    stem: str | None,
    output_dir: str,
) -> int:
    """Create a portable subtitle job with a source snapshot and editable workbook."""

    if not source.is_file():
        raise ValueError(f"source SRT does not exist: {source}")
    manifest_path = work_dir / "manifest.json"
    if manifest_path.exists():
        raise ValueError(f"job already exists: {manifest_path}")

    cues = parse_srt(source)
    if not cues:
        raise ValueError("cannot initialize a job from an empty SRT")
    selected_targets = targets or list(DEFAULT_TARGETS)
    if len(selected_targets) != len(set(selected_targets)):
        raise ValueError("target language tags must be unique")
    if source_tag in selected_targets:
        raise ValueError("source and target language tags must differ")
    staging_dir = Path(output_dir)
    if staging_dir.is_absolute() or ".." in staging_dir.parts:
        raise ValueError(
            "--output-dir must be a job-relative staging directory; "
            "use deliver-job for the external destination"
        )

    selected_stem = stem or LANGUAGE_TAG_RE.sub("", source.stem)
    snapshot = work_dir / "source" / "source.srt"
    snapshot.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, snapshot)

    columns = [
        *WORKBOOK_BASE_COLUMNS,
        *selected_targets,
        *WORKBOOK_TRAILING_COLUMNS,
    ]
    workbook_path = work_dir / "workbook.tsv"
    workbook_path.parent.mkdir(parents=True, exist_ok=True)
    with workbook_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\t".join(columns) + "\n")
        for number, timestamp, body in cues:
            source_text = "\n".join(body)
            row = [
                str(number),
                encode_workbook_cell(timestamp),
                encode_workbook_cell(source_text),
                encode_workbook_cell(source_text),
                *("" for _ in selected_targets),
                "unreviewed",
                "",
            ]
            handle.write("\t".join(row) + "\n")

    glossary_path = work_dir / "glossary.tsv"
    glossary_path.write_text(
        "\t".join(["source", source_tag, *selected_targets, "notes"]) + "\n",
        encoding="utf-8",
    )
    (work_dir / "uncertainties.jsonl").write_text("", encoding="utf-8")
    (work_dir / "qa-waivers.jsonl").write_text("", encoding="utf-8")

    outputs = {
        source_tag: f"{selected_stem}.refined.{source_tag}.srt",
        **{target: f"{selected_stem}.{target}.srt" for target in selected_targets},
    }
    manifest = {
        "version": 1,
        "source": {
            "original_path": str(source.resolve()),
            "snapshot": str(snapshot.relative_to(work_dir)),
            "sha256": sha256_file(snapshot),
            "cue_count": len(cues),
            "source_tag": source_tag,
        },
        "targets": selected_targets,
        "stem": selected_stem,
        "workbook": str(workbook_path.relative_to(work_dir)),
        "glossary": str(glossary_path.relative_to(work_dir)),
        "uncertainties": "uncertainties.jsonl",
        "qa_waivers": "qa-waivers.jsonl",
        "output_dir": output_dir,
        "outputs": outputs,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"initialized job: {manifest_path}")
    print(f"source cues: {len(cues)}")
    print(f"targets: {', '.join(selected_targets)}")
    print(f"workbook: {workbook_path}")
    return 0


def parse_workbook(
    path: Path,
    targets: list[str],
) -> list[dict[str, str]]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if not lines:
        raise ValueError(f"{path}: empty workbook")
    expected_columns = [
        *WORKBOOK_BASE_COLUMNS,
        *targets,
        *WORKBOOK_TRAILING_COLUMNS,
    ]
    columns = lines[0].split("\t")
    if columns != expected_columns:
        raise ValueError(
            f"{path}: expected columns {expected_columns!r}, got {columns!r}"
        )

    rows: list[dict[str, str]] = []
    seen_numbers: set[int] = set()
    for line_number, raw_line in enumerate(lines[1:], start=2):
        fields = raw_line.split("\t")
        if len(fields) != len(columns):
            raise ValueError(
                f"{path}:{line_number}: expected {len(columns)} fields, got {len(fields)}"
            )
        row = dict(zip(columns, fields, strict=True))
        try:
            number = int(row["number"])
        except ValueError as exc:
            raise ValueError(
                f"{path}:{line_number}: invalid cue number {row['number']!r}"
            ) from exc
        if number in seen_numbers:
            raise ValueError(f"{path}:{line_number}: duplicate cue {number}")
        seen_numbers.add(number)
        row["number"] = str(number)
        for column in columns[1:]:
            row[column] = decode_workbook_cell(row[column])
        rows.append(row)
    return rows


def write_workbook(
    path: Path,
    rows: list[dict[str, str]],
    targets: list[str],
) -> None:
    columns = [
        *WORKBOOK_BASE_COLUMNS,
        *targets,
        *WORKBOOK_TRAILING_COLUMNS,
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("\t".join(columns) + "\n")
        for row in rows:
            fields = [str(int(row["number"]))]
            fields.extend(encode_workbook_cell(row[column]) for column in columns[1:])
            handle.write("\t".join(fields) + "\n")


def split_workbook(job: Path, out_dir: Path, size: int) -> int:
    """Split one job workbook into disjoint cue-range workbooks."""

    if size <= 0:
        raise ValueError("chunk size must be positive")
    manifest_path, manifest = resolve_manifest(job)
    targets = list(manifest["targets"])
    workbook_path = path_from_manifest(manifest_path, manifest["workbook"])
    rows = parse_workbook(workbook_path, targets)
    if out_dir.exists() and any(out_dir.glob("*.tsv")):
        raise ValueError(f"chunk directory already contains TSV files: {out_dir}")
    out_dir.mkdir(parents=True, exist_ok=True)
    for start in range(0, len(rows), size):
        chunk = rows[start : start + size]
        first = int(chunk[0]["number"])
        last = int(chunk[-1]["number"])
        write_workbook(
            out_dir / f"chunk-{first:04d}-{last:04d}.tsv",
            chunk,
            targets,
        )
    print(f"wrote {(len(rows) + size - 1) // size} workbook chunks to {out_dir}")
    return 0


def merge_workbook(job: Path, in_dir: Path) -> int:
    """Merge disjoint workbook chunks back into the job after integrity checks."""

    manifest_path, manifest = resolve_manifest(job)
    targets = list(manifest["targets"])
    chunk_paths = sorted(in_dir.glob("*.tsv"))
    if not chunk_paths:
        raise ValueError(f"no .tsv workbook chunks found in {in_dir}")
    rows_by_number: dict[int, dict[str, str]] = {}
    for path in chunk_paths:
        for row in parse_workbook(path, targets):
            number = int(row["number"])
            if number in rows_by_number:
                raise ValueError(f"duplicate cue {number} across workbook chunks")
            rows_by_number[number] = row

    source_path = path_from_manifest(manifest_path, manifest["source"]["snapshot"])
    expected_numbers = [number for number, _, _ in parse_srt(source_path)]
    actual_numbers = sorted(rows_by_number)
    if actual_numbers != expected_numbers:
        missing = sorted(set(expected_numbers) - set(actual_numbers))
        extra = sorted(set(actual_numbers) - set(expected_numbers))
        raise ValueError(
            f"workbook chunk coverage differs; missing={missing[:20]} extra={extra[:20]}"
        )
    workbook_path = path_from_manifest(manifest_path, manifest["workbook"])
    write_workbook(
        workbook_path,
        [rows_by_number[number] for number in expected_numbers],
        targets,
    )
    print(
        f"merged {len(chunk_paths)} workbook chunks, "
        f"{len(expected_numbers)} cues -> {workbook_path}"
    )
    return 0


def body_from_workbook(value: str, label: str, number: int) -> list[str]:
    body = value.split("\n")
    if not value or any(not line for line in body):
        raise ValueError(f"cue {number}: {label} body is blank or has an empty line")
    return body


def assemble_job(job: Path) -> int:
    """Assemble refined and translated SRTs from a complete job workbook."""

    manifest_path, manifest = resolve_manifest(job)
    source_info = manifest["source"]
    source_path = path_from_manifest(manifest_path, source_info["snapshot"])
    if sha256_file(source_path) != source_info["sha256"]:
        raise ValueError("source snapshot hash differs from manifest")
    source_cues = parse_srt(source_path)
    targets = list(manifest["targets"])
    workbook_path = path_from_manifest(manifest_path, manifest["workbook"])
    rows = parse_workbook(workbook_path, targets)
    if len(rows) != len(source_cues):
        raise ValueError(
            f"workbook cue count differs: source={len(source_cues)} workbook={len(rows)}"
        )

    refined: list[tuple[int, str, list[str]]] = []
    translated: dict[str, list[tuple[int, str, list[str]]]] = {
        target: [] for target in targets
    }
    for source_cue, row in zip(source_cues, rows, strict=True):
        number, timestamp, source_body = source_cue
        row_number = int(row["number"])
        if row_number != number or row["timestamp"] != timestamp:
            raise ValueError(f"workbook skeleton differs at cue {number}")
        if row["source"] != "\n".join(source_body):
            raise ValueError(f"workbook source text differs at cue {number}")
        refined.append(
            (
                number,
                timestamp,
                body_from_workbook(row["refined"], "refined", number),
            )
        )
        for target in targets:
            translated[target].append(
                (
                    number,
                    timestamp,
                    body_from_workbook(row[target], target, number),
                )
            )

    output_dir = path_from_manifest(manifest_path, manifest["output_dir"])
    source_tag = source_info["source_tag"]
    outputs = manifest["outputs"]
    assembled: dict[str, dict[str, str]] = {}
    all_tracks = {source_tag: refined, **translated}
    for language, cues in all_tracks.items():
        output_path = output_dir / outputs[language]
        write_srt(output_path, cues, crlf=True, bom=True)
        try:
            recorded_path = str(output_path.relative_to(manifest_path.parent))
        except ValueError:
            recorded_path = str(output_path.resolve())
        assembled[language] = {
            "path": recorded_path,
            "sha256": sha256_file(output_path),
        }
        print(f"wrote {language}: {output_path}")

    manifest["assembled"] = assembled
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


def compare_sources(
    source: Path,
    reference: Path,
    output: Path | None,
) -> int:
    """Report source-family identity and timing compatibility evidence."""

    source_cues = parse_srt(source)
    reference_cues = parse_srt(reference)
    source_normalized = [normalized_cue_text(lines) for _, _, lines in source_cues]
    reference_normalized = [
        normalized_cue_text(lines) for _, _, lines in reference_cues
    ]
    source_counts = Counter(text for text in source_normalized if len(text) >= 8)
    reference_counts = Counter(text for text in reference_normalized if len(text) >= 8)
    reference_unique = {
        text: index
        for index, text in enumerate(reference_normalized)
        if len(text) >= 8 and reference_counts[text] == 1
    }

    offsets: list[int] = []
    anchors: list[dict[str, int]] = []
    reference_anchor_indexes: list[int] = []
    for source_index, text in enumerate(source_normalized):
        if len(text) < 8 or source_counts[text] != 1 or text not in reference_unique:
            continue
        reference_index = reference_unique[text]
        reference_anchor_indexes.append(reference_index)
        source_center = sum(timestamp_bounds(source_cues[source_index][1])) // 2
        reference_center = (
            sum(timestamp_bounds(reference_cues[reference_index][1])) // 2
        )
        offset = reference_center - source_center
        offsets.append(offset)
        anchors.append(
            {
                "source_number": source_cues[source_index][0],
                "reference_number": reference_cues[reference_index][0],
                "offset_ms": offset,
            }
        )

    raw_equal = sha256_file(source) == sha256_file(reference)
    normalized_equal = normalized_track_hash(source_cues) == normalized_track_hash(
        reference_cues
    )
    skeleton_equal = [(number, timestamp) for number, timestamp, _ in source_cues] == [
        (number, timestamp) for number, timestamp, _ in reference_cues
    ]
    median_offset = int(statistics.median(offsets)) if offsets else None
    median_absolute_deviation = (
        int(statistics.median(abs(value - median_offset) for value in offsets))
        if offsets and median_offset is not None
        else None
    )
    offset_range = max(offsets) - min(offsets) if offsets else None
    increasing_tails: list[int] = []
    for reference_index in reference_anchor_indexes:
        position = bisect.bisect_left(increasing_tails, reference_index)
        if position == len(increasing_tails):
            increasing_tails.append(reference_index)
        else:
            increasing_tails[position] = reference_index
    monotonic_anchor_ratio = (
        len(increasing_tails) / len(reference_anchor_indexes)
        if reference_anchor_indexes
        else None
    )

    if raw_equal or normalized_equal:
        classification = "same_source_family"
    elif skeleton_equal:
        classification = "same_timing_skeleton"
    elif (
        len(offsets) >= 5
        and median_absolute_deviation is not None
        and offset_range is not None
        and monotonic_anchor_ratio is not None
        and median_absolute_deviation <= 1_500
        and offset_range <= 5_000
        and monotonic_anchor_ratio >= 0.8
    ):
        classification = "likely_release_compatible"
    elif (
        len(offsets) >= 5
        and median_absolute_deviation is not None
        and offset_range is not None
        and (
            median_absolute_deviation > 3_000
            or offset_range > 10_000
            or (monotonic_anchor_ratio is not None and monotonic_anchor_ratio < 0.7)
        )
    ):
        classification = "different_timing_or_edit"
    else:
        classification = "insufficient_evidence"

    report = {
        "version": 1,
        "source": {
            "path": str(source.resolve()),
            "sha256": sha256_file(source),
            "normalized_sha256": normalized_track_hash(source_cues),
            "cue_count": len(source_cues),
        },
        "reference": {
            "path": str(reference.resolve()),
            "sha256": sha256_file(reference),
            "normalized_sha256": normalized_track_hash(reference_cues),
            "cue_count": len(reference_cues),
        },
        "raw_equal": raw_equal,
        "normalized_text_equal": normalized_equal,
        "timestamp_skeleton_equal": skeleton_equal,
        "exact_text_anchor_count": len(offsets),
        "median_reference_minus_source_ms": median_offset,
        "median_absolute_deviation_ms": median_absolute_deviation,
        "offset_range_ms": offset_range,
        "monotonic_anchor_ratio": (
            round(monotonic_anchor_ratio, 4)
            if monotonic_anchor_ratio is not None
            else None
        ),
        "classification": classification,
        "anchor_sample": anchors[:50],
    }
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
        print(f"wrote: {output}")
    return 0


def load_compatibility_report(
    path: Path,
    source: Path,
    reference: Path,
    allow_unsafe: bool,
) -> int:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid compatibility report JSON") from exc
    if not isinstance(report, dict) or report.get("version") != 1:
        raise ValueError(f"{path}: unsupported compatibility report")
    if report.get("source", {}).get("sha256") != sha256_file(source):
        raise ValueError(f"{path}: source hash does not match")
    if report.get("reference", {}).get("sha256") != sha256_file(reference):
        raise ValueError(f"{path}: reference hash does not match")
    classification = report.get("classification")
    safe = {"same_timing_skeleton", "likely_release_compatible"}
    if classification not in safe and not allow_unsafe:
        raise ValueError(
            f"cross-reference refused for classification {classification!r}; "
            "inspect manually or pass --allow-unsafe explicitly"
        )
    offset = report.get("median_reference_minus_source_ms")
    return (
        int(offset) if classification == "likely_release_compatible" and offset else 0
    )


def cross_reference(
    source: Path,
    reference: Path,
    output: Path,
    compatibility_report: Path | None = None,
    allow_unsafe: bool = False,
) -> int:
    """Align an independent reference transcript to the source timing skeleton.

    This produces evidence for an LLM or human reviewer; it never chooses or rewrites text.
    """

    source_cues = parse_srt(source)
    reference_cues = parse_srt(reference)
    if compatibility_report:
        reference_offset_ms = load_compatibility_report(
            compatibility_report, source, reference, allow_unsafe
        )
    else:
        reference_offset_ms = 0
        print(
            "WARNING: no compatibility report supplied; run compare-sources first",
            file=sys.stderr,
        )
    reference_intervals = [
        (start - reference_offset_ms, end - reference_offset_ms)
        for start, end in (
            timestamp_bounds(timestamp) for _, timestamp, _ in reference_cues
        )
    ]
    output.parent.mkdir(parents=True, exist_ok=True)

    reference_index = 0
    matched = 0
    with output.open("w", encoding="utf-8") as handle:
        for source_number, source_timestamp, source_lines in source_cues:
            source_start, source_end = timestamp_bounds(source_timestamp)
            while (
                reference_index < len(reference_cues)
                and reference_intervals[reference_index][1] <= source_start
            ):
                reference_index += 1

            aligned = []
            candidate_index = max(0, reference_index - 1)
            while candidate_index < len(reference_cues):
                reference_start, reference_end = reference_intervals[candidate_index]
                if reference_start >= source_end:
                    break
                overlap = min(source_end, reference_end) - max(
                    source_start, reference_start
                )
                if overlap > 0:
                    number, timestamp, lines = reference_cues[candidate_index]
                    aligned.append(
                        {
                            "number": number,
                            "timestamp": timestamp,
                            "lines": lines,
                            "overlap_ms": overlap,
                        }
                    )
                candidate_index += 1

            if not aligned and reference_cues:
                source_center = (source_start + source_end) // 2
                nearest_index = min(
                    range(
                        max(0, reference_index - 2),
                        min(len(reference_cues), reference_index + 3),
                    ),
                    key=lambda index: abs(
                        source_center
                        - (
                            reference_intervals[index][0]
                            + reference_intervals[index][1]
                        )
                        // 2
                    ),
                    default=None,
                )
                if nearest_index is not None:
                    reference_center = sum(reference_intervals[nearest_index]) // 2
                    if abs(source_center - reference_center) <= 1_500:
                        number, timestamp, lines = reference_cues[nearest_index]
                        aligned.append(
                            {
                                "number": number,
                                "timestamp": timestamp,
                                "lines": lines,
                                "overlap_ms": 0,
                            }
                        )

            if aligned:
                matched += 1
            handle.write(
                json.dumps(
                    {
                        "source_number": source_number,
                        "source_timestamp": source_timestamp,
                        "source_lines": source_lines,
                        "references": aligned,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    print(f"source cues: {len(source_cues)}")
    print(f"reference cues: {len(reference_cues)}")
    print(f"source cues with reference evidence: {matched}")
    print(f"reference offset applied: {reference_offset_ms} ms")
    print(f"wrote: {output}")
    return 0


def review(
    source: Path,
    candidate: Path,
    output: Path,
    cross_reference_path: Path | None,
) -> int:
    """Write changed cue bodies with optional independent evidence for human/LLM review."""

    source_cues = parse_srt(source)
    candidate_cues = parse_srt(candidate)
    source_skeleton = [(number, timestamp) for number, timestamp, _ in source_cues]
    candidate_skeleton = [
        (number, timestamp) for number, timestamp, _ in candidate_cues
    ]
    if source_skeleton != candidate_skeleton:
        raise ValueError("source and candidate cue number/timestamp skeletons differ")

    references: dict[int, list[dict[str, object]]] = {}
    if cross_reference_path:
        if cross_reference_path.suffix.lower() != ".jsonl":
            raise ValueError(
                f"{cross_reference_path}: expected cross-reference JSONL produced "
                "by the cross-reference command, not an SRT or other source file"
            )
        for line_number, line in enumerate(
            cross_reference_path.read_text(encoding="utf-8-sig").splitlines(), start=1
        ):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"{cross_reference_path}: invalid JSON on line {line_number}"
                ) from exc
            if not isinstance(record, dict) or "source_number" not in record:
                raise ValueError(
                    f"{cross_reference_path}:{line_number}: expected a cross-reference "
                    "JSON object produced by the cross-reference command"
                )
            record_references = record.get("references", [])
            if not isinstance(record_references, list) or any(
                not isinstance(item, dict) for item in record_references
            ):
                raise ValueError(
                    f"{cross_reference_path}:{line_number}: references must be a list "
                    "of JSON objects"
                )
            references[int(record["source_number"])] = record_references

    output.parent.mkdir(parents=True, exist_ok=True)
    changed = 0
    with output.open("w", encoding="utf-8") as handle:
        for source_cue, candidate_cue in zip(source_cues, candidate_cues, strict=True):
            number, timestamp, source_lines = source_cue
            _, _, candidate_lines = candidate_cue
            if source_lines == candidate_lines:
                continue
            changed += 1
            handle.write(
                json.dumps(
                    {
                        "number": number,
                        "timestamp": timestamp,
                        "source_lines": source_lines,
                        "candidate_lines": candidate_lines,
                        "references": references.get(number, []),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    print(f"source cues: {len(source_cues)}")
    print(f"changed cue bodies: {changed}")
    print(f"wrote: {output}")
    return 0


def lint(
    path: Path,
    max_chars_per_line: int,
    max_cps: float,
    scan_regexes: list[str],
    strict: bool,
) -> int:
    """Report reading-load and residual-text candidates without changing subtitles."""

    cues = parse_srt(path)
    long_lines: list[tuple[int, int, str]] = []
    high_cps: list[tuple[int, float, str]] = []
    regex_hits: list[tuple[int, str, str]] = []
    compiled_patterns = [(pattern, re.compile(pattern)) for pattern in scan_regexes]

    for number, timestamp, body in cues:
        visible_lines = [TAG_RE.sub("", line) for line in body]
        for line in visible_lines:
            if len(line) > max_chars_per_line:
                long_lines.append((number, len(line), line))

        start, end = timestamp_bounds(timestamp)
        duration_seconds = max((end - start) / 1_000, 0.001)
        visible_text = " ".join(line.strip() for line in visible_lines if line.strip())
        visible_characters = len(re.sub(r"\s+", "", visible_text))
        characters_per_second = visible_characters / duration_seconds
        if characters_per_second > max_cps:
            high_cps.append((number, characters_per_second, visible_text))

        for pattern, compiled_pattern in compiled_patterns:
            if compiled_pattern.search(visible_text):
                regex_hits.append((number, pattern, visible_text))

    print(f"cues: {len(cues)}")
    print(f"long_line_count: {len(long_lines)}")
    for number, length, line in long_lines[:50]:
        print(f"LONG cue={number} chars={length}: {line}")
    print(f"high_cps_count: {len(high_cps)}")
    for number, characters_per_second, text in sorted(
        high_cps, key=lambda item: item[1], reverse=True
    )[:50]:
        print(f"CPS cue={number} cps={characters_per_second:.1f}: {text}")
    print(f"regex_hit_count: {len(regex_hits)}")
    for number, pattern, text in regex_hits[:50]:
        print(f"REGEX cue={number} pattern={pattern!r}: {text}")

    has_findings = bool(long_lines or high_cps or regex_hits)
    return 1 if strict and has_findings else 0


def glossary_forbidden_variants(path: Path, profile: str) -> set[str]:
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    if not lines:
        return set()
    columns = lines[0].split("\t")
    if "source" not in columns or profile not in columns:
        raise ValueError(
            f"{path}: glossary must contain source and {profile!r} columns"
        )
    forbidden: set[str] = set()
    for line_number, raw_line in enumerate(lines[1:], start=2):
        if not raw_line.strip():
            continue
        fields = raw_line.split("\t")
        if len(fields) != len(columns):
            raise ValueError(
                f"{path}:{line_number}: expected {len(columns)} fields, got {len(fields)}"
            )
        row = dict(zip(columns, fields, strict=True))
        canonical = row[profile].strip()
        if not canonical:
            continue
        for language, value in row.items():
            variant = value.strip()
            if (
                language.startswith("zh-")
                and language != profile
                and variant
                and variant != canonical
            ):
                forbidden.add(variant)
    return forbidden


def load_qa_waivers(path: Path | None) -> dict[tuple[str, int, str], str]:
    if path is None:
        return {}
    waivers: dict[tuple[str, int, str], str] = {}
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid waiver JSON") from exc
        if not isinstance(record, dict):
            raise ValueError(f"{path}:{line_number}: waiver must be a JSON object")
        try:
            key = (
                str(record["profile"]),
                int(record["cue"]),
                str(record["kind"]),
            )
            reason = str(record["reason"]).strip()
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"{path}:{line_number}: waiver requires profile, cue, kind, and reason"
            ) from exc
        if not reason:
            raise ValueError(f"{path}:{line_number}: waiver reason cannot be blank")
        waivers[key] = reason
    return waivers


def qa(
    source: Path,
    target: Path,
    profile: str,
    max_chars_per_line: int | None,
    max_cps: float | None,
    max_lines: int | None,
    allowed_latin: list[str],
    forbidden_text: list[str],
    glossary: Path | None,
    scan_regexes: list[str],
    waiver_path: Path | None,
    report_path: Path | None,
    strict: bool,
) -> int:
    """Run one structural and language-profile QA pass without rewriting text."""

    settings = QA_PROFILES[profile]
    line_limit = max_chars_per_line or int(settings["max_chars_per_line"])
    cps_limit = max_cps or float(settings["max_cps"])
    line_count_limit = max_lines or int(settings["max_lines"])
    source_cues = parse_srt(source)
    target_cues = parse_srt(target)
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    source_skeleton = [(number, timestamp) for number, timestamp, _ in source_cues]
    target_skeleton = [(number, timestamp) for number, timestamp, _ in target_cues]
    if source_skeleton != target_skeleton:
        errors.append(
            {
                "kind": "skeleton",
                "message": "cue number/timestamp skeleton differs",
            }
        )

    has_bom, crlf_count, bare_lf_count, bare_cr_count = file_format(target)
    if not has_bom or crlf_count == 0 or bare_lf_count or bare_cr_count:
        errors.append(
            {
                "kind": "player_format",
                "message": (
                    f"expected UTF-8 BOM and pure CRLF; bom={has_bom} "
                    f"crlf={crlf_count} bare_lf={bare_lf_count} bare_cr={bare_cr_count}"
                ),
            }
        )

    source_by_number = {
        number: (timestamp, body) for number, timestamp, body in source_cues
    }
    allowed_tokens = {token.casefold() for token in DEFAULT_ALLOWED_LATIN}
    allowed_tokens.update(token.casefold() for token in allowed_latin)
    forbidden = set(forbidden_text)
    if glossary:
        forbidden.update(glossary_forbidden_variants(glossary, profile))
    waivers = load_qa_waivers(waiver_path)
    compiled_patterns = [(pattern, re.compile(pattern)) for pattern in scan_regexes]

    for number, timestamp, body in target_cues:
        source_entry = source_by_number.get(number)
        if source_entry:
            source_timestamp, source_body = source_entry
            if timestamp != source_timestamp:
                errors.append(
                    {
                        "kind": "timestamp",
                        "cue": number,
                        "message": "timestamp differs from source",
                    }
                )
            if TAG_RE.findall("\n".join(body)) != TAG_RE.findall(
                "\n".join(source_body)
            ):
                errors.append(
                    {
                        "kind": "tags",
                        "cue": number,
                        "message": "formatting-tag sequence differs from source",
                    }
                )
        if not body or not any(line.strip() for line in body):
            errors.append(
                {"kind": "blank", "cue": number, "message": "blank target cue"}
            )
            continue
        if len(body) > line_count_limit:
            warnings.append(
                {
                    "kind": "line_count",
                    "cue": number,
                    "value": len(body),
                    "limit": line_count_limit,
                    "text": " / ".join(body),
                }
            )

        visible_lines = [TAG_RE.sub("", line) for line in body]
        for line in visible_lines:
            if len(line) > line_limit:
                warnings.append(
                    {
                        "kind": "line_length",
                        "cue": number,
                        "value": len(line),
                        "limit": line_limit,
                        "text": line,
                    }
                )

        visible_text = " ".join(line.strip() for line in visible_lines if line.strip())
        start, end = timestamp_bounds(timestamp)
        duration_seconds = max((end - start) / 1_000, 0.001)
        character_count = len(re.sub(r"\s+", "", visible_text))
        characters_per_second = character_count / duration_seconds
        if characters_per_second > cps_limit:
            warnings.append(
                {
                    "kind": "cps",
                    "cue": number,
                    "value": round(characters_per_second, 2),
                    "limit": cps_limit,
                    "text": visible_text,
                }
            )

        if CYRILLIC_RE.search(visible_text):
            warnings.append(
                {
                    "kind": "cyrillic",
                    "cue": number,
                    "text": visible_text,
                }
            )
        if profile.startswith("zh-"):
            unexpected_tokens = sorted(
                {
                    token
                    for token in LATIN_TOKEN_RE.findall(visible_text)
                    if token.casefold() not in allowed_tokens
                },
                key=str.casefold,
            )
            if unexpected_tokens:
                warnings.append(
                    {
                        "kind": "latin",
                        "cue": number,
                        "tokens": unexpected_tokens,
                        "text": visible_text,
                    }
                )
        for value in sorted(forbidden, key=len, reverse=True):
            if value and value in visible_text:
                warnings.append(
                    {
                        "kind": "forbidden_text",
                        "cue": number,
                        "value": value,
                        "text": visible_text,
                    }
                )
        for pattern, compiled_pattern in compiled_patterns:
            if compiled_pattern.search(visible_text):
                warnings.append(
                    {
                        "kind": "regex",
                        "cue": number,
                        "pattern": pattern,
                        "text": visible_text,
                    }
                )

    for warning in warnings:
        cue = warning.get("cue")
        if not isinstance(cue, int):
            continue
        reason = waivers.get((profile, cue, str(warning["kind"])))
        if reason:
            warning["waived"] = True
            warning["waiver_reason"] = reason
    unwaived_warnings = [warning for warning in warnings if not warning.get("waived")]
    summary = {
        "source_cues": len(source_cues),
        "target_cues": len(target_cues),
        "profile": profile,
        "max_chars_per_line": line_limit,
        "max_cps": cps_limit,
        "max_lines": line_count_limit,
        "cps_definition": "visible Unicode code points excluding whitespace per second",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "waived_warning_count": len(warnings) - len(unwaived_warnings),
        "unwaived_warning_count": len(unwaived_warnings),
        "warnings_by_kind": dict(Counter(item["kind"] for item in warnings)),
    }
    report = {"summary": summary, "errors": errors, "warnings": warnings}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    for finding in [*errors, *warnings][:50]:
        print(json.dumps(finding, ensure_ascii=False))
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"wrote: {report_path}")
    return 1 if errors or (strict and unwaived_warnings) else 0


def chunk_sort_key(path: Path) -> tuple[int, int, str]:
    match = CHUNK_RE.search(path.name)
    if match:
        first = int(match.group(1) or match.group(3))
        last = int(match.group(2) or match.group(4))
        return (first, last, path.name)
    cues = parse_srt(path)
    first = cues[0][0] if cues else 0
    last = cues[-1][0] if cues else 0
    return (first, last, path.name)


def merge(in_dir: Path, output: Path) -> int:
    chunk_paths = sorted(in_dir.glob("*.srt"), key=chunk_sort_key)
    if not chunk_paths:
        raise ValueError(f"no .srt files found in {in_dir}")
    cues: list[tuple[int, str, list[str]]] = []
    for path in chunk_paths:
        cues.extend(parse_srt(path))
    write_srt(output, cues)
    print(f"merged {len(chunk_paths)} chunks, {len(cues)} cues -> {output}")
    return 0


def deliver_job(
    job: Path,
    destination: Path,
    overwrite: bool,
) -> int:
    """Atomically copy assembled artifacts and verify each copied hash."""

    manifest_path, manifest = resolve_manifest(job)
    assembled = manifest.get("assembled")
    if not isinstance(assembled, dict) or not assembled:
        raise ValueError("job has no assembled artifacts; run assemble-job first")
    destination.mkdir(parents=True, exist_ok=True)
    original_path = Path(manifest["source"]["original_path"])
    delivered: dict[str, dict[str, str]] = {}

    for language, artifact in assembled.items():
        if not isinstance(artifact, dict):
            raise ValueError(f"invalid assembled artifact for {language}")
        source_path = path_from_manifest(manifest_path, artifact["path"])
        expected_hash = artifact["sha256"]
        if not source_path.is_file() or sha256_file(source_path) != expected_hash:
            raise ValueError(f"assembled artifact changed or is missing: {source_path}")
        target_path = destination / manifest["outputs"][language]
        if target_path.resolve() == original_path.resolve():
            raise ValueError(f"refusing to overwrite original source: {target_path}")
        if target_path.exists() and not overwrite:
            raise ValueError(
                f"delivery target already exists: {target_path}; pass --overwrite "
                "only after confirming it is a generated output"
            )

        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=destination,
                prefix=f".{target_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                handle.write(source_path.read_bytes())
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, target_path)
        finally:
            if temporary_path and temporary_path.exists():
                temporary_path.unlink()
        copied_hash = sha256_file(target_path)
        if copied_hash != expected_hash:
            raise ValueError(f"copied hash mismatch: {target_path}")
        delivered[language] = {
            "path": str(target_path.resolve()),
            "sha256": copied_hash,
        }
        print(f"delivered {language}: {target_path}")

    receipt_path = manifest_path.parent / "delivery.json"
    receipt_path.write_text(
        json.dumps(
            {
                "version": 1,
                "destination": str(destination.resolve()),
                "artifacts": delivered,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"receipt: {receipt_path}")
    return 0


def validate(
    source: Path,
    target: Path,
    scan: bool = False,
    require_player_format: bool = False,
) -> int:
    src = parse_srt(source)
    dst = parse_srt(target)
    errors: list[str] = []

    if len(src) != len(dst):
        errors.append(f"cue count differs: source={len(src)} target={len(dst)}")

    src_skeleton = [(n, t) for n, t, _ in src]
    dst_skeleton = [(n, t) for n, t, _ in dst]
    if src_skeleton != dst_skeleton:
        errors.append("cue number/timestamp skeleton differs")

    if dst:
        expected = list(range(dst[0][0], dst[-1][0] + 1))
        actual = [n for n, _, _ in dst]
        if actual != expected:
            errors.append("target cue numbers are not sequential")

    src_blank = {n for n, _, body in src if not any(line.strip() for line in body)}
    dst_blank = {n for n, _, body in dst if not any(line.strip() for line in body)}
    unexpected_blank = sorted(dst_blank - src_blank)
    if unexpected_blank:
        errors.append(f"target has unexpected blank cues: {unexpected_blank[:20]}")

    target_text = target.read_text(encoding="utf-8-sig")
    has_bom, crlf_count, bare_lf_count, bare_cr_count = file_format(target)
    if require_player_format:
        if not has_bom:
            errors.append("target is missing a UTF-8 BOM")
        if crlf_count == 0 or bare_lf_count or bare_cr_count:
            errors.append(
                "target is not pure CRLF: "
                f"crlf={crlf_count} bare_lf={bare_lf_count} bare_cr={bare_cr_count}"
            )
    if target_text.count("<i>") != target_text.count("</i>"):
        errors.append(
            f"target italic tags are unbalanced: <i>={target_text.count('<i>')} </i>={target_text.count('</i>')}"
        )

    tag_mismatches = []
    for source_cue, target_cue in zip(src, dst, strict=False):
        source_number, _, source_body = source_cue
        target_number, _, target_body = target_cue
        if source_number != target_number:
            continue
        source_tags = TAG_RE.findall("\n".join(source_body))
        target_tags = TAG_RE.findall("\n".join(target_body))
        if source_tags != target_tags:
            tag_mismatches.append(source_number)
    if tag_mismatches:
        errors.append(f"preserved tag sequence differs in cues: {tag_mismatches[:20]}")

    if scan:
        marker_hits = []
        for line_no, line in enumerate(target_text.splitlines(), start=1):
            if ENGLISH_SDH_RE.search(line):
                marker_hits.append(f"{line_no}:{line}")
        if marker_hits:
            errors.append(
                "possible untranslated English SDH markers:\n"
                + "\n".join(marker_hits[:20])
            )

    print(f"source cues: {len(src)}")
    print(f"target cues: {len(dst)}")
    print(f"skeleton_equal: {src_skeleton == dst_skeleton}")
    print(f"blank_target_cues: {sorted(dst_blank)}")
    print(
        f"italic_tags: <i>={target_text.count('<i>')} </i>={target_text.count('</i>')}"
    )
    print(f"tag_mismatch_cues: {tag_mismatches}")
    if require_player_format:
        print(
            "player_format: "
            f"utf8_bom={has_bom} crlf={crlf_count} "
            f"bare_lf={bare_lf_count} bare_cr={bare_cr_count}"
        )

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("OK")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="SRT translation workflow helpers")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_parser = sub.add_parser("inspect")
    inspect_parser.add_argument("path", type=Path)

    split_parser = sub.add_parser("split")
    split_parser.add_argument("path", type=Path)
    split_parser.add_argument("out_dir", type=Path)
    split_parser.add_argument("--size", type=int, default=120)
    split_parser.add_argument("--suffix", default="en")

    init_job_parser = sub.add_parser("init-job")
    init_job_parser.add_argument("source", type=Path)
    init_job_parser.add_argument("work_dir", type=Path)
    init_job_parser.add_argument("--source-tag", default="en")
    init_job_parser.add_argument("--target", action="append")
    init_job_parser.add_argument("--stem")
    init_job_parser.add_argument("--output-dir", default="deliverables")

    assemble_job_parser = sub.add_parser("assemble-job")
    assemble_job_parser.add_argument("job", type=Path)

    split_workbook_parser = sub.add_parser("split-workbook")
    split_workbook_parser.add_argument("job", type=Path)
    split_workbook_parser.add_argument("out_dir", type=Path)
    split_workbook_parser.add_argument("--size", type=int, default=150)

    merge_workbook_parser = sub.add_parser("merge-workbook")
    merge_workbook_parser.add_argument("job", type=Path)
    merge_workbook_parser.add_argument("in_dir", type=Path)

    compare_parser = sub.add_parser("compare-sources")
    compare_parser.add_argument("source", type=Path)
    compare_parser.add_argument("reference", type=Path)
    compare_parser.add_argument("--output", type=Path)

    cross_reference_parser = sub.add_parser("cross-reference")
    cross_reference_parser.add_argument("source", type=Path)
    cross_reference_parser.add_argument("reference", type=Path)
    cross_reference_parser.add_argument("output", type=Path)
    cross_reference_parser.add_argument("--compatibility-report", type=Path)
    cross_reference_parser.add_argument("--allow-unsafe", action="store_true")

    review_parser = sub.add_parser("review")
    review_parser.add_argument("source", type=Path)
    review_parser.add_argument("candidate", type=Path)
    review_parser.add_argument("output", type=Path)
    review_parser.add_argument("--cross-reference", type=Path)

    lint_parser = sub.add_parser("lint")
    lint_parser.add_argument("path", type=Path)
    lint_parser.add_argument("--max-chars-per-line", type=int, default=42)
    lint_parser.add_argument("--max-cps", type=float, default=20.0)
    lint_parser.add_argument("--scan-regex", action="append", default=[])
    lint_parser.add_argument("--strict", action="store_true")

    qa_parser = sub.add_parser("qa")
    qa_parser.add_argument("source", type=Path)
    qa_parser.add_argument("target", type=Path)
    qa_parser.add_argument("--profile", choices=sorted(QA_PROFILES), required=True)
    qa_parser.add_argument("--max-chars-per-line", type=int)
    qa_parser.add_argument("--max-cps", type=float)
    qa_parser.add_argument("--max-lines", type=int)
    qa_parser.add_argument("--allowed-latin", action="append", default=[])
    qa_parser.add_argument("--forbid-text", action="append", default=[])
    qa_parser.add_argument("--glossary", type=Path)
    qa_parser.add_argument("--scan-regex", action="append", default=[])
    qa_parser.add_argument("--waivers", type=Path)
    qa_parser.add_argument("--report", type=Path)
    qa_parser.add_argument("--strict", action="store_true")

    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("source", type=Path)
    validate_parser.add_argument("target", type=Path)
    validate_scan_group = validate_parser.add_mutually_exclusive_group()
    validate_scan_group.add_argument(
        "--scan-untranslated-english-sdh",
        "--scan-sdh",
        dest="scan_sdh",
        action="store_true",
        help="scan a non-English translated target for leftover English SDH labels",
    )
    validate_scan_group.add_argument("--no-scan", action="store_true")
    validate_parser.add_argument("--require-player-format", action="store_true")

    merge_parser = sub.add_parser("merge")
    merge_parser.add_argument("in_dir", type=Path)
    merge_parser.add_argument("output", type=Path)

    deliver_parser = sub.add_parser("deliver-job")
    deliver_parser.add_argument("job", type=Path)
    deliver_parser.add_argument("destination", type=Path)
    deliver_parser.add_argument("--overwrite", action="store_true")

    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            return inspect(args.path)
        if args.command == "split":
            return split(args.path, args.out_dir, args.size, args.suffix)
        if args.command == "init-job":
            return init_job(
                args.source,
                args.work_dir,
                args.source_tag,
                args.target,
                args.stem,
                args.output_dir,
            )
        if args.command == "assemble-job":
            return assemble_job(args.job)
        if args.command == "split-workbook":
            return split_workbook(args.job, args.out_dir, args.size)
        if args.command == "merge-workbook":
            return merge_workbook(args.job, args.in_dir)
        if args.command == "compare-sources":
            return compare_sources(args.source, args.reference, args.output)
        if args.command == "cross-reference":
            return cross_reference(
                args.source,
                args.reference,
                args.output,
                args.compatibility_report,
                args.allow_unsafe,
            )
        if args.command == "review":
            return review(
                args.source,
                args.candidate,
                args.output,
                args.cross_reference,
            )
        if args.command == "lint":
            return lint(
                args.path,
                args.max_chars_per_line,
                args.max_cps,
                args.scan_regex,
                args.strict,
            )
        if args.command == "qa":
            return qa(
                args.source,
                args.target,
                args.profile,
                args.max_chars_per_line,
                args.max_cps,
                args.max_lines,
                args.allowed_latin,
                args.forbid_text,
                args.glossary,
                args.scan_regex,
                args.waivers,
                args.report,
                args.strict,
            )
        if args.command == "validate":
            return validate(
                args.source,
                args.target,
                scan=args.scan_sdh and not args.no_scan,
                require_player_format=args.require_player_format,
            )
        if args.command == "merge":
            return merge(args.in_dir, args.output)
        if args.command == "deliver-job":
            return deliver_job(args.job, args.destination, args.overwrite)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
