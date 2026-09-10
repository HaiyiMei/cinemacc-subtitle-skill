# CinemaCC Subtitle Skill

[![skills.sh](https://skills.sh/b/HaiyiMei/cinemacc-subtitle-skill)](https://skills.sh/HaiyiMei/cinemacc-subtitle-skill)

An open-source Agent Skill for researching, repairing, translating and checking SRT subtitles. It prepares files for CinemaCC or another subtitle player while preserving cue timing unless a change is explicitly authorized.

## Why we built it

A subtitle translation can read well line by line and still be confusing across a whole film. While preparing Project Hail Mary subtitles, we found that Petrova line switched Chinese transliterations partway through the file. Astrophage also appeared under two different Chinese terms.

Context caused another kind of mistake in an Odyssey subtitle task: Hades referred to the underworld in the passage, but was translated as the god's name. Mentor was a character, but became the ordinary word for an adviser. Valid timestamps would not tell us any of that was wrong.

The Skill starts with research. The agent records character identities, relationships, places and recurring terms in a context file and glossary, then uses the same notes for every chunk. Locale choices belong there too: Mainland Chinese 蜘蛛侠 and Taiwan Chinese 蜘蛛人 are both Spider-Man, but character conversion alone will not choose the right name.

The agent handles source repair and translation decisions. Python scripts handle source snapshots, chunk assembly and checks for cue numbering, timestamps, tags and file structure. Uncertain readings remain visible for review. Passing those checks proves structural properties, not translation quality.

Read the [background and examples](https://cinemacc.net/guides/cinemacc-subtitle-skill), or install the Skill below.

## Install

The skill is a plain [Agent Skill](https://agentskills.io/specification), so any compatible agent can load
it. Pick the path that matches your client.

### Any agent, with the open skills CLI

```bash
npx skills add HaiyiMei/cinemacc-subtitle-skill
```

The CLI detects the agents you have installed. Add `-a claude-code` (repeatable) to target specific ones,
`-g` to install globally instead of into the current project.

### Claude Code

```text
/plugin marketplace add HaiyiMei/cinemacc-subtitle-skill
/plugin install cinemacc-subtitle@cinemacc
```

### ChatGPT and Codex

```text
$skill-installer install https://github.com/HaiyiMei/cinemacc-subtitle-skill/tree/main/skills/cinemacc-subtitle
```

### Other Agent Plugins clients

The repository root is an [Agent Plugins 1.0.0](https://agent-plugins.org/specification) package: a
`plugin.json` manifest plus a `skills/` directory. Clients that implement the standard - including VS Code,
Cursor, GitHub Copilot, and Kiro - can install it directly from the repository. Follow your client's plugin
installation instructions and point it at
`https://github.com/HaiyiMei/cinemacc-subtitle-skill`.

### Manually

Copy `skills/cinemacc-subtitle/` into your agent's skills directory, keeping the directory name
intact. Nothing outside that directory is required at runtime.

## Use

```text
Use $cinemacc-subtitle to find an eligible English SRT for [title and year], refine it, translate it into zh-CN, and package the result for CinemaCC.
```

When only a title is supplied, the default route acquires and verifies a source, refines it, translates it, runs QA, and delivers the result. An attached source skips acquisition. Explicit requests can stop after download, refinement, translation, or packaging. Chinese jobs still default to independently localized Mainland Chinese (`zh-CN`) and Taiwan Chinese (`zh-TW`) unless the user requests one target.

## What it handles

- source search and ordinary authorized download with a manual fallback for blocked sites;
- source-track diagnosis and OCR/STT repair before translation;
- title, character, terminology, and cultural context research;
- subtitle-source provenance and timing-family comparison;
- resumable workbooks, glossaries, uncertainties, and narrow QA waivers;
- deterministic cue, timestamp, formatting-tag, encoding, and newline checks;
- audited pruning and sequential renumbering of confirmed non-program cue residue;
- safe chunk splitting and merging for long subtitles;
- deterministic two-track CinemaCC ZIP bundles with movie, release, language, and source metadata;
- atomic standalone-file delivery with hashes and receipts.

## Repository layout

```text
.
├── plugin.json                       # Agent Plugins 1.0.0 manifest (portable)
├── .claude-plugin/
│   ├── plugin.json                   # Claude Code plugin manifest
│   └── marketplace.json              # Claude Code marketplace catalog
├── .codex-plugin/plugin.json         # OpenAI ChatGPT/Codex plugin manifest
├── tools/check_manifests.py          # keeps the manifests and SKILL.md in sync
└── skills/cinemacc-subtitle/
    ├── SKILL.md
    ├── agents/openai.yaml            # OpenAI-specific skill metadata
    ├── references/
    └── scripts/
```

`skills/cinemacc-subtitle/` is the whole skill. Every manifest at the repository root is an additive
distribution wrapper for one client family; none of them changes the skill, and removing any one of them
leaves the skill installable by every other client.

## Compatibility

| Client | Mechanism | Manifest used |
| --- | --- | --- |
| Claude Code | plugin marketplace | `.claude-plugin/marketplace.json`, `.claude-plugin/plugin.json` |
| ChatGPT, Codex | plugin install / `$skill-installer` | `.codex-plugin/plugin.json` |
| VS Code, Cursor, GitHub Copilot, Kiro, and other Agent Plugins clients | Agent Plugins package | `plugin.json` |
| 75+ agents via the skills CLI | direct `skills/` discovery | none |

The skill uses no MCP servers and no client-specific hooks, so the portable core is the same everywhere.

## Requirements

- Python 3.10 or newer; the deterministic tooling uses only the standard library.
- A skills-compatible agent with file access.
- Web access for source acquisition and title-specific research unless a usable source is supplied and the user explicitly requests no browsing.

## Verify

```bash
python3 skills/cinemacc-subtitle/scripts/test_srt_tools.py
python3 tools/check_manifests.py
python3 evals/evaluate.py
```

The first command exercises the deterministic tooling. The second validates the `SKILL.md` frontmatter
against the Agent Skills specification limits and checks that the skill name and version match every
distribution manifest. Both run in CI on every push.

## Evaluate

[`evals/harbor-lights/case.json`](evals/harbor-lights/case.json) is a synthetic end-to-end regression case that explicitly invokes the installed skill and exercises the full acquire → review → zh-CN translation → CinemaCC delivery route, including the rule against inventing an import link. Run its prompt in a clean directory, then grade the resulting package:

```bash
python3 evals/evaluate.py /path/to/candidate.cinemacc.zip
```

The deterministic grader checks the package contract, source-byte preservation, cue timing, formatting tags, and player encoding. Use the human rubric in the case file for translation quality and the agent's report. The committed [reference package](evals/harbor-lights/reference.cinemacc.zip) is also a stable public fixture for CinemaCC import tests after it lands on `main`.

## Privacy, cost, and rights

CinemaCC does not operate a translation or subtitle-hosting service for this skill. Subtitle text, source pages, and research queries may be sent to the agent or model provider you choose, and that provider's pricing and privacy terms apply.

The repository does not include commercial movie or TV subtitles. You are responsible for having the rights needed to translate or distribute any source and output files.

## CinemaCC

[CinemaCC](https://cinemacc.net) is a subtitle companion for films on any screen. It can import one or two SRT tracks, including the two-track ZIP produced by this skill, for synchronized theater-dark playback.

## License

The code and documentation are available under the [MIT License](LICENSE). The license does not grant rights to third-party subtitle content or CinemaCC trademarks.
