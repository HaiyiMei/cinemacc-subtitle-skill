# Job format and language profiles

## Default outputs

Use `zh-CN` for natural Mainland Simplified Chinese and `zh-TW` for natural Taiwan Traditional Chinese. Unless the user requests other targets, initialize both:

- `<stem>.refined.<source-tag>.srt`
- `<stem>.zh-CN.srt`
- `<stem>.zh-TW.srt`
- `<stem>.context.md` when research, glossary, or unresolved readings need an audit trail

Treat language tags as output contracts, not script-conversion labels. Do not ship `zh-TW` produced only by converting `zh-CN`.

## Portable job

`init-job` creates:

- `manifest.json`: source hash, language tags, output names, and relative artifact paths;
- `source/source.srt`: immutable snapshot used for every structural comparison;
- `workbook.tsv`: one row per cue;
- `glossary.tsv`: canonical renderings by language;
- `uncertainties.jsonl`: readings that need later audio or human review;
- `qa-waivers.jsonl`: reviewed QA outliers that cannot be fixed without retiming or omission;
- `deliverables/`: assembled SRTs.

The workbook columns are `number`, `timestamp`, `source`, `refined`, one column per target language, `confidence`, and `notes`. Embedded backslashes, tabs, and newlines use `\\`, `\t`, and `\n`. Do not reorder rows or edit `number`, `timestamp`, or `source`.

Use `high`, `medium`, `low`, or `unreviewed` in `confidence`. Keep uncertainty detail out of viewing subtitles. Write one JSON object per unresolved reading:

```json
{"number":429,"language":"en","reading":"How old are you?","confidence":"low","reason":"Two unofficial witnesses disagree; verify against matched audio."}
```

Use glossary columns `source`, the source tag, target tags, and `notes`. The QA command treats renderings from another `zh-*` column as locale-leak candidates when they differ from the selected profile.

## Non-film cue policy

Keep the cue identity and choose text deliberately:

1. Preserve verified film dialogue, SDH, or on-screen text.
2. Remove clear uploader promotion, betting advertisements, URLs, and repeated source-family interstitials.
3. Replace a contaminated cue with a verified on-screen card when audiovisual or independent evidence supports that card.
4. When the user explicitly prefers a localized official film title in a contaminated cue, use the territory-appropriate title and record it as an editorial substitution.
5. Otherwise use a neutral ellipsis and document the coverage gap.

Never reconstruct overwritten dialogue from a translated derivative alone.

## QA profiles

Defaults are candidate-review thresholds rather than permission to retime:

| Profile | Characters per line | Characters per second | Lines per cue |
| --- | ---: | ---: | ---: |
| `en` | 48 | 20 | 2 |
| `zh-CN` | 22 | 13 | 2 |
| `zh-TW` | 22 | 13 | 2 |

CPS counts visible Unicode code points excluding whitespace. A warning caused by a short source window does not authorize timing changes or content deletion. Document accepted outliers.

The Chinese profiles allow common abbreviations such as `DNA`, `RNA`, `mRNA`, `MJ`, `App`, `GPS`, `MRI`, `FBI`, `NYPD`, and `MIT`. Pass project-specific tokens such as `V-MAX`, `Nomex`, or `Kevlar` with repeated `--allowed-latin` options.

Record an accepted warning narrowly by profile, cue, and kind:

```json
{"profile":"en","cue":25,"kind":"cps","reason":"The fixed source window is short; wording is already minimal and retiming is out of scope."}
```

Strict QA ignores only matching, documented waivers. Structural errors are never waivable.

The separate `validate` command performs structural checks by default. Its `--scan-untranslated-english-sdh` option is only for non-English translated tracks; valid English source/refined SDH such as `[MUSIC PLAYING]` must not be scanned as untranslated text.

## Delivery

Re-resolve the destination immediately before delivery. Keep `init-job --output-dir` relative to the job; it is a staging directory, never the external destination. Do not hardcode a mutable external source path in an assembler. Run strict QA first, then use `deliver-job` for atomic copies and a hash receipt. Pass `--overwrite` only after confirming every existing target is a previously generated output; never overwrite the original source subtitle.
