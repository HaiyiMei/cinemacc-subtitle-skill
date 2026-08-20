from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("srt_tools.py")
SPEC = importlib.util.spec_from_file_location("srt_tools", MODULE_PATH)
assert SPEC and SPEC.loader
srt_tools = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(srt_tools)


class SrtToolsTests(unittest.TestCase):
    def test_write_srt_emits_bom_and_pure_crlf(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "target.srt"
            srt_tools.write_srt(
                path,
                [(1, "00:00:00,000 --> 00:00:01,000", ["First line", "Second line"])],
            )

            self.assertEqual(srt_tools.file_format(path), (True, 4, 0, 0))

    def test_validate_player_format_rejects_mixed_newlines(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.srt"
            target = root / "target.srt"
            cue = [(1, "00:00:00,000 --> 00:00:01,000", ["First line", "Second line"])]
            srt_tools.write_srt(source, cue)
            srt_tools.write_srt(target, cue)
            target.write_bytes(
                target.read_bytes().replace(b"First line\r\n", b"First line\n")
            )

            self.assertEqual(
                srt_tools.validate(
                    source, target, scan=False, require_player_format=True
                ),
                1,
            )

    def test_split_merge_and_validate_preserve_skeleton(self) -> None:
        cues = [
            (1, "00:00:00,000 --> 00:00:01,000", ["<i>Hello</i>"]),
            (2, "00:00:01,500 --> 00:00:02,500", ["World"]),
            (3, "00:00:03,000 --> 00:00:04,000", ["Again"]),
        ]
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.srt"
            chunks = root / "chunks"
            merged = root / "merged.srt"
            srt_tools.write_srt(source, cues)

            self.assertEqual(srt_tools.split(source, chunks, 2, "refined"), 0)
            self.assertEqual(
                [path.name for path in sorted(chunks.glob("*.srt"))],
                ["chunk-0001-0002.refined.srt", "chunk-0003-0003.refined.srt"],
            )
            self.assertEqual(srt_tools.merge(chunks, merged), 0)
            self.assertEqual(srt_tools.validate(source, merged, scan=False), 0)

    def test_validate_rejects_preserved_tag_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.srt"
            target = root / "target.srt"
            srt_tools.write_srt(
                source,
                [(1, "00:00:00,000 --> 00:00:01,000", ["<i>Hello</i>"])],
            )
            srt_tools.write_srt(
                target,
                [(1, "00:00:00,000 --> 00:00:01,000", ["Hello"])],
            )

            self.assertEqual(srt_tools.validate(source, target, scan=False), 1)

    def test_validate_rejects_added_ass_positioning_tag(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.srt"
            target = root / "target.srt"
            timestamp = "00:00:00,000 --> 00:00:01,000"
            srt_tools.write_srt(source, [(1, timestamp, ["Good luck!"])])
            srt_tools.write_srt(target, [(1, timestamp, [r"{\an8}Bonne chance !"])])

            self.assertEqual(srt_tools.validate(source, target, scan=False), 1)

    def test_cross_reference_aligns_by_time_overlap_without_rewriting(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.srt"
            reference = root / "reference.srt"
            output = root / "aligned.jsonl"
            srt_tools.write_srt(
                source,
                [
                    (1, "00:00:00,000 --> 00:00:01,000", ["Hullo"]),
                    (2, "00:00:02,000 --> 00:00:03,000", ["World"]),
                ],
            )
            srt_tools.write_srt(
                reference,
                [
                    (10, "00:00:00,200 --> 00:00:01,200", ["Hello"]),
                    (11, "00:00:02,200 --> 00:00:02,800", ["World!"]),
                ],
            )

            self.assertEqual(srt_tools.cross_reference(source, reference, output), 0)
            records = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertEqual(records[0]["source_lines"], ["Hullo"])
            self.assertEqual(records[0]["references"][0]["lines"], ["Hello"])
            self.assertEqual(records[1]["references"][0]["number"], 11)

    def test_lint_reports_candidates_and_only_fails_in_strict_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "target.srt"
            srt_tools.write_srt(
                path,
                [(1, "00:00:00,000 --> 00:00:01,000", ["A very long English line"])],
            )

            self.assertEqual(srt_tools.lint(path, 10, 5, [r"English"], strict=False), 0)
            self.assertEqual(srt_tools.lint(path, 10, 5, [r"English"], strict=True), 1)

    def test_lint_excludes_ass_positioning_tags_from_visible_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "target.srt"
            srt_tools.write_srt(
                path,
                [(1, "00:00:00,000 --> 00:00:01,000", [r"{\an8}Visible"])],
            )

            self.assertEqual(srt_tools.lint(path, 7, 7, [], strict=True), 0)

    def test_review_emits_only_changed_cues_with_reference_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.srt"
            candidate = root / "candidate.srt"
            evidence = root / "evidence.jsonl"
            output = root / "review.jsonl"
            timestamp = "00:00:00,000 --> 00:00:01,000"
            srt_tools.write_srt(
                source, [(1, timestamp, ["Hullo"]), (2, timestamp, ["Same"])]
            )
            srt_tools.write_srt(
                candidate, [(1, timestamp, ["Hello"]), (2, timestamp, ["Same"])]
            )
            evidence.write_text(
                json.dumps(
                    {
                        "source_number": 1,
                        "references": [{"number": 9, "lines": ["Hello"]}],
                    }
                )
                + "\n"
            )

            self.assertEqual(srt_tools.review(source, candidate, output, evidence), 0)
            records = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["candidate_lines"], ["Hello"])
            self.assertEqual(records[0]["references"][0]["number"], 9)

    def test_review_rejects_an_srt_as_cross_reference_jsonl(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.srt"
            candidate = root / "candidate.srt"
            evidence = root / "not-evidence.srt"
            output = root / "review.jsonl"
            timestamp = "00:00:00,000 --> 00:00:01,000"
            srt_tools.write_srt(source, [(1, timestamp, ["Hullo"])])
            srt_tools.write_srt(candidate, [(1, timestamp, ["Hello"])])
            srt_tools.write_srt(evidence, [(1, timestamp, ["Reference"])])

            with self.assertRaisesRegex(ValueError, "cross-reference JSONL"):
                srt_tools.review(source, candidate, output, evidence)

    def test_init_job_defaults_to_zh_cn_and_zh_tw_and_delivers(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "Movie-en.srt"
            job = root / "job"
            destination = root / "delivery"
            timestamp = "00:00:00,000 --> 00:00:01,000"
            srt_tools.write_srt(source, [(1, timestamp, ["Hello"])])

            with self.assertRaisesRegex(ValueError, "job-relative staging"):
                srt_tools.init_job(
                    source,
                    root / "invalid-job",
                    source_tag="en",
                    targets=None,
                    stem=None,
                    output_dir=str(root / "external-output"),
                )
            self.assertEqual(
                srt_tools.init_job(
                    source,
                    job,
                    source_tag="en",
                    targets=None,
                    stem=None,
                    output_dir="deliverables",
                ),
                0,
            )
            manifest = json.loads((job / "manifest.json").read_text())
            self.assertEqual(manifest["targets"], ["zh-CN", "zh-TW"])
            self.assertEqual(
                manifest["outputs"],
                {
                    "en": "Movie.refined.en.srt",
                    "zh-CN": "Movie.zh-CN.srt",
                    "zh-TW": "Movie.zh-TW.srt",
                },
            )

            workbook = job / "workbook.tsv"
            lines = workbook.read_text().splitlines()
            columns = lines[0].split("\t")
            row = lines[1].split("\t")
            row[columns.index("refined")] = "Hello!"
            row[columns.index("zh-CN")] = "你好！"
            row[columns.index("zh-TW")] = "你好！"
            row[columns.index("confidence")] = "high"
            workbook.write_text(
                "\n".join([lines[0], "\t".join(row)]) + "\n",
                encoding="utf-8",
            )

            self.assertEqual(srt_tools.assemble_job(job), 0)
            self.assertEqual(
                srt_tools.parse_srt(job / "deliverables/Movie.zh-CN.srt")[0][2],
                ["你好！"],
            )
            self.assertEqual(
                srt_tools.deliver_job(job, destination, overwrite=False),
                0,
            )
            self.assertTrue((destination / "Movie.refined.en.srt").is_file())
            self.assertTrue((destination / "Movie.zh-CN.srt").is_file())
            self.assertTrue((destination / "Movie.zh-TW.srt").is_file())
            with self.assertRaisesRegex(ValueError, "already exists"):
                srt_tools.deliver_job(job, destination, overwrite=False)

    def test_split_and_merge_workbook_require_complete_disjoint_ranges(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "Movie-en.srt"
            job = root / "job"
            chunks = root / "chunks"
            cues = [
                (
                    number,
                    f"00:00:0{number},000 --> 00:00:0{number + 1},000",
                    [f"Line {number}"],
                )
                for number in range(1, 4)
            ]
            srt_tools.write_srt(source, cues)
            srt_tools.init_job(
                source,
                job,
                source_tag="en",
                targets=None,
                stem=None,
                output_dir="deliverables",
            )

            self.assertEqual(srt_tools.split_workbook(job, chunks, size=2), 0)
            chunk_paths = sorted(chunks.glob("*.tsv"))
            self.assertEqual(
                [path.name for path in chunk_paths],
                ["chunk-0001-0002.tsv", "chunk-0003-0003.tsv"],
            )
            for path in chunk_paths:
                rows = srt_tools.parse_workbook(path, ["zh-CN", "zh-TW"])
                for row in rows:
                    row["zh-CN"] = f"简体{row['number']}"
                    row["zh-TW"] = f"繁體{row['number']}"
                    row["confidence"] = "high"
                srt_tools.write_workbook(path, rows, ["zh-CN", "zh-TW"])
            self.assertEqual(srt_tools.merge_workbook(job, chunks), 0)
            merged = srt_tools.parse_workbook(
                job / "workbook.tsv",
                ["zh-CN", "zh-TW"],
            )
            self.assertEqual(
                [row["zh-CN"] for row in merged], ["简体1", "简体2", "简体3"]
            )

    def test_compare_sources_reports_stable_offset_and_guards_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.srt"
            reference = root / "reference.srt"
            report = root / "compatibility.json"
            output = root / "cross-reference.jsonl"
            source_cues = []
            reference_cues = []
            for number in range(1, 7):
                source_start = number * 2
                reference_start = source_start + 1
                source_cues.append(
                    (
                        number,
                        f"00:00:{source_start:02d},000 --> 00:00:{source_start + 1:02d},000",
                        [f"Distinct dialogue anchor number {number}"],
                    )
                )
                reference_cues.append(
                    (
                        number + 20,
                        f"00:00:{reference_start:02d},000 --> 00:00:{reference_start + 1:02d},000",
                        [
                            (
                                "An independently worded final line"
                                if number == 6
                                else f"Distinct dialogue anchor number {number}"
                            )
                        ],
                    )
                )
            srt_tools.write_srt(source, source_cues)
            srt_tools.write_srt(reference, reference_cues)

            self.assertEqual(
                srt_tools.compare_sources(source, reference, report),
                0,
            )
            compatibility = json.loads(report.read_text())
            self.assertEqual(
                compatibility["classification"],
                "likely_release_compatible",
            )
            self.assertEqual(
                compatibility["median_reference_minus_source_ms"],
                1_000,
            )
            self.assertEqual(
                srt_tools.cross_reference(
                    source,
                    reference,
                    output,
                    compatibility_report=report,
                ),
                0,
            )
            records = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertEqual(records[0]["references"][0]["number"], 21)

    def test_cross_reference_refuses_an_incompatible_report(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.srt"
            reference = root / "reference.srt"
            report = root / "compatibility.json"
            output = root / "cross-reference.jsonl"
            srt_tools.write_srt(
                source,
                [(1, "00:00:00,000 --> 00:00:01,000", ["Source only"])],
            )
            srt_tools.write_srt(
                reference,
                [(9, "00:01:00,000 --> 00:01:01,000", ["Different text"])],
            )
            srt_tools.compare_sources(source, reference, report)

            with self.assertRaisesRegex(ValueError, "cross-reference refused"):
                srt_tools.cross_reference(
                    source,
                    reference,
                    output,
                    compatibility_report=report,
                )

    def test_qa_uses_language_profile_and_glossary_variants(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.srt"
            target = root / "target.srt"
            glossary = root / "glossary.tsv"
            report = root / "qa.json"
            timestamp = "00:00:00,000 --> 00:00:01,000"
            srt_tools.write_srt(source, [(1, timestamp, ["Spider-Man"])])
            srt_tools.write_srt(
                target,
                [(1, timestamp, ["蜘蛛侠", "Spider-Man", "第三行"])],
            )
            glossary.write_text(
                "source\ten\tzh-CN\tzh-TW\tnotes\n"
                "Spider-Man\tSpider-Man\t蜘蛛侠\t蜘蛛人\thero\n",
                encoding="utf-8",
            )

            self.assertEqual(
                srt_tools.qa(
                    source,
                    target,
                    profile="zh-TW",
                    max_chars_per_line=None,
                    max_cps=None,
                    max_lines=None,
                    allowed_latin=[],
                    forbidden_text=[],
                    glossary=glossary,
                    scan_regexes=[],
                    waiver_path=None,
                    report_path=report,
                    strict=True,
                ),
                1,
            )
            kinds = {
                finding["kind"]
                for finding in json.loads(report.read_text())["warnings"]
            }
            self.assertTrue({"line_count", "latin", "forbidden_text"} <= kinds)
            waivers = root / "qa-waivers.jsonl"
            waivers.write_text(
                "\n".join(
                    json.dumps(
                        {
                            "profile": "zh-TW",
                            "cue": 1,
                            "kind": kind,
                            "reason": "Synthetic fixture intentionally exercises this warning.",
                        }
                    )
                    for kind in kinds
                )
                + "\n",
                encoding="utf-8",
            )
            self.assertEqual(
                srt_tools.qa(
                    source,
                    target,
                    profile="zh-TW",
                    max_chars_per_line=None,
                    max_cps=None,
                    max_lines=None,
                    allowed_latin=[],
                    forbidden_text=[],
                    glossary=glossary,
                    scan_regexes=[],
                    waiver_path=waivers,
                    report_path=None,
                    strict=True,
                ),
                0,
            )

    def test_validate_preserves_font_tags(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.srt"
            target = root / "target.srt"
            timestamp = "00:00:00,000 --> 00:00:01,000"
            text = '<font color="#ffff00">Hello</font>'
            srt_tools.write_srt(source, [(1, timestamp, [text])])
            srt_tools.write_srt(target, [(1, timestamp, [text])])

            self.assertEqual(
                srt_tools.validate(
                    source,
                    target,
                    scan=False,
                    require_player_format=True,
                ),
                0,
            )

    def test_validate_only_scans_sdh_when_explicitly_requested(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "source.srt"
            target = root / "target.srt"
            timestamp = "00:00:00,000 --> 00:00:01,000"
            cue = [(1, timestamp, ["[MUSIC PLAYING]"])]
            srt_tools.write_srt(source, cue)
            srt_tools.write_srt(target, cue)

            self.assertEqual(srt_tools.validate(source, target), 0)
            self.assertEqual(srt_tools.validate(source, target, scan=True), 1)


if __name__ == "__main__":
    unittest.main()
