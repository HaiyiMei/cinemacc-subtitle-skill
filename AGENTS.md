# Repository guide for agents

This repository publishes a single Agent Skill through several distribution manifests. Nothing here is
application code; treat `skills/cinemacc-subtitle-skill/` as the product and everything else as packaging.

## Layout

- `skills/cinemacc-subtitle-skill/SKILL.md` - the skill itself. Authoritative for `name` and, through
  `metadata.version`, for the release version.
- `skills/cinemacc-subtitle-skill/references/` - loaded on demand by the skill; keep each file focused.
- `skills/cinemacc-subtitle-skill/scripts/srt_tools.py` - deterministic tooling. Standard library only,
  Python 3.10+. It must never call a translation service or rewrite subtitle meaning.
- `plugin.json` - portable Agent Plugins manifest. Closed schema: only the fields the spec permits.
- `.claude-plugin/` - Claude Code plugin and marketplace manifests.
- `.codex-plugin/plugin.json` - OpenAI Codex plugin manifest, including install-surface `interface` copy.
- `tools/check_manifests.py` - consistency check across all of the above.

## Before committing

```bash
python3 skills/cinemacc-subtitle-skill/scripts/test_srt_tools.py
python3 tools/check_manifests.py
```

## Release checklist

1. Bump `metadata.version` in `SKILL.md`.
2. Mirror that version in `plugin.json`, `.claude-plugin/plugin.json`,
   `.claude-plugin/marketplace.json` (both the metadata and the plugin entry), and
   `.codex-plugin/plugin.json`.
3. Add a `CHANGELOG.md` entry.
4. Run `python3 tools/check_manifests.py`.

## Conventions

- Keep `SKILL.md` under 500 lines; move detail into `references/`.
- Do not add commercial subtitle content to the repository.
