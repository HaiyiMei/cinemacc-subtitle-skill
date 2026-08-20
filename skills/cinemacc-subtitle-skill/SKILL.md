---
name: cinemacc-subtitle-skill
description: Research, repair, translate, QA, and deliver movie or TV SRT subtitles while preserving cue identity and timing. Use for poor source tracks, OCR/STT cleanup, context-aware translation, independent zh-CN/zh-TW localization, source comparison, SDH, glossaries, long-form chunking, or exact UTF-8 BOM/CRLF delivery.
license: MIT
compatibility: Requires Python 3.10+ (standard library only), an agent with local file read/write and shell access, and web access for title research unless the user opts out.
metadata:
  author: CinemaCC
  version: "0.2.0"
---

# CinemaCC Subtitle Skill

Produce a clean source-language track before translating it. Keep semantic decisions model-driven and structural operations deterministic.

Resolve `scripts/srt_tools.py` from this skill directory and reuse that absolute path as `TOOL`. Read [references/job-format-and-profiles.md](references/job-format-and-profiles.md) when creating a job, translating Chinese, handling contaminated cues, recording QA waivers, or delivering files. Read [references/release-provenance-and-trust.md](references/release-provenance-and-trust.md) when comparing candidate releases, interpreting release names, assessing uploaders or credits, or deciding whether a subtitle is official, transcribed, OCR-derived, or machine-translated.

## Establish the contract

1. Record the input path, source language, requested output directory, and naming convention.
2. Default Chinese work to both `zh-CN` and `zh-TW`. Treat them as independently reviewed Mainland and Taiwan localizations, not mechanical script variants.
3. Default to text repair only. Preserve every cue number, timestamp, and formatting-tag sequence. Require explicit authorization and matched audiovisual evidence for retiming, cue merges/splits, or positioning changes.
4. Preserve original inputs. Write generated work into a portable job directory and deliver only named outputs.
5. Do not use external machine-translation services unless the user explicitly requests one.

Initialize a resumable job:

```bash
python3 "$TOOL" init-job input.srt work/subtitle-job --source-tag en
```

This snapshots the source, records its hash, and creates a workbook with default `zh-CN` and `zh-TW` columns. Repeat `--target <tag>` to override the default targets. Use `--stem` when the user's naming contract requires it. Keep `--output-dir` job-relative; it changes only the staging subdirectory, while `deliver-job` selects the external destination.

## Inspect and diagnose

Run:

```bash
python3 "$TOOL" inspect input.srt
```

Confirm encoding, newline style, cue count and sequence, duration, overlaps, gaps, blank bodies, tags, speaker labels, and SDH style. Sample the beginning, middle, and end. Scan for uploader credits, betting ads, URLs, repeated interstitials, OCR/STT artifacts, improbable words, inconsistent names, and suspicious line breaks.

Classify each problem as structural, textual, coverage, or timing. Do not claim that text refinement fixes missing dialogue or bad timing.

## Research the title

Browse current title-specific evidence before editing, including spoilers when they resolve dialogue. Skip external title research only for an explicitly synthetic fixture, a private/non-released recording with no public title, or an explicit no-browse request; state that limitation. Prefer:

1. official studio pages, credits, press notes, trailers, and interviews;
2. reliable current reviews and character reporting;
3. authoritative cultural, historical, scientific, or geographic references;
4. independent source-language transcripts as wording evidence;
5. fan discussions only as labeled leads.

Build a compact context pack with scene order, character identities and relationships, places, factions, invented terms, official territory-specific titles, canonical renderings for every target, source links, and clearly separated inference. Prefer adaptation-specific evidence over general lore.

## Classify additional subtitle sources

Treat every release-name source label as an unverified claim and classify its provenance using the release-provenance reference. Compare every candidate before using it:

```bash
python3 "$TOOL" compare-sources input.srt independent.srt \
  --output work/subtitle-job/compatibility.json
```

Treat `same_source_family` as a mirror or derivative, not independent evidence. A safe timing classification does not prove independent wording; inspect language, provenance, segmentation, and translation lineage separately. Use automatic time alignment only for `same_timing_skeleton` or `likely_release_compatible`:

```bash
python3 "$TOOL" cross-reference input.srt independent.srt \
  work/subtitle-job/cross-reference.jsonl \
  --compatibility-report work/subtitle-job/compatibility.json
```

For `different_timing_or_edit` or `insufficient_evidence`, locate lines manually and never transplant timestamps. Do not bypass the compatibility guard merely to obtain more apparent evidence.

## Refine the source track

Work cue by cue with neighboring context:

