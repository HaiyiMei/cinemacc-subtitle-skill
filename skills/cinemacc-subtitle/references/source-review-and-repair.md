# Source review and repair

Use this reference to verify a supplied or downloaded source, remove confirmed non-program residue, research context, compare compatible evidence, and produce the approved source-language track.

## Inspect the source

Run:

```bash
python3 "$TOOL" inspect input.srt
```

Confirm encoding, newline style, cue count and sequence, duration, overlaps, gaps, blank bodies, tags, speaker labels, and SDH style. Sample the beginning, middle, and end. Scan for uploader credits, betting ads, URLs, repeated interstitials, OCR or STT artifacts, improbable words, inconsistent names, suspicious line breaks, and short blank or punctuation-only runs.

## Pass the source-eligibility gate

Record the claimed language, observed language, and coverage as `full`, `partial`, or `unverified`. Verify language from representative cues rather than the filename or provider label. Compare the final cue with a reliable runtime when available.

An unexpected-language or partial track can be evidence, but it is not an eligible base for a deliverable advertised as a complete track in another language. Find a compatible track in the requested language, or obtain explicit permission to translate the actual language and disclose the coverage limit.

Classify problems as structural, textual, coverage, or timing. Text repair does not fix missing dialogue or a release mismatch.

## Prune confirmed non-program residue

Remove a contiguous run only after verifying that it contains no dialogue, SDH, or story-relevant on-screen text. Blank or short bodies alone are not proof. If uncertain, keep the cues and record the uncertainty.

Select by 1-based block position so malformed or duplicate cue numbers cannot make the request ambiguous:

```bash
python3 "$TOOL" prune-cues input.srt cleaned.srt \
  --drop-blocks 2-21 \
  --reason "Reviewed fragments of an uploader credit animation before program content." \
  --audit work/prune-audit.json
```

The command preserves the original, removes only selected blocks, keeps every retained body and timestamp, renumbers the viewing track, and writes a hash-backed map. Use one neutral ellipsis only for an isolated contaminated cue that may occupy genuine program time. Never fill a confirmed non-program run with placeholders.

## Research and compare evidence

Browse current title-specific sources when context affects dialogue, names, places, invented terms, or established target-language renderings. Prefer official credits, press notes, trailers, and interviews, followed by reliable reporting and authoritative subject references. Treat fan discussion as a lead, not proof.

When another subtitle may improve the reading, compare it before reuse:

```bash
python3 "$TOOL" compare-sources cleaned.srt independent.srt \
  --output work/compatibility.json
```

Treat `same_source_family` as a mirror or derivative, not independent evidence. Use automatic time alignment only for `same_timing_skeleton` or `likely_release_compatible`:

```bash
python3 "$TOOL" cross-reference cleaned.srt independent.srt \
  work/cross-reference.jsonl \
  --compatibility-report work/compatibility.json
```

For `different_timing_or_edit` or `insufficient_evidence`, locate lines manually and never transplant timestamps.

## Repair the source

Work cue by cue with neighboring context. Repair supported spelling, grammar, punctuation, casing, names, OCR or STT errors, and line layout. Preserve profanity, hesitation, repetition, fragments, ambiguity, interruptions, speaker distinctions, SDH meaning, and formatting tags. Keep each cue's meaning inside that cue. Never invent inaudible dialogue or reconstruct overwritten dialogue from a translated derivative alone.

Record low-confidence readings outside the viewing text. After producing `refined.<source-tag>.srt`, audit and validate it against the cleaned source:

```bash
python3 "$TOOL" review cleaned.srt refined.en.srt work/review.jsonl \
  --cross-reference work/cross-reference.jsonl

python3 "$TOOL" validate cleaned.srt refined.en.srt \
  --require-player-format
```

Omit `--cross-reference` when no compatible reference exists. Do not enable the untranslated-English SDH scan for an English refined track.

For a refine-only request, deliver the validated refined SRT and audit. For a translate-only request, do not rewrite the source; use the eligible supplied track as the approved source for the next stage.
