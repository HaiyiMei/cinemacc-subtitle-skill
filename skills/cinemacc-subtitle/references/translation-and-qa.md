# Translation and QA

Use this reference after an approved source-language SRT exists and the user requests one or more target-language tracks.

## Initialize a portable job

Start from the approved source, not the unreviewed original:

```bash
python3 "$TOOL" init-job approved-source.srt work/subtitle-job --source-tag en
```

Repeat `--target <tag>` to override the default `zh-CN` and `zh-TW` targets. Use `--stem` for an explicit naming contract. Keep `--output-dir` job-relative; it selects the staging subdirectory, while `deliver-job` selects the external destination.

`init-job` creates:

- `manifest.json`: source hash, language tags, output names, and relative artifact paths;
- `source/source.srt`: immutable approved-source snapshot;
- `workbook.tsv`: one row per cue;
- `glossary.tsv`: canonical renderings by language;
- `uncertainties.jsonl`: readings that need later audio or human review;
- `qa-waivers.jsonl`: reviewed QA outliers;
- `deliverables/`: assembled SRTs.

Workbook columns are `number`, `timestamp`, `source`, `refined`, one column per target language, `confidence`, and `notes`. Embedded backslashes, tabs, and newlines use `\\`, `\t`, and `\n`. Do not reorder rows or edit `number`, `timestamp`, or `source`.

Use `high`, `medium`, `low`, or `unreviewed` confidence. Keep uncertainty details outside viewing text. Use glossary columns `source`, the source tag, target tags, and `notes`.

## Translate from the approved source

- Preserve cue identity, timestamp, fragments, ambiguity, pauses, interruptions, and tag sequence.
- Use glossary renderings consistently for names, titles, places, objects, and recurring phrases.
- Write compact, natural theatrical subtitles rather than copying source syntax.
- Translate SDH descriptions and speaker labels using target conventions.
- Translate only supported visible meaning for foreign or inaudible captions.

For `zh-CN`, use natural Mainland Simplified Chinese. For `zh-TW`, use natural Taiwan Traditional Chinese and review vocabulary, names, grammar, punctuation, and false phrase matches cue by cue. A script converter may create a temporary scaffold but cannot produce the shipped `zh-TW` track by itself.

## Divide long work safely

Split long workbooks into disjoint ranges:

```bash
python3 "$TOOL" split-workbook work/subtitle-job work/subtitle-chunks --size 150
```

Give every range the same context pack and glossary. Adjacent cues are read-only context. Never let workers edit overlapping rows. The main agent owns glossary changes, cross-range consistency, uncertainty resolution, and final QA.

Merge completed ranges deterministically:

```bash
python3 "$TOOL" merge-workbook work/subtitle-job work/subtitle-chunks
```

## Assemble and validate

Assemble only after every required body is nonblank:

```bash
python3 "$TOOL" assemble-job work/subtitle-job
```

Validate each translation against the approved source. Run profile QA with the job glossary and a JSON report:

```bash
python3 "$TOOL" qa approved-source.srt movie.zh-CN.srt \
  --profile zh-CN --glossary work/subtitle-job/glossary.tsv \
  --waivers work/subtitle-job/qa-waivers.jsonl --strict --report qa-zh-CN.json

python3 "$TOOL" qa approved-source.srt movie.zh-TW.srt \
  --profile zh-TW --glossary work/subtitle-job/glossary.tsv \
  --waivers work/subtitle-job/qa-waivers.jsonl --strict --report qa-zh-TW.json
```

Default review thresholds are:

| Profile | Characters per line | Characters per second | Lines per cue |
| --- | ---: | ---: | ---: |
| `en` | 48 | 20 | 2 |
| `zh-CN` | 22 | 13 | 2 |
| `zh-TW` | 22 | 13 | 2 |

CPS counts visible Unicode code points excluding whitespace. A short timing window does not authorize retiming or content deletion. Pass project-specific Latin tokens with repeated `--allowed-latin`.

Fix every structural error. Resolve every warning, including `ellipsis_run`, or record a narrow waiver by profile, cue, and warning kind. Structural errors are never waivable. Review the beginning, middle, end, chunk boundaries, named-entity scenes, contaminated cues, and each uncertainty.

The separate `validate` command is structural by default. Use `--scan-untranslated-english-sdh` only for a non-English translated target.