- repair supported spelling, grammar, punctuation, casing, names, OCR/STT errors, and line layout;
- preserve profanity, hesitation, repetition, fragments, ambiguity, interruptions, speaker distinctions, SDH meaning, and formatting tags;
- keep every cue's meaning inside that cue;
- never invent inaudible dialogue or restore overwritten dialogue from a translated derivative alone;
- record low-confidence readings in `uncertainties.jsonl`, not in viewing text.

Apply the non-film cue policy in the job-format reference. In particular, remove clear uploader or betting promotion while retaining the timing skeleton. Use an official localized title in that cue only when supported by the image or explicitly requested by the user, and document editorial substitutions.

Do not start translation until the refined source passes structural checks and a named-entity consistency pass. Generate a changed-cue audit with correctly typed evidence:

```bash
python3 "$TOOL" review source.srt refined.en.srt review.jsonl \
  --cross-reference cross-reference.jsonl
```

## Divide long work safely

For long tracks, split the portable workbook into disjoint ranges:

```bash
python3 "$TOOL" split-workbook work/subtitle-job work/subtitle-chunks --size 150
```

Give every chunk worker the same context pack and glossary. Include adjacent cues only as read-only context. Never let concurrent workers edit the same workbook. Require each worker to preserve the row schema, fill only its assigned cues, and record uncertainty with evidence and confidence.

After all ranges return, merge them deterministically:

```bash
python3 "$TOOL" merge-workbook work/subtitle-job work/subtitle-chunks
```

The main agent owns the glossary, cross-range consistency, uncertainty log, and final quality gate.

## Translate from the refined track

Translate each target directly from the refined source:

- preserve cue identity, timestamp, fragments, ambiguity, pauses, interruptions, and tag sequence;
- use glossary renderings consistently for names, titles, places, objects, and recurring phrases;
- write compact, natural theatrical subtitles rather than literal source syntax;
- translate SDH descriptions and speaker labels using target conventions;
- translate only supported visible meaning for foreign or inaudible captions.

For `zh-CN`, use natural Mainland Simplified Chinese. For `zh-TW`, use natural Taiwan Traditional Chinese and review vocabulary, names, grammar, punctuation, and false phrase matches cue by cue. A deterministic converter may create a temporary scaffold but must never be the shipped `zh-TW` track.

For other target languages, add explicit workbook target columns at initialization and define suitable QA thresholds.

## Assemble, review, and QA

Assemble only after every required workbook body is nonblank:

```bash
python3 "$TOOL" assemble-job work/subtitle-job
```

Validate the refined track against the source snapshot and each translation against the refined track. Run profile QA with the job glossary and a JSON report:

```bash
python3 "$TOOL" qa work/subtitle-job/source/source.srt refined.en.srt \
  --profile en --glossary work/subtitle-job/glossary.tsv \
  --waivers work/subtitle-job/qa-waivers.jsonl --strict --report qa-en.json

python3 "$TOOL" qa refined.en.srt movie.zh-CN.srt \
  --profile zh-CN --glossary work/subtitle-job/glossary.tsv \
  --waivers work/subtitle-job/qa-waivers.jsonl --strict --report qa-zh-CN.json

python3 "$TOOL" qa refined.en.srt movie.zh-TW.srt \
  --profile zh-TW --glossary work/subtitle-job/glossary.tsv \
  --waivers work/subtitle-job/qa-waivers.jsonl --strict --report qa-zh-TW.json
```

Pass project-specific Latin tokens with repeated `--allowed-latin`. Fix every structural error. Resolve every warning or record a narrow waiver with a reason; never waive an entire category globally. Review the beginning, middle, end, chunk boundaries, named-entity scenes, contaminated cues, and every uncertainty.

`validate` is structural by default. Use `--scan-untranslated-english-sdh` only on a non-English translated target; never enable that scan for the refined English track.

## Deliver

Re-resolve the user's destination immediately before writing. Confirm that existing same-name files are generated outputs rather than sources or user-edited artifacts. Deliver atomically and write a hash receipt:

```bash
python3 "$TOOL" deliver-job work/subtitle-job /current/output/directory
```

Use `--overwrite` only after confirming the exact existing targets. Validate the copied files again when delivery crosses a filesystem, cloud-sync boundary, or sandbox boundary. Report coverage and timing limits honestly.

## Deterministic boundary

Use `srt_tools.py` for snapshots, hashes, source comparison, workbook splitting/merging, assembly, structural validation, QA reports, atomic delivery, and receipts. Keep research, evidence evaluation, dialogue repair, translation, and waiver judgment in the model or human review. Never add a script that calls a translation service or silently rewrites subtitle meaning.
