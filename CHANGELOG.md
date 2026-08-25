# Changelog

All notable changes to this repository are documented here. The project follows
[Semantic Versioning](https://semver.org/spec/v2.0.0.html). The version in
`SKILL.md` (`metadata.version`) is authoritative; every plugin manifest mirrors it.

## [0.4.0] - 2026-08-25

### Added

- `prune-cues`, a deterministic command that removes reviewed non-program SRT blocks by unambiguous
  block position, preserves every retained timestamp and body, renumbers the viewing track, and writes a
  hash-backed original-to-output audit map.
- Inspection and strict-QA detection for runs of three or more ellipsis-only cues.
- Tests covering malformed source numbering, empty and punctuation-only residue, renumbering, source
  preservation, invalid selections, missing reasons, and protection against dropping an entire track.

### Changed

- The workflow now inspects and, when justified, prunes confirmed uploader-credit or advertising
  fragments before initializing a translation job.
- Neutral ellipses are limited to isolated contaminated cues that may occupy genuine program time. The
  skill explicitly forbids filling a confirmed non-program run with repeated placeholders.
- Runtime requirements moved from the optional `compatibility` frontmatter field into the skill body so
  the same package passes both portable Agent Skills and current ChatGPT/Codex validation.

## [0.3.0] - 2026-08-25

### Added

- A mandatory source-eligibility gate: verify the observed subtitle language from representative cues and classify coverage against the relevant runtime as full, partial, or unverified before translation begins.
- A candidate-source decision matrix covering observed language, coverage, timing family, textual provenance, and release-name claims.

### Changed

- Prohibits presenting a mislabeled or partial track as the requested source-language deliverable. An unexpected-language track may be translated directly only with explicit user approval and clear coverage disclosure.
- Clarifies that a complete requested-language track with the user’s timing skeleton takes priority over a visually better but incompatible release.

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
