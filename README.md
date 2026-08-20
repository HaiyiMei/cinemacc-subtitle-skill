# CinemaCC Subtitle Skill

[![skills.sh](https://skills.sh/b/HaiyiMei/cinemacc-subtitle-skill)](https://skills.sh/HaiyiMei/cinemacc-subtitle-skill)

An open, auditable Agent Skill for researching, repairing, translating, and validating movie or TV SRT subtitles without silently changing cue timing.

The skill keeps semantic decisions with the agent or human reviewer and delegates snapshots, hashes, source comparison, chunking, assembly, structural QA, and atomic delivery to a deterministic Python tool.

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
Use $cinemacc-subtitle to research and refine this SRT, then create validated zh-CN and zh-TW subtitles without changing its timing.
```

By default, the skill produces a refined source track plus independently localized Mainland Chinese (`zh-CN`) and Taiwan Chinese (`zh-TW`) tracks. Other target languages can be requested explicitly.

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
- Web access for title-specific research unless the input is a synthetic fixture, private unreleased recording, or the user explicitly requests no browsing.

## Verify

```bash
python3 skills/cinemacc-subtitle/scripts/test_srt_tools.py
python3 tools/check_manifests.py
```

The first command exercises the deterministic tooling. The second validates the `SKILL.md` frontmatter
against the Agent Skills specification limits and checks that the skill name and version match every
distribution manifest. Both run in CI on every push.

## Privacy, cost, and rights

CinemaCC does not operate a translation service for this skill. Subtitle text and research queries may be sent to the agent or model provider you choose, and that provider's pricing and privacy terms apply.

The repository does not include commercial movie or TV subtitles. You are responsible for having the rights needed to translate or distribute any source and output files.

## CinemaCC

[CinemaCC](https://cinemacc.net) is a subtitle companion for films on any screen. It can import one or two SRT tracks for synchronized, theater-dark playback.

## License

The code and documentation are available under the [MIT License](LICENSE). The license does not grant rights to third-party subtitle content or CinemaCC trademarks.
