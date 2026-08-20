# Changelog

All notable changes to this repository are documented here. The project follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). The version in
`SKILL.md` (`metadata.version`) is authoritative; every plugin manifest mirrors it.

## [0.2.0] - 2026-08-20

### Added

- Portable [Agent Plugins 1.0.0](https://agent-plugins.org/specification) manifest at `plugin.json`, so
  Agent Plugins clients (VS Code, Cursor, GitHub Copilot, ChatGPT & Codex, Kiro, and others) can load the
  skill from the repository root.
- Claude Code plugin manifest at `.claude-plugin/plugin.json` and marketplace catalog at
  `.claude-plugin/marketplace.json`, so the repository can be added with `/plugin marketplace add`.
- `compatibility` frontmatter in `SKILL.md` declaring the Python, filesystem, and network requirements.
- `tools/check_manifests.py`, which validates the `SKILL.md` frontmatter against the Agent Skills
  specification limits and keeps the name and version aligned across all four manifests.
- GitHub Actions workflow running the tool test suite on Python 3.10-3.13, the manifest check, and a
  skills CLI discovery smoke test.

### Changed

- Renamed the skill and the plugin from `cinemacc-subtitle-skill` to `cinemacc-subtitle`. The `-skill`
  suffix was redundant everywhere the identifier is actually typed (`$cinemacc-subtitle`,
  `/plugin install cinemacc-subtitle@cinemacc`). The repository name is unchanged, so existing
  `npx skills add HaiyiMei/cinemacc-subtitle-skill` commands and the skills.sh listing still resolve.
- Documented per-client installation in the README instead of assuming the OpenAI distribution path.

## [0.1.1] - 2026-08-20

### Added

- Initial public release: `SKILL.md`, deterministic `srt_tools.py`, references, and the OpenAI Codex
  plugin manifest.
