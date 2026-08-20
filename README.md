# CinemaCC Subtitle Workflow

[![skills.sh](https://skills.sh/b/HaiyiMei/cinemacc-subtitle-workflow)](https://skills.sh/HaiyiMei/cinemacc-subtitle-workflow)

An open, auditable Agent Skill for researching, repairing, translating, and validating movie or TV SRT subtitles without silently changing cue timing.

The workflow keeps semantic decisions with the agent or human reviewer and delegates snapshots, hashes, source comparison, chunking, assembly, structural QA, and atomic delivery to a deterministic Python tool.

## Install

With the open Skills CLI:

```bash
npx skills add HaiyiMei/cinemacc-subtitle-workflow
```

In Codex, you can also ask the built-in installer:

```text
$skill-installer install https://github.com/HaiyiMei/cinemacc-subtitle-workflow/tree/main/skills/cinemacc-subtitle-workflow
```

The repository also includes a minimal OpenAI skill-only plugin manifest for current ChatGPT and Codex distribution tooling.

## Use

```text
Use $cinemacc-subtitle-workflow to research and refine this SRT, then create validated zh-CN and zh-TW subtitles without changing its timing.
```

By default, the workflow produces a refined source track plus independently localized Mainland Chinese (`zh-CN`) and Taiwan Chinese (`zh-TW`) tracks. Other target languages can be requested explicitly.

## What it handles

- source-track diagnosis and OCR/STT repair before translation;
- title, character, terminology, and cultural context research;
- subtitle-source provenance and timing-family comparison;
- resumable workbooks, glossaries, uncertainties, and narrow QA waivers;
- deterministic cue, timestamp, formatting-tag, encoding, and newline checks;
- safe chunk splitting and merging for long subtitles;
- atomic delivery with hashes and receipts.

## Repository layout

```text
.
├── .codex-plugin/plugin.json
└── skills/cinemacc-subtitle-workflow/
    ├── SKILL.md
    ├── agents/openai.yaml
    ├── references/
    └── scripts/
```

The skill follows the [Agent Skills specification](https://agentskills.io/specification). The plugin manifest is an additive OpenAI distribution wrapper; the skill remains installable by any compatible agent that understands `SKILL.md`.

## Requirements

- Python 3.10 or newer; the deterministic tooling uses only the standard library.
- A skills-compatible agent with file access.
- Web access for title-specific research unless the input is a synthetic fixture, private unreleased recording, or the user explicitly requests no browsing.

## Verify

```bash
python3 skills/cinemacc-subtitle-workflow/scripts/test_srt_tools.py
```

## Privacy, cost, and rights

CinemaCC does not operate a translation service for this skill. Subtitle text and research queries may be sent to the agent or model provider you choose, and that provider's pricing and privacy terms apply.

The repository does not include commercial movie or TV subtitles. You are responsible for having the rights needed to translate or distribute any source and output files.

## CinemaCC

[CinemaCC](https://cinemacc.net) is a subtitle companion for films on any screen. It can import one or two SRT tracks for synchronized, theater-dark playback.

## License

The code and documentation are available under the [MIT License](LICENSE). The license does not grant rights to third-party subtitle content or CinemaCC trademarks.
