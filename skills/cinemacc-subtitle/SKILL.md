---
name: cinemacc-subtitle
description: Find or use a movie or TV SRT, verify and repair it, translate requested languages, run QA, and deliver standalone files or CinemaCC import bundles without changing program cue timing.
license: MIT
metadata:
  author: CinemaCC
  version: "0.5.0"
---

# CinemaCC Subtitle Skill

Produce an eligible source track, improve it only as authorized, translate requested targets, and deliver validated SRT files. Keep semantic decisions model-driven and structural operations deterministic.

Require Python 3.10 or newer, local file read/write and shell access, and web access when source acquisition or title research is needed. Resolve `scripts/srt_tools.py` from this skill directory and reuse that absolute path as `TOOL`. The tool uses only the Python standard library.

## Choose the route

Select the shortest route that satisfies the request:

| Request | Stages |
| --- | --- |
| Title only or no eligible source | Acquire, review and repair, translate and QA, deliver |
| Supplied source with no narrower instruction | Review and repair, translate and QA, deliver |
| Find or download only | Acquire, verify, deliver the unchanged source |
| Refine only | Review and repair, validate, deliver the refined source |
| Translate only | Verify the supplied source, translate and QA, deliver without rewriting the source |
| Package for CinemaCC | Validate the supplied pair, then package and deliver |

Default Chinese translation to independently reviewed `zh-CN` and `zh-TW` outputs unless the user requests one target. Do not run omitted semantic stages. Read only the references required by the selected route, and read each selected reference before starting that stage.

## Shared contract

- Record the title and year, claimed source language, requested targets, output directory, and naming convention. Record the input path when one exists.
- Preserve every original input and downloaded file. Write generated work to a separate job or output directory.
- Verify observed language and coverage before presenting a file as the requested source or a complete track.
- Preserve every program-content cue number, timestamp, and formatting-tag sequence. Retiming, cue merges or splits, and positioning changes require explicit authorization and matched audiovisual evidence.
- Do not substitute an unexpected language or partial track without explicit approval and clear disclosure.
- Do not use an external machine-translation service unless the user explicitly requests one.
- Do not bypass authentication, CAPTCHAs, paywalls, provider limits, disabled files, or takedowns. Do not upload subtitles to a new public host without explicit authorization.

## Stage 1: acquire a source

Use this stage only when no eligible source was supplied or the user asks for source comparison. Read [references/source-acquisition.md](references/source-acquisition.md).

The stage ends with the untouched downloaded file plus a record of its provider page, release claim, observed language, coverage, and access date. A download-only request stops after this output is verified.

## Stage 2: review and repair

Use this stage for every full or refine-only workflow. A translate-only request runs only the eligibility and structural checks from this stage. Read [references/source-review-and-repair.md](references/source-review-and-repair.md).

Read [references/release-provenance-and-trust.md](references/release-provenance-and-trust.md) only when comparing releases, assessing source or uploader claims, or deciding whether text is official, transcribed, OCR-derived, or machine-translated.

A repair route ends with a structurally validated source-language SRT, a changed-cue audit, and documented uncertainties. A translate-only route ends with an eligibility record for the unchanged supplied source. Do not start translation from a source that failed the applicable checks.

## Stage 3: translate and QA

Use this stage only when the user requests a target-language track. Read [references/translation-and-qa.md](references/translation-and-qa.md).

Translate each target directly from the approved source. The stage ends with standalone SRT files that passed structural validation and target-language QA, plus narrow waivers for any reviewed warning that cannot be fixed without changing timing or meaning.

## Stage 4: deliver

Read [references/cinemacc-delivery.md](references/cinemacc-delivery.md) when copying generated outputs, packaging a CinemaCC pair, or creating an import link.

Keep standalone SRT files as the primary deliverables. For CinemaCC, create one two-track ZIP per target language. Create a one-tap import link only after verifying that the ZIP has an anonymous public HTTPS download URL.

## Completion gates

- Report source, release match, observed language, coverage, timing limits, QA result, and unresolved uncertainty.
- Never claim that text repair fixes missing dialogue, a different cut, or timing drift.
- Never call a local path, share page, or account-scoped artifact a direct import link.
- Revalidate files after copying across a filesystem, cloud-sync boundary, or sandbox boundary.

## Deterministic boundary

Use `srt_tools.py` for cue pruning and renumbering, snapshots, hashes, source comparison, workbook splitting and merging, assembly, structural validation, QA reports, atomic delivery, CinemaCC bundles, import-link formatting, and receipts. Keep source discovery, access decisions, non-program classification, research, evidence evaluation, dialogue repair, translation, and waiver judgment in the model or human review. Never add a script that calls a translation service or silently rewrites subtitle meaning.
